from __future__ import annotations

from open_paxel.models.domain import SessionFacts, SessionReport
from open_paxel.models.pipeline_models import SteeringTrace
from open_paxel.parser.patterns import REDIRECT_PATTERN
from open_paxel.redact.transcript import redact_text


def extract_steering_traces(
    facts: SessionFacts,
    *,
    max_traces: int = 20,
) -> list[SteeringTrace]:
    traces: list[SteeringTrace] = []
    last_was_tool = False

    for msg in facts.user_messages:
        text = msg.text.strip()
        if not text:
            last_was_tool = True
            continue
        is_steering = (
            last_was_tool
            or bool(REDIRECT_PATTERN.search(text))
            or len(text.split()) <= 25
        )
        if is_steering:
            traces.append(
                SteeringTrace(
                    session_id=facts.session_id,
                    text=redact_text(text, 500),
                    timestamp=msg.timestamp,
                    after_tool=last_was_tool,
                )
            )
        last_was_tool = False
        if len(traces) >= max_traces:
            break

    return traces


def attach_steering_traces(report: SessionReport, facts: SessionFacts) -> SessionReport:
    return report.model_copy(update={"steering_traces": extract_steering_traces(facts)})
