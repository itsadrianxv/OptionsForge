from __future__ import annotations

from typing import Any

from ..models import CapabilityContribution, ClosePipelineRoles, OpenPipelineRoles


class _SmartOrderExecutorProvider:
    def build(
        self,
        entry: Any,
        full_config: dict[str, Any],
        kernel: Any,
    ) -> CapabilityContribution:
        executor = getattr(entry, "smart_order_executor", None)
        if executor is None:
            return CapabilityContribution()

        def open_execution_planner(selected_contract: Any, signal: Any, sizing_payload: dict[str, Any] | None) -> dict[str, Any]:
            return {
                "vt_symbol": selected_contract.vt_symbol,
                "signal_name": getattr(signal, "signal_name", ""),
                "planned_action": "open",
                "suggested_volume": sizing_payload.get("final_volume") if sizing_payload else None,
            }

        def close_execution_planner(position: Any, signal: Any, close_payload: dict[str, Any] | None) -> dict[str, Any]:
            return {
                "vt_symbol": getattr(position, "vt_symbol", ""),
                "signal_name": getattr(signal, "signal_name", ""),
                "planned_action": "close",
                **dict(close_payload or {}),
            }

        return CapabilityContribution(
            open_pipeline=OpenPipelineRoles(execution_planner=open_execution_planner),
            close_pipeline=ClosePipelineRoles(execution_planner=close_execution_planner),
        )


PROVIDER = _SmartOrderExecutorProvider()
