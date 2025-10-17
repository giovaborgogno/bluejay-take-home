# BlueJay - YC Co-Founder Voice Agent

> _"Your idea's fine, but your distribution sucks. Let's fix that."_

A RAG-enabled voice agent that acts as your brutally honest YC co-founder. Built with LiveKit, deployed on AWS.

## Demo: https://bluejay-take-home.vercel.app/

## 🎯 What It Does

Talk to an AI modeled after early YC advisors that:

- **Challenges your startup ideas** with direct, insightful feedback
- **Answers questions using Peter Thiel's "Zero to One"** via real-time RAG retrieval
- **Searches the web** to benchmark competitors and validate market claims
- **Maintains live transcription** of your conversation

## 🏗️ Architecture

```
Frontend (Next.js) → LiveKit Cloud → Agent (Python/AWS ECS)
                                          ├─ RAG Engine (LlamaIndex)
                                          ├─ Vector Store (Zero to One PDF)
                                          └─ Web Search Tool (Serper API)
```

### Tech Stack

- **Voice**: LiveKit Agents (STT/TTS/VAD pipeline)
- **RAG**: LlamaIndex with OpenAI embeddings & retrieval
- **LLM**: OpenAI GPT-4.1-mini
- **Tools**: Web search via Serper API
- **Frontend**: Next.js + React
- **Deployment**: AWS ECS with Docker

### RAG Implementation

1. **Document Processing**: Peter Thiel's "Zero to One" (PDF) → chunked with semantic overlap
2. **Embedding**: OpenAI `text-embedding-3-small`
3. **Storage**: Persistent vector store with metadata (chapter/page refs)
4. **Retrieval**: Semantic search → top-k relevant passages → injected into agent context
5. **Citation**: Agent formats responses with `"Chapter X: Title, page Y — insight"`

The agent can answer specific questions like _"What does Thiel say about competition in Chapter 4?"_ with exact page references.

## 🚀 Setup

### Prerequisites

```bash
# Required API keys
LIVEKIT_URL=wss://...
LIVEKIT_API_KEY=...
LIVEKIT_API_SECRET=...
OPENAI_API_KEY=sk-...
SERPER_API_KEY=...  # For web search
```

### Local Development

**Backend**:

```bash
cd backend
uv sync
uv run python src/entrypoint.py download-files
uv run python src/entrypoint.py dev
```

**Frontend**:

```bash
cd frontend
pnpm install
pnpm dev
```

Visit `http://localhost:3000`, click "Start Call", and challenge the AI with your startup idea.

### AWS Deployment

Backend is containerized and deployed to ECS:

See `backend/infra/README.md` for detailed deployment steps.

## 💡 Design Decisions

**1. Personality-First Design**: The system prompt is the core product. Spent significant time crafting the YC advisor persona—sharp, direct, actionable. Voice agents live or die by conversational quality.

**2. RAG Framework Over DIY**: Used LlamaIndex instead of building from scratch. Faster iteration, better retrieval quality, and proper chunking strategies out-of-the-box.

**3. Web Search Tool**: Essential for the "co-founder" narrative. Agent can fact-check market claims ("Search: {competitor} funding rounds") and surface real-time data during the call.

**4. AWS vs Local**: Deployed on ECS for reliability and to avoid local network issues during evaluation. Trade-off: slightly higher latency (~50ms) vs. 100% uptime.

**5. PDF Choice**: "Zero to One" is the canonical startup playbook. Fits the YC narrative perfectly and has dense, quotable insights across 160 pages—ideal for testing RAG accuracy.

## 🛠️ Development Process

1. **Research Phase**: Explored LiveKit docs, agent examples, and RAG integrations
2. **Prototype**: Combined `agent-starter-react`, `agent-starter-python`, and `llamaindex-rag-retrieval` examples from LiveKit
3. **Personality Layer**: Crafted system prompt, tested conversational flow, tuned for voice (no markdown/emojis)
4. **Robust RAG**: Enhanced retrieval with better chunking, metadata tracking, and citation formatting
5. **Tools**: Integrated Serper web search for competitive analysis
6. **Deployment**: Dockerized backend, deployed to AWS ECS, configured LiveKit Cloud
7. **UI Polish**: Updated frontend theme to match YC branding

## 📦 Repository Structure

```
bluejay-take-home/
├── backend/
│   ├── src/
│   │   ├── agent.py          # LiveKit agent logic
│   │   ├── prompts.py        # System prompt & personality
│   │   ├── rag_engine.py     # LlamaIndex RAG setup
│   │   ├── tools.py          # Web search tool
│   │   └── data/             # Zero to One PDF
│   ├── infra/                # AWS CloudFormation
│   └── Dockerfile
└── frontend/
    ├── app/                  # Next.js routes
    ├── components/           # React UI components
    └── hooks/                # LiveKit integration
```

## 🎨 AI Tools Used

- **ChatGPT**: Exploratory research on LiveKit architecture and RAG strategies (before to go deep into oficial docs)
- **Cursor**: Plan mode and Build on each iteration (AWS Deployment, UI Polish, parser and chunking for RAG, Web Search and Refactor)

---

**Built by Giovanni Borgogno** • [Contact me](mailto:giovaborgogno@gmail.com)
