from brain_dump.text.document_scan import scan_document
from brain_dump.text.tokens import divide_into_chunks, estimate_tokens, sliding_windows


def test_estimate_tokens():
    assert estimate_tokens("hello world") >= 2
    long = "word " * 500
    assert estimate_tokens(long) > 100


def test_sliding_windows_overlap():
    text = "paragraph. " * 800
    windows = sliding_windows(text, window_tokens=200, overlap_tokens=50)
    assert len(windows) > 1
    assert all(w.strip() for w in windows)


def test_divide_into_chunks():
    text = ("paragraph one with extra words. " * 20 + "\n\n") * 40
    chunks = divide_into_chunks(text, chunk_tokens=200)
    assert len(chunks) >= 2


def test_document_scan_counts():
    text = """
# Plan the API

User: How do I fix this bug?

```bash
pytest tests/
npm run lint
```

Actually wait, use redis instead.

+added line
-removed line
"""
    stats = scan_document(text)
    assert stats.total_tokens > 0
    assert stats.test_lint_hits >= 1
    assert stats.redirect_hits >= 1
    assert stats.code_block_count >= 1
    assert stats.estimated_turns >= 1
