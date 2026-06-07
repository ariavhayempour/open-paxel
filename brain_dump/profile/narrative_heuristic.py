from __future__ import annotations

from collections import Counter

from brain_dump.models.domain import DIMENSIONS, SessionReport
from brain_dump.models.profile_narrative import ProfileNarrative
from brain_dump.profile.insights import ProfileSignals, _the_archetype


def _session_phrase(n: int, word: str = "session") -> str:
    return f"{n} {word}{'' if n == 1 else 's'}"


def _top_projects(reports: list[SessionReport]) -> list[str]:
    paths = [r.project_path for r in reports if r.project_path]
    if not paths:
        return []
    counts = Counter(paths)
    return [p for p, _ in counts.most_common(3)]


def _steering_summary(reports: list[SessionReport]) -> str:
    scores = [r.dimensions["steering"].score for r in reports if "steering" in r.dimensions]
    if not scores:
        return "You steer the agent actively during implementation."
    avg = sum(scores) / len(scores)
    if avg >= 75:
        return "You keep strong control over architecture, scope, and direction while the agent executes."
    if avg >= 55:
        return "You mix hands-on steering with letting the agent run on well-scoped tasks."
    return "You tend to delegate execution and step in when outcomes drift."


def build_profile_narrative(
    reports: list[SessionReport],
    signals: ProfileSignals,
    *,
    archetype: str,
    signature_moves: list[str],
    growth_edge: list[str],
) -> ProfileNarrative:
    if not reports:
        return ProfileNarrative()

    n = len(reports)
    top_arch = _the_archetype(archetype)
    projects = _top_projects(reports)
    titles = [r.title for r in reports if r.title and r.title.strip()]

    narrative = (
        f"You used Claude Code as an implementation partner. {_steering_summary(reports)} "
        f"Across {_session_phrase(n)}, your overall builder pattern reads as {top_arch}."
    )

    built_parts: list[str] = []
    if projects:
        built_parts.append(
            "You worked across "
            + ", ".join(projects[:3])
            + ("." if len(projects) <= 3 else ", and related projects.")
        )
    if titles:
        built_parts.append(
            "Session focus areas included "
            + "; ".join(titles[:4])
            + ("." if len(titles) <= 4 else "; and more.")
        )
    elif signature_moves:
        built_parts.append(signature_moves[0] + ".")
    what_you_built = " ".join(built_parts) or "Your analyzed sessions show sustained building work with Claude Code."

    redirects_per_10 = (signals.redirect_hits / max(signals.turn_total, 1)) * 10
    decision_intro = (
        "Your decision style skews toward architecture and course-correction."
        if redirects_per_10 >= 2
        else "Your decision style balances exploration with targeted corrections when the agent drifts."
    )
    pattern_body = ""
    if signature_moves:
        pattern_body = (
            f" Recurring moves include: {signature_moves[0]}"
            + (f"; {signature_moves[1]}" if len(signature_moves) > 1 else "")
            + "."
        )
    matched = signature_moves[0] if signature_moves else None
    matched_category = "Code & Architecture" if matched else None

    decision_patterns = decision_intro + pattern_body
    if signals.relationship:
        decision_patterns += f" {signals.relationship}"

    strengths: list[str] = []
    for move in signature_moves[:3]:
        strengths.append(f"In {_session_phrase(n)}, {move[0].lower() + move[1:] if move else move}.")
    for dim in ("steering", "execution", "engineering"):
        scores = [r.dimensions[dim].score for r in reports if dim in r.dimensions]
        if scores and sum(scores) / len(scores) >= 70:
            label = dim.replace("_", " ")
            strengths.append(f"You show strong {label} in your analyzed sessions.")

    growth_areas: list[str] = []
    for tip in growth_edge[:3]:
        growth_areas.append(tip)
    planning_scores = [r.dimensions["planning"].score for r in reports if "planning" in r.dimensions]
    if planning_scores and sum(planning_scores) / len(planning_scores) < 55 and not growth_areas:
        growth_areas.append(
            f"In {_session_phrase(n)}, planning signals were light. "
            "Before the next long run, write a short plan with target files, expected outputs, and validation steps."
        )

    return ProfileNarrative(
        narrative=narrative,
        what_you_built=what_you_built,
        decision_patterns=decision_patterns.strip(),
        matched_pattern=matched,
        matched_pattern_category=matched_category,
        strengths=strengths[:4],
        growth_areas=growth_areas[:3],
    )
