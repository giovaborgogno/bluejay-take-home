import logging
import os
import random
from pathlib import Path
from typing import Any, Optional

from dotenv import load_dotenv
from kairoz import Kairoz
from kairoz.tracking import initialize_tracking
from livekit.agents import (
    AgentSession,
    JobContext,
    JobProcess,
    MetricsCollectedEvent,
    RoomInputOptions,
    WorkerOptions,
    cli,
    metrics,
)
from livekit.plugins import noise_cancellation, silero
from livekit.plugins.turn_detector.multilingual import MultilingualModel

from agent import CofounderAgent
from prompts import SYSTEM_PROMPT, WELCOME_MESSAGES
from rag_engine import initialize_rag_index

logger = logging.getLogger("entrypoint")

load_dotenv(".env.local")

# Initialize RAG index
THIS_DIR = Path(__file__).parent
DATA_DIR = THIS_DIR / "data"
PERSIST_DIR = THIS_DIR / "retrieval-engine-storage"

index = initialize_rag_index(DATA_DIR, PERSIST_DIR)

DEFAULT_MODEL_CONFIG: dict[str, str] = {
    "stt": "assemblyai/universal-streaming:en",
    "llm": "openai/gpt-4.1-mini",
    "tts": "cartesia/sonic-2:a167e0f3-df7e-4d52-a9c3-f949145efdab",
}


class _KairozSettings:
    def __init__(self) -> None:
        self._prompt_instructions: Optional[str] = None
        self._model_config: dict[str, str] = DEFAULT_MODEL_CONFIG.copy()
        self._prompt_metadata: dict[str, Any] = {}
        self._prompt_config: dict[str, Any] = {}
        self._welcome_messages: list[str] = list(WELCOME_MESSAGES)
        self._tracing_enabled = False
        self._initialized = False

    def ensure_loaded(self) -> None:
        if self._initialized:
            return

        self._initialized = True

        api_key = os.getenv("KAIROZ_API_KEY")
        if not api_key:
            logger.warning("KAIROZ_API_KEY not set; using local prompt configuration.")
            return

        try:
            initialize_tracking(api_key=api_key)
            self._tracing_enabled = True
        except Exception as exc:  # pragma: no cover - best effort logging
            logger.warning("Failed to initialize Kairoz tracing: %s", exc)
            self._tracing_enabled = False

        try:
            client = Kairoz(api_key=api_key)
        except Exception as exc:  # pragma: no cover - best effort logging
            logger.warning("Failed to initialize Kairoz client: %s", exc)
            return

        prompt_name = os.getenv("KAIROZ_PROMPT_NAME", "cofounder-agent")
        prompt_kwargs: dict[str, Any] = {}
        prompt_label = os.getenv("KAIROZ_PROMPT_LABEL")
        prompt_version = os.getenv("KAIROZ_PROMPT_VERSION")
        if prompt_label:
            prompt_kwargs["label"] = prompt_label
        if prompt_version:
            prompt_kwargs["version"] = prompt_version

        try:
            prompt = client.get_prompt(prompt_name, **prompt_kwargs)
        except Exception as exc:
            logger.warning("Failed to fetch Kairoz prompt '%s': %s", prompt_name, exc)
            return

        self._prompt_instructions = self._extract_system_prompt(prompt)
        self._prompt_config = getattr(prompt, "config", {}) or {}
        self._model_config = self._build_model_config(self._prompt_config)
        self._welcome_messages = self._extract_welcome_messages(self._prompt_config)
        self._prompt_metadata = {
            "prompt_name": getattr(prompt, "name", prompt_name),
            "prompt_label": prompt_kwargs.get("label"),
            "prompt_version": getattr(prompt, "version", prompt_kwargs.get("version")),
        }

    @staticmethod
    def _extract_system_prompt(prompt: Any) -> Optional[str]:
        if prompt is None:
            return None

        prompt_body = getattr(prompt, "prompt", None)

        if isinstance(prompt_body, str):
            return prompt_body

        if isinstance(prompt_body, list):
            system_messages = [
                message.get("content")
                for message in prompt_body
                if isinstance(message, dict)
                and message.get("role") == "system"
                and isinstance(message.get("content"), str)
            ]
            if system_messages:
                return "\n\n".join(system_messages)

        return None

    @staticmethod
    def _build_model_config(prompt_config: dict[str, Any]) -> dict[str, str]:
        config_source: dict[str, Any] = {}
        if isinstance(prompt_config, dict):
            config_source = prompt_config.get("models", prompt_config) or {}

        model_config = DEFAULT_MODEL_CONFIG.copy()

        for key in ("stt", "llm", "tts"):
            value = None
            if isinstance(config_source, dict):
                value = config_source.get(key) or config_source.get(f"{key}_model")
            if isinstance(prompt_config, dict) and value is None:
                value = prompt_config.get(key) or prompt_config.get(f"{key}_model")
            if isinstance(value, str) and value.strip():
                model_config[key] = value.strip()

        return model_config

    @property
    def welcome_messages(self) -> list[str]:
        self.ensure_loaded()
        return self._welcome_messages or list(WELCOME_MESSAGES)

    @staticmethod
    def _extract_welcome_messages(config: dict[str, Any]) -> list[str]:
        if not isinstance(config, dict):
            return list(WELCOME_MESSAGES)

        candidates = config.get("welcome_messages") or config.get("welcomeMessages")
        if not isinstance(candidates, list):
            return list(WELCOME_MESSAGES)

        messages = [msg for msg in candidates if isinstance(msg, str) and msg.strip()]
        return messages or list(WELCOME_MESSAGES)

    @property
    def prompt_instructions(self) -> str:
        self.ensure_loaded()
        return self._prompt_instructions or SYSTEM_PROMPT

    @property
    def model_config(self) -> dict[str, str]:
        self.ensure_loaded()
        return self._model_config

    @property
    def prompt_config(self) -> dict[str, Any]:
        self.ensure_loaded()
        return self._prompt_config

    @property
    def tracing_enabled(self) -> bool:
        self.ensure_loaded()
        return self._tracing_enabled

    @property
    def prompt_metadata(self) -> dict[str, Any]:
        self.ensure_loaded()
        return {k: v for k, v in self._prompt_metadata.items() if v}


def load_kairoz_settings() -> _KairozSettings:
    settings = _KairozSettings()
    settings.ensure_loaded()
    return settings


def prewarm(proc: JobProcess):
    proc.userdata["vad"] = silero.VAD.load()


async def entrypoint(ctx: JobContext):
    # Logging setup
    # Add any other context you want in all log entries here
    ctx.log_context_fields = {
        "room": ctx.room.name,
    }

    kairoz_settings = load_kairoz_settings()
    model_config = kairoz_settings.model_config
    instructions = kairoz_settings.prompt_instructions
    prompt_config = kairoz_settings.prompt_config
    trace_metadata = kairoz_settings.prompt_metadata
    welcome_messages = kairoz_settings.welcome_messages
    tracing_enabled = kairoz_settings.tracing_enabled

    logger.info(
        "Starting session with config",
        extra={
            "stt_model": model_config.get("stt"),
            "llm_model": model_config.get("llm"),
            "tts_model": model_config.get("tts"),
            "prompt_source": trace_metadata.get("prompt_name"),
        },
    )

    # Set up a voice AI pipeline using OpenAI, Cartesia, AssemblyAI, and the LiveKit turn detector
    session = AgentSession(
        # Speech-to-text (STT) is your agent's ears, turning the user's speech into text that the LLM can understand
        # See all available models at https://docs.livekit.io/agents/models/stt/
        stt=model_config["stt"],
        # A Large Language Model (LLM) is your agent's brain, processing user input and generating a response
        # See all available models at https://docs.livekit.io/agents/models/llm/
        llm=model_config["llm"],
        # Text-to-speech (TTS) is your agent's voice, turning the LLM's text into speech that the user can hear
        # See all available models as well as voice selections at https://docs.livekit.io/agents/models/tts/
        tts=model_config["tts"],
        # VAD and turn detection are used to determine when the user is speaking and when the agent should respond
        # See more at https://docs.livekit.io/agents/build/turns
        turn_detection=MultilingualModel(),
        vad=ctx.proc.userdata["vad"],
        # allow the LLM to generate a response while waiting for the end of turn
        # See more at https://docs.livekit.io/agents/build/audio/#preemptive-generation
        preemptive_generation=True,
    )

    # Metrics collection, to measure pipeline performance
    # For more information, see https://docs.livekit.io/agents/build/metrics/
    usage_collector = metrics.UsageCollector()

    @session.on("metrics_collected")
    def _on_metrics_collected(ev: MetricsCollectedEvent):
        metrics.log_metrics(ev.metrics)
        usage_collector.collect(ev.metrics)

    async def log_usage():
        summary = usage_collector.get_summary()
        logger.info(f"Usage: {summary}")

    ctx.add_shutdown_callback(log_usage)

    # Start the session, which initializes the voice pipeline and warms up the models
    # Using CofounderAgent - AI Co-Founder Simulator with RAG and web search
    agent = CofounderAgent(
        index,
        instructions=instructions,
        prompt_config=prompt_config,
        trace_metadata=trace_metadata,
        enable_tracing=tracing_enabled,
    )
    await session.start(
        agent=agent,
        room=ctx.room,
        room_input_options=RoomInputOptions(
            # For telephony applications, use `BVCTelephony` for best results
            noise_cancellation=noise_cancellation.BVC(),
        ),
    )

    # Join the room and connect to the user
    await ctx.connect()

    # Send a random welcome message when the session starts
    welcome_message = random.choice(welcome_messages)
    logger.info(f"Sending welcome message: {welcome_message}")
    await session.say(welcome_message, allow_interruptions=False)


if __name__ == "__main__":
    cli.run_app(WorkerOptions(entrypoint_fnc=entrypoint, prewarm_fnc=prewarm))
