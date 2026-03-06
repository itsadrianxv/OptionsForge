# Persistence 模块职责边界

`src/strategy/infrastructure/persistence` 只承载两类能力：

1. 策略状态持久化
- 快照序列化与反序列化
- 状态保存、加载、完整性校验、压缩与清理
- 自动保存调度与后台写入

2. 策略重启信号恢复所需的历史回放
- 从数据库加载历史 Bar 并通过回调回放
- 用于策略重启后重新计算状态/信号

## 当前保留组件

- `state_repository.py`
- `auto_save_service.py`
- `json_serializer.py`
- `history_data_repository.py`
- `exceptions.py`
- `model/strategy_state_po.py`

## 不应放入本目录的组件

- 监控系统 PO 与监控快照写入逻辑（应放 `infrastructure/monitoring`）
- 某个执行器/调度器的特化状态序列化器
- 兼容过渡导出层（如别名转发模块）
