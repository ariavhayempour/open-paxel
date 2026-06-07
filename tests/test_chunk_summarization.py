import pytest

from brain_dump.metrics.heuristics import compute_heuristics
from brain_dump.parser.text_session import TextSessionParser
from brain_dump.redact.excerpts import build_excerpts
from brain_dump.scorer.openai_scorer import OpenAIScorer
from brain_dump.text.chunking import needs_chunk_summarization
from brain_dump.text.tokens import divide_into_chunks


def test_divide_into_chunks_long_text():
    text = ("paragraph one.\n\n" * 50) + ("paragraph two with more words.\n\n" * 80)
    chunks = divide_into_chunks(text, chunk_tokens=400)
    assert len(chunks) > 1
    assert all(c.strip() for c in chunks)


def test_needs_chunk_summarization():
    assert needs_chunk_summarization(total_tokens=100, is_structured=True, transcript_tokens=100) is False
    assert needs_chunk_summarization(total_tokens=500, is_structured=False, transcript_tokens=500) is False
    assert needs_chunk_summarization(total_tokens=1500, is_structured=False, transcript_tokens=1500) is True
    assert needs_chunk_summarization(total_tokens=11_000, is_structured=True, transcript_tokens=11_000) is True


@pytest.mark.asyncio
async def test_accumulate_chunk_summaries_dry_run():
    text = ("User wants a feature.\n\n" * 30) + ("Assistant writes code.\n\n" * 30)
    scorer = OpenAIScorer(api_key="x", model="gpt-4.1-mini", dry_run=True)
    summary, count = await scorer.accumulate_chunk_summaries(text)
    assert count >= 1
    assert "Chunk" in summary


@pytest.mark.asyncio
async def test_excerpts_flag_unstructured_for_chunk_pass(tmp_path):
    path = tmp_path / "long.txt"
    path.write_text("word " * 2000 + "\n\n" + "line " * 2000, encoding="utf-8")
    facts = TextSessionParser().parse(path)
    metrics = compute_heuristics(facts)
    excerpts = build_excerpts(facts, metrics)
    assert excerpts.raw_transcript
    assert excerpts.metrics_json["uses_chunk_summarization"] is True
