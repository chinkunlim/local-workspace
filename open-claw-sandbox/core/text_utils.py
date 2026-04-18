# -*- coding: utf-8 -*-
"""
text_utils.py — Text processing and chunking utilities
========================================================
Provides text splitting and tokenization-aware chunking for Map-Reduce operations.
Extracted from voice-memo Phase 5 for shared usage with pdf-knowledge.
"""

from typing import List

def smart_split(text: str, chunk_size: int) -> List[str]:
    """
    Split text into chunks ≤ chunk_size, respecting line boundaries.
    
    Args:
        text: The input text to split
        chunk_size: Maximum character count per chunk
        
    Returns:
        A list of string chunks.
    """
    lines = text.split("\n")
    chunks = []
    current = ""
    for line in lines:
        candidate = (current + "\n" + line).strip() if current else line
        if len(candidate) > chunk_size and current:
            chunks.append(current.strip())
            current = line
        else:
            current = candidate
    if current.strip():
        chunks.append(current.strip())
    return chunks if chunks else [text]

def count_words_approx(text: str) -> int:
    """Approximate word/token count for rough LLM sizing."""
    # Assuming avg 2 chars per CJK word or 5 per English word. Simple approx:
    return len(text)
