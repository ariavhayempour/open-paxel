import asyncio

import open_paxel.cli  # noqa: F401  # load packages in app order (avoids documented text<->parser import cycle when this module is collected first)
from open_paxel.config import Settings
from open_paxel.scorer.transcript_condenser import (
    _char_chunks,
    _sample_chunks,
    condense_transcript,
    needs_condensing,
)


def test_char_chunks_respects_size_and_covers_text():
    text = "\n".join(f"line {i} " + "x" * 50 for i in range(2000))
    chunks = _char_chunks(text, 5_000)
    assert len(chunks) > 1
    assert all(len(c) <= 5_000 for c in chunks)
    # Concatenated chunks preserve all non-whitespace content (boundary-split only).
    assert "".join(c.replace("\n", "").replace(" ", "") for c in chunks) == \
        text.replace("\n", "").replace(" ", "")


def test_sample_chunks_caps_and_keeps_first_and_last():
    chunks = [f"c{i}" for i in range(50)]
    sampled, was_sampled = _sample_chunks(chunks, 12)
    assert was_sampled is True
    assert len(sampled) == 12
    assert sampled[0] == "c0"
    assert sampled[-1] == "c49"


def test_sample_chunks_noop_under_cap():
    chunks = [f"c{i}" for i in range(5)]
    sampled, was_sampled = _sample_chunks(chunks, 12)
    assert was_sampled is False
    assert sampled == chunks


def test_needs_condensing_threshold():
    s = Settings(condense_over_est_tokens=1_000)
    assert needs_condensing("x " * 10_000, s) is True
    assert needs_condensing("short transcript", s) is False


def test_condense_transcript_dry_run_produces_summary():
    s = Settings(dry_run=True, condense_chunk_chars=2_000, condense_max_chunks=8)
    text = "\n\n".join(f"user: step {i}\n\nassistant: did {i}" for i in range(500))
    summary, chunk_count = asyncio.run(condense_transcript(text, s))
    assert chunk_count >= 1
    assert summary.strip()
