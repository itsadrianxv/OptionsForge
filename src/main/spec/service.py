from __future__ import annotations

from dataclasses import replace
import json
from pathlib import Path
import tomllib

from src.main.focus.service import DEFAULT_PACK_KEYS
from src.main.scaffold.catalog import (
    CAPABILITY_OPTION_ORDER,
    CAPABILITY_ORDER,
    derive_capabilities,
    get_preset,
    resolve_capability_options,
    slugify,
)
from src.main.scaffold.config_params import (
    ConfigOverride,
    apply_config_overrides,
    build_all_config_param_schemas,
    build_available_config_param_schemas,
    build_default_config_payload,
    get_config_value,
)
from src.main.scaffold.models import CapabilityKey, CapabilityOptionKey, CreateOptions, ScaffoldPlan

from .models import SpecAcceptance, SpecLogic, SpecScaffold, SpecStrategy, StrategySpec

DEFAULT_SPEC_FILENAME = "strategy_spec.toml"

DEFAULT_ENTRY_RULES: tuple[str, ...] = (
    "Define the minimum market state needed before opening a position.",
    "Describe the signal threshold or pattern that triggers entry.",
)
DEFAULT_EXIT_RULES: tuple[str, ...] = (
    "Describe profit-taking and stop-loss conditions.",
    "State when positions must be flattened before expiry or session close.",
)
DEFAULT_SELECTION_RULES: tuple[str, ...] = (
    "Describe how the underlying and option chain are chosen.",
    "Explain strike, expiry, and option type preferences.",
)
DEFAULT_SIZING_RULES: tuple[str, ...] = (
    "Define the maximum position count and per-trade capital usage.",
)
DEFAULT_RISK_RULES: tuple[str, ...] = (
    "State hard limits for margin, Greeks, or portfolio concentration.",
)
DEFAULT_HEDGING_RULES: tuple[str, ...] = (
    "Describe whether Delta or Vega hedging is enabled and when it should trigger.",
)
DEFAULT_OBSERVABILITY_NOTES: tuple[str, ...] = (
    "List the key decisions and signals that must appear in logs or monitoring.",
)
DEFAULT_TEST_SCENARIOS: tuple[str, ...] = (
    "Validate generated contracts and strategy imports.",
    "Validate configuration and focus navigation assets.",
    "Run focus smoke tests for enabled packs.",
)
DEFAULT_COMPLETION_CHECKS: tuple[str, ...] = (
    "Focus navigation files are refreshed and point to the current manifest.",
    "Validation command succeeds for the current strategy configuration.",
    "Focus smoke tests pass for the current strategy.",
)

CAPABILITY_TO_PACKS: dict[CapabilityKey, tuple[str, ...]] = {
    CapabilityKey.SELECTION: ("selection",),
    CapabilityKey.POSITION_SIZING: ("risk",),
    CapabilityKey.PRICING: ("pricing",),
    CapabilityKey.GREEKS_RISK: ("risk",),
    CapabilityKey.EXECUTION: ("execution",),
    CapabilityKey.HEDGING: ("hedging",),
    CapabilityKey.MONITORING: ("monitoring", "web"),
    CapabilityKey.OBSERVABILITY: ("monitoring",),
}


def default_spec_path(repo_root: Path) -> Path:
    return repo_root / DEFAULT_SPEC_FILENAME


def _ensure_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"`{field_name}` must be a non-empty string.")
    return value.strip()


def _ensure_string_tuple(value: object, field_name: str) -> tuple[str, ...]:
    if value is None:
        return ()
    if not isinstance(value, list):
        raise ValueError(f"`{field_name}` must be an array of strings.")
    items: list[str] = []
    for item in value:
        if not isinstance(item, str) or not item.strip():
            raise ValueError(f"`{field_name}` contains an empty string.")
        items.append(item.strip())
    return tuple(items)


def _parse_capabilities(value: object) -> tuple[CapabilityKey, ...]:
    raw_items = _ensure_string_tuple(value, "scaffold.capabilities")
    return tuple(CapabilityKey(item) for item in raw_items)


def _parse_options(value: object) -> tuple[CapabilityOptionKey, ...]:
    raw_items = _ensure_string_tuple(value, "scaffold.options")
    return tuple(CapabilityOptionKey(item) for item in raw_items)


def _flatten_config(prefix: str, payload: dict[str, object]) -> tuple[ConfigOverride, ...]:
    overrides: list[ConfigOverride] = []
    for key, value in payload.items():
        dotted_key = f"{prefix}.{key}" if prefix else key
        if isinstance(value, dict):
            overrides.extend(_flatten_config(dotted_key, value))
            continue
        overrides.append(ConfigOverride(key=dotted_key, value=value))
    return tuple(overrides)


def _config_payload_to_overrides(
    config_payload: dict[str, object],
    *,
    preset_key: str,
    enabled_options: tuple[CapabilityOptionKey, ...],
) -> tuple[ConfigOverride, ...]:
    preset = get_preset(preset_key)
    available_schemas = build_available_config_param_schemas(preset, enabled_options)
    available = {schema.key for schema in available_schemas}
    baseline_payload = build_default_config_payload(preset, enabled_options)
    baseline = {
        schema.key: get_config_value(baseline_payload, schema.key)
        for schema in available_schemas
    }

    overrides = []
    for item in _flatten_config("", config_payload):
        if item.key not in available:
            raise ValueError(f"Unknown `config` key in strategy spec: {item.key}")
        if item.value == baseline.get(item.key):
            continue
        overrides.append(item)
    return tuple(overrides)


def pack_keys_from_spec(spec: StrategySpec) -> tuple[str, ...]:
    if spec.acceptance.focus_packs:
        requested = spec.acceptance.focus_packs
    else:
        derived: list[str] = ["kernel"]
        for capability in spec.scaffold.capabilities:
            derived.extend(CAPABILITY_TO_PACKS.get(capability, ()))
        requested = tuple(dict.fromkeys(derived))

    resolved: list[str] = []
    for key in DEFAULT_PACK_KEYS:
        if key in requested and key not in resolved:
            resolved.append(key)
    for key in requested:
        if key not in resolved:
            resolved.append(key)
    return tuple(resolved or ("kernel",))


def load_strategy_spec(repo_root: Path, spec_path: Path | None = None) -> StrategySpec:
    target = spec_path or default_spec_path(repo_root)
    if not target.exists():
        raise FileNotFoundError(f"Strategy spec not found: {target}")

    raw = tomllib.loads(target.read_text(encoding="utf-8"))
    strategy_raw = raw.get("strategy")
    scaffold_raw = raw.get("scaffold")
    logic_raw = raw.get("logic")
    acceptance_raw = raw.get("acceptance")
    config_raw = raw.get("config", {})

    if not isinstance(strategy_raw, dict):
        raise ValueError("Strategy spec is missing `[strategy]`.")
    if not isinstance(scaffold_raw, dict):
        raise ValueError("Strategy spec is missing `[scaffold]`.")
    if not isinstance(logic_raw, dict):
        raise ValueError("Strategy spec is missing `[logic]`.")
    if not isinstance(acceptance_raw, dict):
        raise ValueError("Strategy spec is missing `[acceptance]`.")
    if not isinstance(config_raw, dict):
        raise ValueError("`[config]` must be a table.")

    preset_key = _ensure_string(scaffold_raw.get("preset"), "scaffold.preset")
    preset = get_preset(preset_key)
    capabilities = _parse_capabilities(scaffold_raw.get("capabilities", []))
    include_options = _parse_options(scaffold_raw.get("options", []))
    enabled_options = resolve_capability_options(
        preset,
        capabilities,
        (),
        include_options,
        (),
    )
    resolved_capabilities = derive_capabilities(enabled_options)

    overrides = _config_payload_to_overrides(
        config_raw,
        preset_key=preset_key,
        enabled_options=enabled_options,
    )

    spec = StrategySpec(
        spec_path=target,
        strategy=SpecStrategy(
            name=slugify(_ensure_string(strategy_raw.get("name"), "strategy.name")),
            summary=_ensure_string(strategy_raw.get("summary"), "strategy.summary"),
            trading_target=_ensure_string(strategy_raw.get("trading_target"), "strategy.trading_target"),
            strategy_type=_ensure_string(strategy_raw.get("strategy_type"), "strategy.strategy_type"),
            run_mode=_ensure_string(strategy_raw.get("run_mode"), "strategy.run_mode"),
        ),
        scaffold=SpecScaffold(
            preset=preset_key,
            capabilities=resolved_capabilities,
            options=enabled_options,
        ),
        config_overrides=overrides,
        logic=SpecLogic(
            entry_rules=_ensure_string_tuple(logic_raw.get("entry_rules"), "logic.entry_rules"),
            exit_rules=_ensure_string_tuple(logic_raw.get("exit_rules"), "logic.exit_rules"),
            selection_rules=_ensure_string_tuple(logic_raw.get("selection_rules"), "logic.selection_rules"),
            sizing_rules=_ensure_string_tuple(logic_raw.get("sizing_rules"), "logic.sizing_rules"),
            risk_rules=_ensure_string_tuple(logic_raw.get("risk_rules"), "logic.risk_rules"),
            hedging_rules=_ensure_string_tuple(logic_raw.get("hedging_rules"), "logic.hedging_rules"),
            observability_notes=_ensure_string_tuple(
                logic_raw.get("observability_notes"),
                "logic.observability_notes",
            ),
        ),
        acceptance=SpecAcceptance(
            completion_checks=_ensure_string_tuple(
                acceptance_raw.get("completion_checks"),
                "acceptance.completion_checks",
            ),
            focus_packs=_ensure_string_tuple(acceptance_raw.get("focus_packs"), "acceptance.focus_packs"),
            test_scenarios=_ensure_string_tuple(
                acceptance_raw.get("test_scenarios"),
                "acceptance.test_scenarios",
            ),
        ),
    )
    return spec


def _quote(value: object) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    return str(value)


def _render_config_table(table_name: str, payload: dict[str, object]) -> list[str]:
    lines: list[str] = []
    scalar_items = {
        key: value
        for key, value in payload.items()
        if not isinstance(value, dict)
    }
    nested_items = {
        key: value
        for key, value in payload.items()
        if isinstance(value, dict)
    }
    if scalar_items:
        lines.append(f"[config.{table_name}]")
        for key, value in scalar_items.items():
            lines.append(f"{key} = {_quote(value)}")
        lines.append("")
    for key, value in nested_items.items():
        lines.extend(_render_config_table(f"{table_name}.{key}", value))
    return lines


def _default_logic() -> SpecLogic:
    return SpecLogic(
        entry_rules=DEFAULT_ENTRY_RULES,
        exit_rules=DEFAULT_EXIT_RULES,
        selection_rules=DEFAULT_SELECTION_RULES,
        sizing_rules=DEFAULT_SIZING_RULES,
        risk_rules=DEFAULT_RISK_RULES,
        hedging_rules=DEFAULT_HEDGING_RULES,
        observability_notes=DEFAULT_OBSERVABILITY_NOTES,
    )


def _default_acceptance(plan: ScaffoldPlan) -> SpecAcceptance:
    return SpecAcceptance(
        completion_checks=DEFAULT_COMPLETION_CHECKS,
        focus_packs=pack_keys_from_spec(
            StrategySpec(
                spec_path=plan.project_root / DEFAULT_SPEC_FILENAME,
                strategy=SpecStrategy(
                    name=plan.project_slug,
                    summary=f"{plan.project_name} strategy workspace.",
                    trading_target="option-universe",
                    strategy_type="custom",
                    run_mode="standalone",
                ),
                scaffold=SpecScaffold(
                    preset=plan.preset.key,
                    capabilities=plan.capabilities,
                    options=plan.enabled_options,
                ),
                config_overrides=(),
                logic=_default_logic(),
                acceptance=SpecAcceptance(
                    completion_checks=DEFAULT_COMPLETION_CHECKS,
                    focus_packs=(),
                    test_scenarios=DEFAULT_TEST_SCENARIOS,
                ),
            )
        ),
        test_scenarios=DEFAULT_TEST_SCENARIOS,
    )


def spec_from_plan(plan: ScaffoldPlan) -> StrategySpec:
    return StrategySpec(
        spec_path=plan.project_root / DEFAULT_SPEC_FILENAME,
        strategy=SpecStrategy(
            name=plan.project_slug,
            summary=f"{plan.project_name} strategy workspace.",
            trading_target="option-universe",
            strategy_type="custom",
            run_mode="standalone",
        ),
        scaffold=SpecScaffold(
            preset=plan.preset.key,
            capabilities=plan.capabilities,
            options=plan.enabled_options,
        ),
        config_overrides=plan.config_overrides,
        logic=_default_logic(),
        acceptance=_default_acceptance(plan),
    )


def render_strategy_spec(spec: StrategySpec) -> str:
    lines = [
        "[strategy]",
        f"name = {json.dumps(spec.strategy.name, ensure_ascii=False)}",
        f"summary = {json.dumps(spec.strategy.summary, ensure_ascii=False)}",
        f"trading_target = {json.dumps(spec.strategy.trading_target, ensure_ascii=False)}",
        f"strategy_type = {json.dumps(spec.strategy.strategy_type, ensure_ascii=False)}",
        f"run_mode = {json.dumps(spec.strategy.run_mode, ensure_ascii=False)}",
        "",
        "[scaffold]",
        (
            "capabilities = ["
            + ", ".join(json.dumps(item.value, ensure_ascii=False) for item in spec.scaffold.capabilities)
            + "]"
        ),
        (
            "options = ["
            + ", ".join(json.dumps(item.value, ensure_ascii=False) for item in spec.scaffold.options)
            + "]"
        ),
        f"preset = {json.dumps(spec.scaffold.preset, ensure_ascii=False)}",
        "",
    ]

    if spec.config_overrides:
        payload = build_default_config_payload(get_preset(spec.scaffold.preset), spec.scaffold.options)
        payload = apply_config_overrides(payload, spec.config_overrides)
        for key in ("setting", "runtime", "observability", "position_sizing", "greeks_risk", "order_execution", "advanced_orders", "hedging", "indicator_kwargs", "signal_kwargs"):
            section = payload.get(key)
            if isinstance(section, dict) and section:
                lines.extend(_render_config_table(key, section))

    lines.extend(
        [
            "[logic]",
            (
                "entry_rules = ["
                + ", ".join(json.dumps(item, ensure_ascii=False) for item in spec.logic.entry_rules)
                + "]"
            ),
            (
                "exit_rules = ["
                + ", ".join(json.dumps(item, ensure_ascii=False) for item in spec.logic.exit_rules)
                + "]"
            ),
            (
                "selection_rules = ["
                + ", ".join(json.dumps(item, ensure_ascii=False) for item in spec.logic.selection_rules)
                + "]"
            ),
            (
                "sizing_rules = ["
                + ", ".join(json.dumps(item, ensure_ascii=False) for item in spec.logic.sizing_rules)
                + "]"
            ),
            (
                "risk_rules = ["
                + ", ".join(json.dumps(item, ensure_ascii=False) for item in spec.logic.risk_rules)
                + "]"
            ),
            (
                "hedging_rules = ["
                + ", ".join(json.dumps(item, ensure_ascii=False) for item in spec.logic.hedging_rules)
                + "]"
            ),
            (
                "observability_notes = ["
                + ", ".join(json.dumps(item, ensure_ascii=False) for item in spec.logic.observability_notes)
                + "]"
            ),
            "",
            "[acceptance]",
            (
                "completion_checks = ["
                + ", ".join(json.dumps(item, ensure_ascii=False) for item in spec.acceptance.completion_checks)
                + "]"
            ),
            (
                "focus_packs = ["
                + ", ".join(json.dumps(item, ensure_ascii=False) for item in spec.acceptance.focus_packs)
                + "]"
            ),
            (
                "test_scenarios = ["
                + ", ".join(json.dumps(item, ensure_ascii=False) for item in spec.acceptance.test_scenarios)
                + "]"
            ),
            "",
        ]
    )
    return "\n".join(lines)


def write_strategy_spec(spec: StrategySpec, path: Path | None = None) -> Path:
    target = path or spec.spec_path
    target.write_text(render_strategy_spec(replace(spec, spec_path=target)), encoding="utf-8")
    return target


def create_options_from_spec(
    spec: StrategySpec,
    *,
    destination: Path,
    clear: bool = False,
    overwrite: bool = False,
    force: bool = False,
) -> CreateOptions:
    enabled_set = set(spec.scaffold.options)
    excluded_options = tuple(item for item in CAPABILITY_OPTION_ORDER if item not in enabled_set)
    capability_set = set(spec.scaffold.capabilities)
    excluded_capabilities = tuple(item for item in CAPABILITY_ORDER if item not in capability_set)
    return CreateOptions(
        name=spec.strategy.name,
        destination=destination,
        preset=spec.scaffold.preset,
        include_capabilities=spec.scaffold.capabilities,
        exclude_capabilities=excluded_capabilities,
        include_options=spec.scaffold.options,
        exclude_options=excluded_options,
        use_default=False,
        no_interactive=True,
        force=force,
        clear=clear,
        overwrite=overwrite,
        config_overrides=spec.config_overrides,
    )


def build_test_plan_markdown(
    spec: StrategySpec,
    *,
    validate_summary: str | None = None,
    focus_test_summary: str | None = None,
) -> str:
    validate_summary_text = validate_summary or "Not run yet."
    focus_test_summary_text = focus_test_summary or "Not run yet."
    scenarios = "\n".join(f"- {item}" for item in spec.acceptance.test_scenarios)
    completion_checks = "\n".join(f"- {item}" for item in spec.acceptance.completion_checks)
    logic_sections = [
        ("Entry Rules", spec.logic.entry_rules),
        ("Exit Rules", spec.logic.exit_rules),
        ("Selection Rules", spec.logic.selection_rules),
        ("Sizing Rules", spec.logic.sizing_rules),
        ("Risk Rules", spec.logic.risk_rules),
        ("Hedging Rules", spec.logic.hedging_rules),
        ("Observability Notes", spec.logic.observability_notes),
    ]

    lines = [
        "# TEST.md",
        "",
        "## Test Plan",
        "",
        f"- Strategy: `{spec.strategy.name}`",
        f"- Summary: {spec.strategy.summary}",
        f"- Preset: `{spec.scaffold.preset}`",
        "- Focus Packs: " + (", ".join(f"`{item}`" for item in spec.acceptance.focus_packs) or "`kernel`"),
        "",
        "### Completion Checks",
        "",
        completion_checks,
        "",
        "### Scenarios",
        "",
        scenarios,
        "",
        "### Strategy Logic Notes",
        "",
    ]
    for title, items in logic_sections:
        lines.append(f"#### {title}")
        lines.append("")
        lines.extend(f"- {item}" for item in items)
        lines.append("")

    lines.extend(
        [
            "## Latest Results",
            "",
            f"- validate: {validate_summary_text}",
            f"- focus test: {focus_test_summary_text}",
            "",
        ]
    )
    return "\n".join(lines)
