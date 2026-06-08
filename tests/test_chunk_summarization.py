import pytest

from open_paxel.config import Settings
from open_paxel.metrics.heuristics import compute_heuristics
from open_paxel.parser.text_session import TextSessionParser
from open_paxel.redact.excerpts import build_excerpts
from open_paxel.scorer.openai_scorer import OpenAIScorer
from open_paxel.text.tokens import divide_into_chunks


def test_divide_into_chunks_long_text():
    text = ("paragraph one.\n\n" * 50) + ("paragraph two with more words.\n\n" * 80)
    chunks = divide_into_chunks(text, chunk_tokens=400)
    assert len(chunks) > 1
    assert all(c.strip() for c in chunks)


@pytest.mark.asyncio
async def test_score_session_dry_run_skips_api():
    scorer = OpenAIScorer(Settings(dry_run=True, openai_api_key="x"))
    from open_paxel.models.domain import HeuristicMetrics, RedactedExcerpt, SessionFacts

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

    from open_paxel.scorer.openai_scorer import OpenAIScorer

    raw = OpenAIScorer(Settings(dry_run=True, openai_api_key="x")).build_user_prompt(
        facts, metrics, excerpts
    )
    return json.loads(raw)
