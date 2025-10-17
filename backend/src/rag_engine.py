"""RAG Engine for Zero to One knowledge base with chapter parsing."""

import logging
import re
from pathlib import Path

from llama_index.core import (
    StorageContext,
    VectorStoreIndex,
    load_index_from_storage,
)
from llama_index.core.node_parser import SentenceSplitter
from llama_index.readers.file import PyMuPDFReader

logger = logging.getLogger("rag_engine")


def initialize_rag_index(data_dir: Path, persist_dir: Path) -> VectorStoreIndex:
    """
    Initialize or load the RAG index with chapter parsing for Zero to One.

    Args:
        data_dir: Directory containing the PDF documents
        persist_dir: Directory to persist the vector store

    Returns:
        VectorStoreIndex: The initialized or loaded index
    """
    # Check if storage already exists
    if persist_dir.exists():
        logger.info(f"Loading existing RAG index from {persist_dir}")
        storage_context = StorageContext.from_defaults(persist_dir=persist_dir)
        return load_index_from_storage(storage_context)

    logger.info("Creating new RAG index from documents...")

    # Load documents with PyMuPDFReader to preserve page numbers
    reader = PyMuPDFReader()
    pdf_path = data_dir / "zero-to-one.pdf"

    if not pdf_path.exists():
        logger.error(f"PDF not found at {pdf_path}")
        raise FileNotFoundError(f"zero-to-one.pdf not found in {data_dir}")

    documents = reader.load(file_path=pdf_path)
    logger.info(f"Loaded {len(documents)} pages from Zero to One")

    # First pass: identify chapter pages and their titles
    # In Zero to One, chapters are structured as:
    # - One page with just a number (chapter number)
    # - Following pages have the chapter title in ALL CAPS
    chapter_map = {}  # Maps page index to (chapter_number, chapter_title)
    current_chapter = None
    current_chapter_num = None

    num_only = re.compile(r"^\s*\d+\s*$")  # Page with only a number
    up_head = re.compile(r"^[A-Z0-9 ,''–\-:!?\.\&]+$")  # All caps title

    for i, doc in enumerate(documents):
        text = (doc.text or "").strip()

        # Check if this page is just a chapter number
        if num_only.match(text):
            current_chapter_num = text.strip()  # Save the chapter number
            current_chapter = None  # Will be set by next page with title
            continue

        # Check if this page starts with an all-caps title (likely chapter title)
        lines = text.splitlines()
        if lines and len(lines[0].strip()) > 0:
            first_line = lines[0].strip()
            # Must be all caps, reasonably long, and not too long
            if up_head.match(first_line) and 10 < len(first_line) < 80:
                current_chapter = first_line.title()
                # Store both chapter number and title
                chapter_map[i] = (current_chapter_num, current_chapter)
                current_chapter_num = None  # Reset for next chapter
        elif current_chapter:
            # Continue with same chapter for subsequent pages
            chapter_map[i] = (current_chapter_num, current_chapter)

    # Second pass: assign chapters and page numbers
    # Maintain the last known chapter for pages between chapters
    last_chapter_info = None

    for i, doc in enumerate(documents):
        # Check if this page starts a new chapter
        if i in chapter_map:
            last_chapter_info = chapter_map[i]

        # Assign chapter (use last known chapter if available)
        if last_chapter_info:
            chapter_num, chapter_title = last_chapter_info
            if chapter_num:
                doc.metadata["chapter"] = f"Chapter {chapter_num}: {chapter_title}"
                doc.metadata["chapter_number"] = chapter_num
            else:
                doc.metadata["chapter"] = chapter_title
            if chapter_title:
                doc.metadata["chapter_title"] = chapter_title
        else:
            doc.metadata["chapter"] = "Unknown Chapter"

        # Use the 'source' field which PyMuPDFReader provides
        doc.metadata["page_number"] = doc.metadata.get("source", "Unknown")

    logger.info("Chapter parsing complete")

    # Create chunks with overlap
    splitter = SentenceSplitter(chunk_size=1000, chunk_overlap=180)
    nodes = splitter.get_nodes_from_documents(documents)

    logger.info(f"Created {len(nodes)} chunks from documents")

    # Create vector store index
    index = VectorStoreIndex(nodes)

    # Persist for future use
    index.storage_context.persist(persist_dir=persist_dir)
    logger.info(f"RAG index created and saved to {persist_dir}")

    return index
