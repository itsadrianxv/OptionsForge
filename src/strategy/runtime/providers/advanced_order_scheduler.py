from __future__ import annotations

from typing import Any

from ..models import CapabilityContribution, ClosePipelineRoles, OpenPipelineRoles


class _AdvancedOrderSchedulerProvider:
    def build(
        self,
        entry: Any,
        full_config: dict[str, Any],
        kernel: Any,
    ) -> CapabilityContribution:
        def execution_scheduler(execution_plan: dict[str, Any]) -> dict[str, Any]:
            return {**dict(execution_plan), "scheduled": True}

        return CapabilityContribution(
            open_pipeline=OpenPipelineRoles(execution_scheduler=execution_scheduler),
            close_pipeline=ClosePipelineRoles(execution_scheduler=execution_scheduler),
        )


PROVIDER = _AdvancedOrderSchedulerProvider()
