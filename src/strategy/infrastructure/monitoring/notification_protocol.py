"""Shared realtime notification protocol for monitor snapshot and decision events."""

from __future__ import annotations

import json
from typing import Any, Dict


MONITOR_SNAPSHOT_UPDATES_CHANNEL = "monitor_snapshot_updates"
MONITOR_DECISION_TRACE_UPDATES_CHANNEL = "monitor_decision_trace_updates"


def build_snapshot_notification(
    *,
    variant: str,
    instance_id: str,
    updated_at: str,
) -> Dict[str, str]:
    return {
        "variant": variant,
        "instance_id": instance_id,
        "updated_at": updated_at,
    }


def build_decision_trace_notification(
    *,
    variant: str,
    instance_id: str,
    event_id: int,
    event_type: str,
) -> Dict[str, Any]:
    return {
        "variant": variant,
        "instance_id": instance_id,
        "event_id": int(event_id),
        "event_type": event_type,
    }


def encode_notification_payload(payload: Dict[str, Any]) -> str:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True)


def decode_notification_payload(payload: str) -> Dict[str, Any]:
    if not payload:
        return {}
    try:
        obj = json.loads(payload)
    except Exception:
        return {}
    return obj if isinstance(obj, dict) else {}
