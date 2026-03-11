# TASK BRIEF

## 需求摘要

- AI-first scaffold workspace for developing and iterating option strategies.
- 当前策略聚焦 `option-universe`，按 `standalone` 运行
- 默认优先在 Editable Surface 内完成改动，只有确有必要时再扩展焦点

## 首选修改入口

- `src/strategy/strategy_entry.py`
- `src/strategy/application`
- `src/strategy/domain`
- `config/strategy_config.toml`
- `config/general/trading_target.toml`
- `config/domain_service`

## 禁止改动边界

- `.codex`
- `.git`
- `.venv`
- `.pytest_cache`
- `.hypothesis`
- `temp`
- `LICENSE`

## 验收要求

- 概述: AI-first scaffold workspace for developing and iterating option strategies.
- 最小测试命令: `option-scaffold focus test`
- Focus navigation files are refreshed and point to the current manifest.
- Validation command succeeds for the current strategy configuration.
- Focus smoke tests pass for the current strategy.

## 关键日志 / 产物

### 关键日志

- `校验通过`
- `诊断完成`
- `已刷新策略焦点导航`

### 关键产物

- `.focus/SYSTEM_MAP.md`
- `.focus/ACTIVE_SURFACE.md`
- `.focus/TASK_BRIEF.md`
- `.focus/COMMANDS.md`
- `.focus/TASK_ROUTER.md`
- `.focus/TEST_MATRIX.md`
- `.focus/context.json`
