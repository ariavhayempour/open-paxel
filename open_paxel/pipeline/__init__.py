from __future__ import annotations

from open_paxel.pipeline.analysis import AnalysisPipeline
from open_paxel.pipeline.context import PipelineContext

__all__ = ["AnalysisPipeline", "PaxelPipeline", "PipelineContext"]


def __getattr__(name: str):
    if name == "PaxelPipeline":
        from open_paxel.pipeline.orchestrator import PaxelPipeline

        return PaxelPipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
