"""CLI shared helpers."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from datetime import UTC, datetime
import json
from pathlib import Path
import sys
from typing import Any

from dotenv import load_dotenv
import typer

EXIT_CODE_FAILURE = 1
EXIT_CODE_VALIDATION = 2


@dataclass(frozen=True)
class CheckResult:
    """Single command-line check result."""

    status: str
    title: str
    detail: str


def append_option(arguments: list[str], flag: str, value: Any | None) -> None:
    """Append a value-bearing flag."""
    if value is None:
        return
    arguments.extend([flag, str(value)])


def append_flag(arguments: list[str], flag: str, enabled: bool) -> None:
    """Append a boolean flag."""
    if enabled:
        arguments.append(flag)


def flag_enabled(value: Any) -> bool:
    """Handle Click/Typer boolean flag values consistently."""
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


def invoke_legacy_main(
    entrypoint: Callable[[list[str] | None], int | None],
    argv: Sequence[str],
) -> int:
    """Invoke an existing CLI entrypoint and normalize ``SystemExit`` to an int code."""
    try:
        result = entrypoint(list(argv))
    except SystemExit as exc:
        code = exc.code
        if code is None:
            return 0
        return code if isinstance(code, int) else 1

    return 0 if result is None else int(result)


def get_project_root() -> Path:
    """Return the repository root."""
    return Path(__file__).resolve().parents[2]


def resolve_project_path(path: str | Path) -> Path:
    """Resolve a path relative to the repository root."""
    candidate = Path(path)
    if candidate.is_absolute():
        return candidate
    return get_project_root() / candidate


def display_path(path: str | Path) -> str:
    """Prefer repository-relative paths for display."""
    candidate = Path(path)
    try:
        return str(candidate.resolve().relative_to(get_project_root()))
    except Exception:
        return str(candidate)


def ensure_project_root_on_path() -> None:
    """Ensure the repository root is importable."""
    project_root = str(get_project_root())
    if project_root not in sys.path:
        sys.path.insert(0, project_root)


def load_project_dotenv() -> Path | None:
    """Load ``.env`` from the repository root when present."""
    env_path = get_project_root() / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=False)
        return env_path

    load_dotenv(override=False)
    return None


def echo_check(result: CheckResult) -> None:
    """Render a single textual check result."""
    typer.echo(f"[{result.status}] {result.title}: {result.detail}")


def check_payload(result: CheckResult) -> dict[str, str]:
    """Convert a check result into JSON-friendly data."""
    return {
        "status": result.status,
        "title": result.title,
        "detail": result.detail,
    }


def build_artifact(
    path: str | Path,
    *,
    label: str | None = None,
    kind: str = "file",
) -> dict[str, str]:
    """Build a standard artifact reference."""
    return {
        "path": display_path(path),
        "label": label or display_path(path),
        "kind": kind,
    }


def build_error(message: str, *, error_type: str = "error") -> dict[str, str]:
    """Build a standard error object."""
    return {
        "type": error_type,
        "message": message,
    }


def _json_default(value: Any) -> Any:
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, datetime):
        return value.isoformat()
    if is_dataclass(value):
        return asdict(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def to_json_text(payload: Mapping[str, Any] | Sequence[Any] | Any) -> str:
    """Serialize a payload as UTF-8 JSON."""
    return json.dumps(payload, ensure_ascii=False, default=_json_default)


def emit_single_json(
    command: str,
    *,
    ok: bool,
    data: Mapping[str, Any] | None = None,
    checks: Sequence[CheckResult | Mapping[str, Any]] = (),
    artifacts: Sequence[Mapping[str, Any]] = (),
    errors: Sequence[Mapping[str, Any]] = (),
    exit_code: int = 0,
) -> None:
    """Emit the standard single-response JSON envelope."""
    serialized_checks = [
        check_payload(item) if isinstance(item, CheckResult) else dict(item)
        for item in checks
    ]
    payload = {
        "ok": ok,
        "command": command,
        "mode": "single",
        "data": dict(data or {}),
        "checks": serialized_checks,
        "artifacts": [dict(item) for item in artifacts],
        "errors": [dict(item) for item in errors],
        "exit_code": exit_code,
    }
    typer.echo(to_json_text(payload))


def utc_now_iso() -> str:
    """Return the current UTC timestamp in ISO-8601."""
    return datetime.now(tz=UTC).isoformat()


class NdjsonEmitter:
    """Minimal NDJSON event writer for long-running commands."""

    def __init__(self, command: str) -> None:
        self.command = command
        self._seq = 0

    def emit(self, event: str, data: Mapping[str, Any] | None = None) -> None:
        self._seq += 1
        typer.echo(
            to_json_text(
                {
                    "command": self.command,
                    "event": event,
                    "seq": self._seq,
                    "ts": utc_now_iso(),
                    "data": dict(data or {}),
                }
            )
        )

    def start(self, **data: Any) -> None:
        self.emit("start", data)

    def phase(self, *, name: str, status: str, **data: Any) -> None:
        self.emit("phase", {"name": name, "status": status, **data})

    def log(self, *, level: str, message: str, logger_name: str | None = None) -> None:
        payload = {"level": level, "message": message}
        if logger_name:
            payload["logger"] = logger_name
        self.emit("log", payload)

    def artifact(self, *, path: str | Path, label: str | None = None, kind: str = "file") -> None:
        self.emit("artifact", build_artifact(path, label=label, kind=kind))

    def result(self, *, ok: bool, exit_code: int, **data: Any) -> None:
        self.emit("result", {"ok": ok, "exit_code": exit_code, **data})

    def error(self, *, message: str, error_type: str = "error", **data: Any) -> None:
        self.emit("error", {"type": error_type, "message": message, **data})


def capture_cli_failure_json(command: str, message: str, *, exit_code: int = EXIT_CODE_VALIDATION) -> None:
    """Emit a standard JSON error envelope and exit."""
    emit_single_json(
        command,
        ok=False,
        errors=(build_error(message),),
        exit_code=exit_code,
    )
    raise typer.Exit(code=exit_code)


def write_json_file(path: Path, payload: Mapping[str, Any]) -> Path:
    """Persist JSON with stable formatting."""
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=_json_default) + "\n",
        encoding="utf-8",
    )
    return path


def write_command_artifact(
    category: str,
    *,
    ok: bool,
    command: str,
    started_at: str,
    finished_at: str,
    inputs: Mapping[str, Any],
    summary: Mapping[str, Any] | None = None,
    artifacts: Sequence[Mapping[str, Any]] = (),
    errors: Sequence[Mapping[str, Any]] = (),
    repo_root: Path | None = None,
) -> Path:
    """Write ``artifacts/<category>/latest.json`` and return its path."""
    root = repo_root or get_project_root()
    target = root / "artifacts" / category / "latest.json"
    payload = {
        "ok": ok,
        "command": command,
        "started_at": started_at,
        "finished_at": finished_at,
        "inputs": dict(inputs),
        "summary": dict(summary or {}),
        "artifacts": [dict(item) for item in artifacts],
        "errors": [dict(item) for item in errors],
    }
    return write_json_file(target, payload)


def abort(message: str, *, exit_code: int = EXIT_CODE_VALIDATION) -> None:
    """Emit a textual error and terminate."""
    typer.echo(f"错误: {message}", err=True)
    raise typer.Exit(code=exit_code)
