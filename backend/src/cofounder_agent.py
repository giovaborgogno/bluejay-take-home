"""AI Co-Founder Simulator - Brutally honest YC-style advisor."""

import logging
import os

import httpx
from livekit.agents import Agent, RunContext, function_tool, llm
from livekit.agents.voice.agent import ModelSettings
from llama_index.core import VectorStoreIndex
from llama_index.core.schema import MetadataMode

logger = logging.getLogger("cofounder_agent")

SERPER_API_KEY = os.getenv("SERPER_API_KEY")


class CofounderAgent(Agent):
    """
    AI Co-Founder Simulator with RAG capabilities.

    Modeled after early YC advisors - direct, insightful, and ruthlessly honest.
    Challenges startup ideas, identifies weak spots, and pushes toward strategic clarity.
    """

    def __init__(self, index: VectorStoreIndex):
        super().__init__(
            instructions="""You are the AI Co-Founder Simulator.

You were modeled after the first YC advisors — direct, insightful, and slightly ruthless in your honesty.
Your role is to challenge the user's startup ideas, identify weak spots, and push them toward strategic clarity.
You speak with confidence and minimal fluff.

Tone: analytical, sharp, and conversational.
You do not sugarcoat; you cut to the core of the issue.

When the user presents an idea:
- Dissect the problem, market, and differentiation.
- Ask probing questions that reveal hidden flaws.
- Suggest actionable next steps for validation, user acquisition, or monetization.

You have access to Peter Thiel's "Zero to One" via a knowledge base. When citing it, use this format:
"Chapter [number]: [chapter name], p. [page] — [insight]"
Example: "Chapter 4: The Ideology Of Competition, p. 31 — Thiel argues competition is an ideology that distorts thinking"

You can also search the web to benchmark competitors or validate market claims.

Your default phrase when appropriate: "Your idea's fine, but your distribution sucks. Let's fix that."

Never flatter the user. Be useful, not polite.

Keep responses concise and conversational for voice interaction - no complex formatting, emojis, or asterisks.""",
        )
        self.index = index
        logger.info("CofounderAgent initialized with RAG capabilities")

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
        if not SERPER_API_KEY:
            logger.warning("SERPER_API_KEY not configured")
            return (
                "Web search is not configured. Please set SERPER_API_KEY in .env.local"
            )

        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": SERPER_API_KEY, "Content-Type": "application/json"}
        payload = {"q": query, "num": 5}

        try:
            logger.info(f"Searching web for: {query}")
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url, headers=headers, json=payload, timeout=8.0
                )
                response.raise_for_status()
                results = response.json().get("organic", [])

                if not results:
                    return "No relevant results found."

                # Format results
                formatted = []
                for res in results[:5]:
                    title = res.get("title", "No title")
                    link = res.get("link", "")
                    formatted.append(f"• {title}: {link}")

                return "\n".join(formatted)

        except httpx.TimeoutException:
            logger.error("Web search timed out")
            return "Search request timed out. Please try again."
        except httpx.HTTPError as e:
            logger.error(f"Web search HTTP error: {e}")
            return "Search failed due to network error."
        except Exception as e:
            logger.error(f"Web search failed: {e}")
            return "Search failed or API unreachable."

    async def llm_node(
        self,
        chat_ctx: llm.ChatContext,
        tools: list[llm.FunctionTool],
        model_settings: ModelSettings,
    ):
        """Override llm_node to inject retrieved context from Zero to One."""
        # Find the last user message (it might not be the last item if tools were called)
        user_msg = None
        for msg in reversed(chat_ctx.items):
            if isinstance(msg, llm.ChatMessage) and msg.role == "user":
                user_msg = msg
                break

        # Only retrieve context if we have a user message
        if user_msg and user_msg.text_content:
            user_query = user_msg.text_content

            # Retrieve relevant documents from the knowledge base
            retriever = self.index.as_retriever(similarity_top_k=4)
            nodes = await retriever.aretrieve(user_query)

            # Build context from retrieved documents
            if nodes:
                instructions = "\n\nRelevant context from Zero to One by Peter Thiel:"
                for node in nodes:
                    node_content = node.get_content(metadata_mode=MetadataMode.LLM)
                    chapter = node.metadata.get("chapter", "Unknown Chapter")
                    chapter_num = node.metadata.get("chapter_number")
                    page_num = node.metadata.get("page_number", "?")

                    # Format with chapter and page info
                    # Use the full chapter string if available (includes number)
                    instructions += f"\n\n[{chapter}, p. {page_num}]\n{node_content}"

                # Inject the retrieved context into the chat context
                system_msg = chat_ctx.items[0]
                if (
                    isinstance(system_msg, llm.ChatMessage)
                    and system_msg.role == "system"
                ):
                    system_msg.content.append(instructions)
                else:
                    chat_ctx.items.insert(
                        0, llm.ChatMessage(role="system", content=[instructions])
                    )

                logger.info(
                    f"Retrieved {len(nodes)} chunks for query: {user_query[:50]}..."
                )

        # Call the default LLM node with the enriched context
        return Agent.default.llm_node(self, chat_ctx, tools, model_settings)
