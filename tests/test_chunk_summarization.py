import pytest

from brain_dump.metrics.heuristics import compute_heuristics
from brain_dump.parser.text_session import TextSessionParser
from brain_dump.redact.excerpts import build_excerpts
from brain_dump.scorer.openai_scorer import OpenAIScorer
from brain_dump.text.tokens import divide_into_chunks


def test_divide_into_chunks_long_text():
    text = ("paragraph one.\n\n" * 50) + ("paragraph two with more words.\n\n" * 80)
    chunks = divide_into_chunks(text, chunk_tokens=400)
    assert len(chunks) > 1
    assert all(c.strip() for c in chunks)


@pytest.mark.asyncio
async def test_score_session_dry_run_skips_api():
    scorer = OpenAIScorer(api_key="x", model="gpt-4.1-mini", dry_run=True)
    from brain_dump.models.domain import HeuristicMetrics, RedactedExcerpt, SessionFacts

    facts = SessionFacts(session_id="s1", transcript_path="t.jsonl")
    metrics = HeuristicMetrics()
    excerpts = RedactedExcerpt(session_id="s1", raw_transcript="User: hello\n\nAssistant: hi")
    score = await scorer.score_session(facts, metrics, excerpts)
    assert score.archetype == "Explorer"


def test_excerpts_always_include_full_transcript(tmp_path):
    path = tmp_path / "long.txt"
    path.write_text("word " * 2000 + "\n\n" + "line " * 2000, encoding="utf-8")
    facts = TextSessionParser().parse(path)
    metrics = compute_heuristics(facts)
    excerpts = build_excerpts(facts, metrics)
    assert excerpts.raw_transcript
    assert excerpts.metrics_json["uses_full_transcript"] is True
    assert "session_transcript" in scorer_prompt(excerpts, facts, metrics)


def scorer_prompt(excerpts, facts, metrics) -> dict:
    import json

    from brain_dump.scorer.openai_scorer import OpenAIScorer

    raw = OpenAIScorer(api_key="x", model="gpt-4.1-mini", dry_run=True).build_user_prompt(
        facts, metrics, excerpts
    )
    return json.loads(raw)
