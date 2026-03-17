from __future__ import annotations

from typing import Any

from ..models import CapabilityContribution, PortfolioRoles


class _VegaHedgingProvider:
    def build(
        self,
        entry: Any,
        full_config: dict[str, Any],
        kernel: Any,
    ) -> CapabilityContribution:
        def rebalance_planner(**kwargs: Any) -> dict[str, Any]:
            return {"mode": "vega", "action": "hedge"}

        return CapabilityContribution(
            portfolio=PortfolioRoles(rebalance_planner=rebalance_planner)
        )


PROVIDER = _VegaHedgingProvider()
