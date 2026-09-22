"""Google Gemini Multimodal AI package for table tennis rally spotting."""
from .detector import (
    detect_rallies_with_gemini,
    clean_json_response,
    merge_adjacent_rallies,
    build_chunk_prompt,
)

__all__ = [
    "detect_rallies_with_gemini",
    "clean_json_response",
    "merge_adjacent_rallies",
    "build_chunk_prompt",
]
