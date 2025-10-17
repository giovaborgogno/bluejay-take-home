<a href="https://livekit.io/">
  <img src="./.github/assets/livekit-mark.png" alt="LiveKit logo" width="100" height="100">
</a>

# AI Co-Founder Simulator - LiveKit Voice Agent

A brutally honest YC-style co-founder you can talk to, built with [LiveKit Agents for Python](https://github.com/livekit/agents) and [LiveKit Cloud](https://cloud.livekit.io/).

## 🧠 What is this?

The AI Co-Founder Simulator gives you direct, unsweetened feedback on your startup ideas, market strategy, and distribution — modeled after the early Y Combinator advisors. It challenges your assumptions and helps you find leverage points fast.

> "Your idea's fine, but your distribution sucks. Let's fix that."

The agent includes:

- **Brutally honest YC-style personality**: Direct, insightful, and slightly ruthless
- **RAG with Peter Thiel's "Zero to One"**: Ask questions about Thiel's startup philosophy with chapter-aware citations
- **Real-time competitor search**: Web search tool to validate competitors and market claims
- **Voice AI pipeline** with models from OpenAI, Cartesia, and AssemblyAI
- **Modular architecture**: Separated RAG engine, web search tool, and agent logic
- [LiveKit Turn Detector](https://docs.livekit.io/agents/build/turns/turn-detector/) for contextually-aware speaker detection
- [Background voice cancellation](https://docs.livekit.io/home/cloud/noise-cancellation/)
- A Dockerfile ready for [production deployment](https://docs.livekit.io/agents/ops/deployment/)

This agent is compatible with any [custom web/mobile frontend](https://docs.livekit.io/agents/start/frontend/) or [SIP-based telephony](https://docs.livekit.io/agents/start/telephony/).

## Dev Setup

Clone the repository and install dependencies to a virtual environment:

```console
cd agent-starter-python
uv sync
```

Sign up for [LiveKit Cloud](https://cloud.livekit.io/) then set up the environment by copying `.env.example` to `.env.local` and filling in the required keys:

- `LIVEKIT_URL`
- `LIVEKIT_API_KEY`
- `LIVEKIT_API_SECRET`
- `OPENAI_API_KEY` (required for LLM and RAG embeddings)
- `ASSEMBLYAI_API_KEY` (required for speech-to-text)
- `CARTESIA_API_KEY` (required for text-to-speech)
- `SERPER_API_KEY` (required for web search - get it from [serper.dev](https://serper.dev/))

You can load the LiveKit environment automatically using the [LiveKit CLI](https://docs.livekit.io/home/cli/cli-setup):

```bash
lk cloud auth
lk app env -w -d .env.local
```

### RAG Setup - Zero to One Knowledge Base

The agent has access to Peter Thiel's "Zero to One" through a sophisticated RAG system:

1. **Document**: The PDF is located in `src/data/zero-to-one.pdf`
2. **Chapter parsing**: The RAG engine automatically extracts chapter names and page numbers for accurate citations
3. **First run**: The agent will create a vector index with chapter-aware metadata
4. **Subsequent runs**: The pre-built index loads instantly

The RAG index is stored in `src/retrieval-engine-storage/` and persists between runs. To rebuild the index (e.g., after adding new documents), delete this directory and restart the agent.

**Example interaction:**

- User: "What does Thiel say about monopolies?"
- Agent: "Chapter: You Are Not A Lottery Ticket, p. 47 — Thiel argues that monopolies drive progress..."

### Web Search Tool

The agent can search the web for competitor validation and market research using [Serper.dev](https://serper.dev/). Make sure to add your `SERPER_API_KEY` to `.env.local`.

**Example interaction:**

- User: "Who else is doing AI voice assistants?"
- Agent: _searches web and returns competitors_

### Architecture

The codebase is modular:

- `src/rag_engine.py` - RAG initialization with chapter parsing
- `src/cofounder_agent.py` - CofounderAgent class with YC personality and integrated web search tool
- `src/agent.py` - Main entrypoint and session setup

## Run the agent

Before your first run, you must download certain models such as [Silero VAD](https://docs.livekit.io/agents/build/turns/vad/) and the [LiveKit turn detector](https://docs.livekit.io/agents/build/turns/turn-detector/):

```console
uv run python src/agent.py download-files
```

Next, run this command to speak to your agent directly in your terminal:

```console
uv run python src/agent.py console
```

To run the agent for use with a frontend or telephony, use the `dev` command:

```console
uv run python src/agent.py dev
```

In production, use the `start` command:

```console
uv run python src/agent.py start
```

## Frontend & Telephony

Get started quickly with our pre-built frontend starter apps, or add telephony support:

| Platform         | Link                                                                                                                | Description                                        |
| ---------------- | ------------------------------------------------------------------------------------------------------------------- | -------------------------------------------------- |
| **Web**          | [`livekit-examples/agent-starter-react`](https://github.com/livekit-examples/agent-starter-react)                   | Web voice AI assistant with React & Next.js        |
| **iOS/macOS**    | [`livekit-examples/agent-starter-swift`](https://github.com/livekit-examples/agent-starter-swift)                   | Native iOS, macOS, and visionOS voice AI assistant |
| **Flutter**      | [`livekit-examples/agent-starter-flutter`](https://github.com/livekit-examples/agent-starter-flutter)               | Cross-platform voice AI assistant app              |
| **React Native** | [`livekit-examples/voice-assistant-react-native`](https://github.com/livekit-examples/voice-assistant-react-native) | Native mobile app with React Native & Expo         |
| **Android**      | [`livekit-examples/agent-starter-android`](https://github.com/livekit-examples/agent-starter-android)               | Native Android app with Kotlin & Jetpack Compose   |
| **Web Embed**    | [`livekit-examples/agent-starter-embed`](https://github.com/livekit-examples/agent-starter-embed)                   | Voice AI widget for any website                    |
| **Telephony**    | [📚 Documentation](https://docs.livekit.io/agents/start/telephony/)                                                 | Add inbound or outbound calling to your agent      |

For advanced customization, see the [complete frontend guide](https://docs.livekit.io/agents/start/frontend/).

## Tests and evals

This project includes a complete suite of evals, based on the LiveKit Agents [testing & evaluation framework](https://docs.livekit.io/agents/build/testing/). To run them, use `pytest`.

```console
uv run pytest
```

## Using this template repo for your own project

Once you've started your own project based on this repo, you should:

1. **Check in your `uv.lock`**: This file is currently untracked for the template, but you should commit it to your repository for reproducible builds and proper configuration management. (The same applies to `livekit.toml`, if you run your agents in LiveKit Cloud)

2. **Remove the git tracking test**: Delete the "Check files not tracked in git" step from `.github/workflows/tests.yml` since you'll now want this file to be tracked. These are just there for development purposes in the template repo itself.

3. **Add your own repository secrets**: You must [add secrets](https://docs.github.com/en/actions/how-tos/writing-workflows/choosing-what-your-workflow-does/using-secrets-in-github-actions) for `LIVEKIT_URL`, `LIVEKIT_API_KEY`, and `LIVEKIT_API_SECRET` so that the tests can run in CI.

## Deploying to production

This project is production-ready and includes a working `Dockerfile`. To deploy it to LiveKit Cloud or another environment, see the [deploying to production](https://docs.livekit.io/agents/ops/deployment/) guide.

## Self-hosted LiveKit

You can also self-host LiveKit instead of using LiveKit Cloud. See the [self-hosting](https://docs.livekit.io/home/self-hosting/) guide for more information. If you choose to self-host, you'll need to also use [model plugins](https://docs.livekit.io/agents/models/#plugins) instead of LiveKit Inference and will need to remove the [LiveKit Cloud noise cancellation](https://docs.livekit.io/home/cloud/noise-cancellation/) plugin.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
