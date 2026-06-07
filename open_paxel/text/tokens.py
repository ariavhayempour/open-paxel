from __future__ import annotations


def estimate_tokens(text: str) -> int:
    """Fast token estimate (~4 chars/token for mixed code/prose)."""
    if not text:
        return 0
    words = len(text.split())
    char_est = len(text) // 4
    word_est = int(words * 1.35)
    return max(1, (char_est + word_est) // 2)


def sliding_windows(
    text: str,
    *,
    window_tokens: int = 1500,
    overlap_tokens: int = 200,
    max_windows: int | None = None,
) -> list[str]:
    """Split text into overlapping windows sized by estimated tokens."""
    text = text.strip()
    if not text:
        return []

    total = estimate_tokens(text)
    if total <= window_tokens:
        return [text]

    # Approximate chars per window from token ratio
    chars_per_token = max(1, len(text) / total)
    window_chars = max(200, int(window_tokens * chars_per_token))
    overlap_chars = max(40, int(overlap_tokens * chars_per_token))
    step = max(1, window_chars - overlap_chars)

    windows: list[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + window_chars)
        chunk = text[start:end].strip()
        if chunk:
            windows.append(chunk)
        if end >= len(text):
            break
        start += step

    if max_windows and len(windows) > max_windows:
        return _sample_windows(windows, max_windows)
    return windows


def _sample_windows(windows: list[str], count: int) -> list[str]:
    """Evenly sample windows, always keeping first and last."""
    if len(windows) <= count:
        return windows
    if count <= 2:
        return [windows[0], windows[-1]][:count]
    indices = {0, len(windows) - 1}
    inner = count - 2
    for i in range(inner):
        idx = round((i + 1) * (len(windows) - 1) / (inner + 1))
        indices.add(idx)
    return [windows[i] for i in sorted(indices)]


def chunk_paragraphs(text: str, target_tokens: int = 400) -> list[str]:
    """Paragraph-aware chunks for pseudo-turn segmentation."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return [text.strip()] if text.strip() else []

    chunks: list[str] = []
    buf: list[str] = []
    buf_tokens = 0

    def flush() -> None:
        nonlocal buf, buf_tokens
        if buf:
            chunks.append("\n\n".join(buf))
            buf = []
            buf_tokens = 0

    for para in paragraphs:
        pt = estimate_tokens(para)
        if pt >= target_tokens * 2:
            flush()
            for win in sliding_windows(
                para, window_tokens=target_tokens, overlap_tokens=50, max_windows=None
            ):
                chunks.append(win)
            continue
        if buf_tokens + pt > target_tokens and buf:
            flush()
        buf.append(para)
        buf_tokens += pt

    flush()
    return chunks or ([text.strip()] if text.strip() else [])


def divide_into_chunks(text: str, *, chunk_tokens: int = 10_000) -> list[str]:
    """Split text into non-overlapping analysis chunks (paragraph-aware)."""
    text = text.strip()
    if not text:
        return []

    if estimate_tokens(text) <= chunk_tokens:
        return [text]

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    if not paragraphs:
        return [text]

    chunks: list[str] = []
    buf: list[str] = []
    buf_tokens = 0

    def flush() -> None:
        nonlocal buf, buf_tokens
        if buf:
            chunks.append("\n\n".join(buf))
            buf = []
            buf_tokens = 0

    for para in paragraphs:
        pt = estimate_tokens(para)
        if pt > chunk_tokens:
            flush()
            # Hard-split oversized paragraphs without overlap.
            for win in sliding_windows(
                para, window_tokens=chunk_tokens, overlap_tokens=0, max_windows=None
            ):
                if win.strip():
                    chunks.append(win.strip())
            continue
        if buf_tokens + pt > chunk_tokens and buf:
            flush()
        buf.append(para)
        buf_tokens += pt

    flush()
    return chunks or [text]


def select_representative_windows(
    text: str,
    *,
    window_tokens: int = 1200,
    overlap_tokens: int = 150,
    max_windows: int = 5,
) -> list[str]:
    """Pick windows biased toward start, end, and signal-rich regions."""
    from open_paxel.parser.patterns import REDIRECT_PATTERN, TEST_LINT_PATTERN

    all_windows = sliding_windows(
        text,
        window_tokens=window_tokens,
        overlap_tokens=overlap_tokens,
        max_windows=None,
    )
    if len(all_windows) <= max_windows:
        return all_windows

    scored: list[tuple[int, int, str]] = []
    for idx, win in enumerate(all_windows):
        score = 0
        if idx == 0:
            score += 100
        if idx == len(all_windows) - 1:
            score += 90
        if REDIRECT_PATTERN.search(win):
            score += 40
        if TEST_LINT_PATTERN.search(win):
            score += 30
        if "```" in win:
            score += 20
        if "?" in win:
            score += 10
        scored.append((score, idx, win))

    scored.sort(key=lambda x: (-x[0], x[1]))
    chosen = sorted({idx for _, idx, _ in scored[:max_windows]})
    return [all_windows[i] for i in chosen]
