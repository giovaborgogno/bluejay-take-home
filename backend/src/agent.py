"""AI Co-Founder Simulator - Brutally honest YC-style advisor."""

import logging

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

    def __init__(self, index: VectorStoreIndex):
        super().__init__(
            instructions=SYSTEM_PROMPT,
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
        return await web_search_serper(context, query)

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
                    # Gracefully handle None for chapter_num
                    if chapter_num is not None:
                        instructions += f"\n\n[{chapter_num}: {chapter}, p. {page_num}]\n{node_content}"
                    else:
                        instructions += (
                            f"\n\n[{chapter}, p. {page_num}]\n{node_content}"
                        )

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
