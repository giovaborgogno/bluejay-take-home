"""AI Co-Founder Simulator - Brutally honest YC-style advisor."""

import contextlib
import logging
from typing import Any, Optional

from kairoz.tracking import trace
from livekit.agents import Agent, RunContext, function_tool, llm
from livekit.agents.voice.agent import ModelSettings
from llama_index.core import VectorStoreIndex
from llama_index.core.schema import MetadataMode

from prompts import SYSTEM_PROMPT
from tools import web_search_serper

logger = logging.getLogger("agent")


class CofounderAgent(Agent):
    """
    AI Co-Founder Simulator with RAG capabilities.

    Modeled after early YC advisors - direct, insightful, and ruthlessly honest.
    Challenges startup ideas, identifies weak spots, and pushes toward strategic clarity.
    """

    def __init__(
        self,
        index: VectorStoreIndex,
        *,
        instructions: Optional[str] = None,
        prompt_config: Optional[dict[str, Any]] = None,
        trace_metadata: Optional[dict[str, Any]] = None,
        enable_tracing: bool = False,
    ):
        super().__init__(
            instructions=instructions or SYSTEM_PROMPT,
        )
        self.index = index
        self.prompt_config = prompt_config or {}
        self.trace_metadata = trace_metadata or {}
        self._tracing_enabled = bool(enable_tracing and trace is not None)
        self._trace_cm = None
        self._trace = None
        self._trace_name = self._resolve_trace_name(self.prompt_config)
        self._generation_name = self.prompt_config.get("generation_name", "assistant-response")

        logger.info(
            "CofounderAgent initialized with RAG capabilities",
            extra={
                "trace_enabled": self._tracing_enabled,
                "trace_name": self._trace_name if self._tracing_enabled else None,
            },
        )

    @staticmethod
    def _resolve_trace_name(config: dict[str, Any]) -> str:
        if not isinstance(config, dict):
            return "claro-conversation"

        trace_name = config.get("trace_name") or config.get("conversation_trace_name")
        if isinstance(trace_name, str) and trace_name.strip():
            return trace_name.strip()

        return "claro-conversation"

    @staticmethod
    def _filter_metadata(metadata: dict[str, Any]) -> dict[str, Any]:
        if not isinstance(metadata, dict):
            return {}
        allowed_types = (str, int, float, bool)
        return {k: v for k, v in metadata.items() if isinstance(v, allowed_types)}

    async def on_enter(self) -> None:
        await super().on_enter()

        if not self._tracing_enabled or self._trace is not None:
            return

        trace_metadata = {"agent": self.label}
        trace_metadata.update(self._filter_metadata(self.trace_metadata))

        try:
            self._trace_cm = trace(
                name=self._trace_name,
                metadata=trace_metadata,
                tags=["demo", "kairoz"],
            )
            self._trace = self._trace_cm.__enter__()
        except Exception as exc:  # pragma: no cover - best effort logging
            logger.warning("Failed to start Kairoz trace: %s", exc)
            self._trace_cm = None
            self._trace = None
            self._tracing_enabled = False

    async def on_exit(self) -> None:
        try:
            await super().on_exit()
        finally:
            if self._trace_cm:
                try:
                    self._trace_cm.__exit__(None, None, None)
                except Exception as exc:  # pragma: no cover - best effort logging
                    logger.warning("Failed to close Kairoz trace: %s", exc)
                finally:
                    self._trace_cm = None
                    self._trace = None

    @function_tool
    async def web_search_serper(self, context: RunContext, query: str):
        """
        Search the web for competitors, market information, or relevant companies.

        Use this tool when the user asks about competitors, market validation,
        or wants to check if similar products/companies exist.

        Args:
            query: The search query (e.g., "AI voice assistant startups 2024")

        Returns:
            str: Formatted search results with titles and links
        """
        tool_span_cm = None
        tool_span_ctx = None
        result: str | None = None
        tool_error: Exception | None = None

        if self._trace:
            try:
                tool_span_cm = self._trace.span(
                    name="web-search",
                    input_data={"query": query},
                    metadata={"tool": "web_search_serper"},
                )
                tool_span_ctx = tool_span_cm.__enter__()
            except Exception as exc:  # pragma: no cover - best effort logging
                logger.warning("Failed to start web-search span: %s", exc)
                tool_span_cm = None

        try:
            result = await web_search_serper(context, query)
            return result
        except Exception as exc:
            tool_error = exc
            raise
        finally:
            if tool_span_ctx and tool_span_cm:
                update_payload: dict[str, Any] = {}
                if result is not None:
                    update_payload["output"] = result
                if tool_error:
                    update_payload["error"] = str(tool_error)
                if update_payload:
                    try:
                        tool_span_ctx.update(**update_payload)
                    except Exception as update_exc:  # pragma: no cover - best effort logging
                        logger.warning("Failed to update web-search span: %s", update_exc)
                try:
                    tool_span_cm.__exit__(
                        type(tool_error) if tool_error else None,
                        tool_error,
                        tool_error.__traceback__ if tool_error else None,
                    )
                except Exception as close_exc:  # pragma: no cover - best effort logging
                    logger.warning("Failed to close web-search span: %s", close_exc)
            elif tool_span_cm:
                try:
                    tool_span_cm.__exit__(None, None, None)
                except Exception as close_exc:  # pragma: no cover - best effort logging
                    logger.warning("Failed to close web-search span: %s", close_exc)

    async def llm_node(
        self,
        chat_ctx: llm.ChatContext,
        tools: list[llm.FunctionTool],
        model_settings: ModelSettings,
    ):
        """Override llm_node to inject retrieved context from Zero to One and add Kairoz tracing."""
        # Find the last user message (it might not be the last item if tools were called)
        user_msg = None
        for msg in reversed(chat_ctx.items):
            if isinstance(msg, llm.ChatMessage) and msg.role == "user":
                user_msg = msg
                break

        nodes: list[Any] = []
        user_query = None
        rag_error: Exception | None = None
        rag_span_cm = None
        rag_span_ctx = None
        rag_outputs: list[dict[str, Any]] = []

        # Only retrieve context if we have a user message
        # if user_msg and user_msg.text_content:
        #     user_query = user_msg.text_content

        #     # Retrieve relevant documents from the knowledge base
        #     retriever = self.index.as_retriever(similarity_top_k=4)
        #     if self._trace:
        #         try:
        #             rag_span_cm = self._trace.span(
        #                 name="rag-retrieval",
        #                 input_data={"query": user_query},
        #                 metadata={"source": "vector-store"},
        #             )
        #             rag_span_ctx = rag_span_cm.__enter__()
        #         except Exception as exc:  # pragma: no cover - best effort logging
        #             logger.warning("Failed to start RAG span: %s", exc)
        #             rag_span_cm = None
        #             rag_span_ctx = None

        #     try:
        #         nodes = await retriever.aretrieve(user_query)
        #     except Exception as exc:
        #         rag_error = exc
        #         nodes = []
        #         logger.warning("RAG retrieval failed: %s", exc)
        #     if rag_error:
        #         logger.debug("Continuing without RAG context due to retrieval error.")

        #     # Build context from retrieved documents
        #     if nodes:
        #         instructions = "\n\nRelevant context from Zero to One by Peter Thiel:"
        #         for node in nodes:
        #             node_content = node.get_content(metadata_mode=MetadataMode.LLM)
        #             chapter = node.metadata.get("chapter", "Unknown Chapter")
        #             chapter_num = node.metadata.get("chapter_number")
        #             page_num = node.metadata.get("page_number", "?")
        #             rag_outputs.append(
        #                 {
        #                     "chapter": chapter,
        #                     "chapter_number": chapter_num,
        #                     "page_number": page_num,
        #                     "content": node_content,
        #                 }
        #             )

        #             # Format with chapter and page info
        #             # Gracefully handle None for chapter_num
        #             if chapter_num is not None:
        #                 instructions += f"\n\n[{chapter_num}: {chapter}, p. {page_num}]\n{node_content}"
        #             else:
        #                 instructions += (
        #                     f"\n\n[{chapter}, p. {page_num}]\n{node_content}"
        #                 )

        #         # Inject the retrieved context into the chat context
        #         system_msg = chat_ctx.items[0]
        #         if (
        #             isinstance(system_msg, llm.ChatMessage)
        #             and system_msg.role == "system"
        #         ):
        #             system_msg.content.append(instructions)
        #         else:
        #             chat_ctx.items.insert(
        #                 0, llm.ChatMessage(role="system", content=[instructions])
        #             )

        #         logger.info(
        #             f"Retrieved {len(nodes)} chunks for query: {user_query[:50]}..."
        #         )

        #     if rag_span_ctx and rag_span_cm:
        #         span_update: dict[str, Any] = {"chunks": len(nodes)}
        #         if rag_outputs:
        #             span_update["context"] = rag_outputs
        #         if rag_error:
        #             span_update["error"] = str(rag_error)
        #         try:
        #             rag_span_ctx.update(output=span_update)
        #         except Exception as span_exc:  # pragma: no cover - best effort logging
        #             logger.warning("Failed to update RAG span: %s", span_exc)
        #         try:
        #             rag_span_cm.__exit__(
        #                 type(rag_error) if rag_error else None,
        #                 rag_error,
        #                 rag_error.__traceback__ if rag_error else None,
        #             )
        #         except Exception as span_exc:  # pragma: no cover - best effort logging
        #             logger.warning("Failed to close RAG span: %s", span_exc)
        #         rag_span_ctx = None
        #         rag_span_cm = None
        #     elif rag_span_cm:
        #         try:
        #             rag_span_cm.__exit__(None, None, None)
        #         except Exception as span_exc:  # pragma: no cover - best effort logging
        #             logger.warning("Failed to close RAG span: %s", span_exc)
        #         rag_span_cm = None

        # Call the default LLM node with the enriched context
        activity = None
        with contextlib.suppress(RuntimeError):
            activity = self._get_activity_or_raise()

        llm_model = getattr(activity.llm, "model", "unknown") if activity and activity.llm else "unknown"
        generation_cm = None
        generation_ctx = None
        collected_segments: list[str] = []
        usage_payload: dict[str, Any] | None = None
        llm_error: Exception | None = None

        system_prompt_text: str | None = None
        for item in chat_ctx.items:
            if isinstance(item, llm.ChatMessage) and item.role == "system":
                text_parts = [part for part in item.content if isinstance(part, str)]
                if text_parts:
                    system_prompt_text = "\n".join(text_parts)
                    break

        if self._trace:
            try:
                filtered_ctx = chat_ctx.copy(exclude_instructions=True)
                generation_input = {
                    "chat_ctx": filtered_ctx.to_dict(exclude_function_call=True),
                    "tool_count": len(tools),
                }
                generation_cm = self._trace.generation(
                    name=self._generation_name,
                    model=llm_model,
                    input_data=generation_input,
                )
                generation_ctx = generation_cm.__enter__()
            except Exception as exc:  # pragma: no cover - best effort logging
                logger.warning("Failed to create Kairoz generation: %s", exc)
                generation_cm = None
                generation_ctx = None

        try:
            async for chunk in Agent.default.llm_node(self, chat_ctx, tools, model_settings):
                if generation_ctx:
                    if isinstance(chunk, llm.ChatChunk):
                        if chunk.delta and chunk.delta.content:
                            collected_segments.append(chunk.delta.content)
                        if chunk.usage:
                            try:
                                usage_payload = chunk.usage.model_dump(exclude_none=True)
                            except Exception:
                                usage_payload = {
                                    "completion_tokens": chunk.usage.completion_tokens,
                                    "prompt_tokens": chunk.usage.prompt_tokens,
                                    "prompt_cached_tokens": chunk.usage.prompt_cached_tokens,
                                    "cache_creation_tokens": chunk.usage.cache_creation_tokens,
                                    "cache_read_tokens": chunk.usage.cache_read_tokens,
                                    "total_tokens": chunk.usage.total_tokens,
                                }
                    elif isinstance(chunk, str):
                        collected_segments.append(chunk)

                yield chunk
        except Exception as exc:
            llm_error = exc
            raise
        finally:
            if generation_ctx and generation_cm:
                update_payload: dict[str, Any] = {}
                if collected_segments:
                    update_payload["output"] = "".join(collected_segments)
                if usage_payload:
                    update_payload["usage"] = usage_payload
                if llm_error:
                    update_payload["error"] = str(llm_error)
                generation_metadata = self._filter_metadata(
                    {
                        "agent": self.label,
                        "provider": getattr(activity.llm, "provider", None)
                        if activity and activity.llm
                        else None,
                        "prompt_name": self.trace_metadata.get("prompt_name"),
                        "system_prompt": system_prompt_text,
                    }
                )
                if generation_metadata:
                    update_payload.setdefault("metadata", {}).update(generation_metadata)

                try:
                    if update_payload:
                        generation_ctx.update(**update_payload)
                except Exception as exc:  # pragma: no cover - best effort logging
                    logger.warning("Failed to update Kairoz generation: %s", exc)

                try:
                    generation_cm.__exit__(
                        type(llm_error) if llm_error else None,
                        llm_error,
                        llm_error.__traceback__ if llm_error else None,
                    )
                except Exception as exc:  # pragma: no cover - best effort logging
                    logger.warning("Failed to close Kairoz generation: %s", exc)
