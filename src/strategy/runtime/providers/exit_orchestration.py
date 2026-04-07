from __future__ import annotations

from typing import Any, Callable

from ..models import CapabilityContribution, ClosePipelineRoles


def _adapt_role(target: Any, method_name: str) -> Callable[..., Any] | None:
    if target is None:
        return None
    method = getattr(target, method_name, None)
    if callable(method):
        return method
    if callable(target):
        return target
    return None


class _ExitOrchestrationProvider:
    def build(
        self,
        entry: Any,
        full_config: dict[str, Any],
        kernel: Any,
    ) -> CapabilityContribution:
        intent_provider = _adapt_role(getattr(entry, "exit_intent_provider", None), "provide")
        group_resolver = _adapt_role(getattr(entry, "exit_group_resolver", None), "resolve")
        freshness_guard = _adapt_role(getattr(entry, "exit_freshness_guard", None), "check")

        return CapabilityContribution(
            close_pipeline=ClosePipelineRoles(
                exit_intent_provider=intent_provider,
                exposure_group_resolver=group_resolver,
                freshness_guard=freshness_guard,
            )
        )


PROVIDER = _ExitOrchestrationProvider()
