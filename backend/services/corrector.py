from backend.services.llm_client import LLMClient

_client = LLMClient()


async def correct_asr_text(raw_text: str) -> str:
    """Post-process a final ASR transcript through LLM for error correction."""
    if not raw_text.strip():
        return raw_text
    return await _client.correct_transcript(raw_text)
