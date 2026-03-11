# AGENTS_FOCUS.md

> 这是一个开发期上下文文件，写法按 `AGENTS.md` 的风格组织，但不替代根目录 `AGENTS.md`。
> 目标是给人类开发者与 coding agent 提供一份更聚焦、可执行、低噪音的工作指引。

## 目标

本仓库当前优先优化的是：

1. **基于当前大仓进行 vibe coding**
2. **缩短 agent 的阅读 → 修改 → 验证闭环**
3. **尽量让修改先落在最小必要上下文里**

如果没有额外说明，默认按“先聚焦、再改动、先 smoke、后 full”的方式工作。

## 推荐起手式

每次开始开发前，优先执行以下顺序：

1. 运行 `option-scaffold focus refresh`
2. 运行 `option-scaffold focus show`
3. 阅读以下文件：
   - `.focus/SYSTEM_MAP.md`
   - `.focus/ACTIVE_SURFACE.md`
   - `.focus/TASK_BRIEF.md`
   - `.focus/TASK_ROUTER.md`
   - `.focus/TEST_MATRIX.md`
4. 先根据 `TASK_ROUTER` 找到本次任务最相关的 pack 和“首看入口”
5. 默认先跑 `option-scaffold focus test`
6. 只有在 smoke 通过、且确实需要完整回归时，才跑 `option-scaffold focus test --full`

## 工作边界

### 代码阅读优先级

优先阅读顺序如下：

1. 当前 `focus/strategies/*/strategy.manifest.toml`
2. `.focus/TASK_BRIEF.md`
3. `.focus/TASK_ROUTER.md`
4. 当前任务对应 pack 的 owned paths
5. 当前任务对应测试文件

除非必要，不要先通读整个 `src/strategy/domain`。

### 修改边界

- 默认只改 `.focus/ACTIVE_SURFACE.md` 里的 `Editable Surface`
- `Support Surface` 用于阅读、参考、理解调用关系
- `Frozen Surface` 不应修改，除非任务明确要求

如果发现必须超出 Editable Surface 才能完成任务：

1. 先确认是否只是理解问题，而不是确实需要改动
2. 尽量只扩一层，不要大面积扩散修改面
3. 在交付说明里明确写出“为什么需要越界修改”

## 当前 focus 工作流约定

### 导航文件含义

- `SYSTEM_MAP.md`：当前焦点的系统地图与 pack 链路
- `ACTIVE_SURFACE.md`：可改、可参考、禁止改的边界
- `TASK_BRIEF.md`：任务摘要、验收要求、关键产物
- `TASK_ROUTER.md`：任务类型 → 首看入口 → 配置 → 推荐测试
- `TEST_MATRIX.md`：smoke / full / skipped 的测试分层
- `COMMANDS.md`：当前焦点下最常用命令

### 测试约定

- `option-scaffold focus test`
  - 这是默认入口
  - 表示 **smoke 模式**
  - 会默认排除名称中包含 `property` / `pbt` 的测试节点
- `option-scaffold focus test --full`
  - 表示 **full 模式**
  - 用于完整焦点回归
- 如果 pack 因依赖缺失被跳过，以 `TEST_MATRIX.md` 和命令行输出为准

## 开发原则

### 总体原则

- 优先做**最小必要改动**
- 优先修根因，不做表面补丁
- 优先复用现有 focus / pack / scaffold 机制
- 不为了“看起来更整洁”而主动扩大重构范围

### 分层原则

- 领域逻辑留在 `domain` / `application`
- 基础设施细节留在 `infrastructure`
- Web 层只做读取、转换、展示，不承载策略判断
- 回测优先复用主策略契约，不单独复制一套业务逻辑

### 结构原则

- 不要新增 `facade`、`coordinator` 一类中间层
- 上层直接调用具体服务/基础设施即可
- 优先配置驱动，不把阈值和策略参数散落到代码常量里
- 非必要不要引入新的抽象层、全局状态或“万能 helper”

## Pack 维度的默认心智模型

### `selection`

- 负责选标、期权筛选、合约候选集合
- 改这里时，优先看选择逻辑与相关集成测试

### `pricing`

- 负责定价、隐波、Greeks 相关计算
- 改这里时，注意不要把定价逻辑泄漏到 Web 或 execution

### `risk`

- 负责组合风控、限额、暴露控制
- 优先直接修改具体风险服务，不要包一层新的总控对象

### `execution`

- 负责下单、排程、执行细节
- 不要新增 facade/coordinator 风格抽象

### `hedging`

- 负责 Delta / Vega 等对冲逻辑
- 对冲参数优先保持配置化

### `monitoring`

- 负责日志、快照、状态落盘
- 不要把监控持久化细节混入 domain service

### `web`

- 负责读取状态并展示
- 不要把策略判断、信号生成迁移到 Web 层

### `backtest`

- 负责回测入口、参数联动与验证
- 优先共享主策略契约与配置

## 验证策略

默认按下面顺序验证：

1. 先跑与任务最相关的单个测试文件或 `option-scaffold focus test`
2. 如改了配置或契约绑定，再跑 `option-scaffold validate --config config/strategy_config.toml`
3. 如改动影响范围较大，再跑 `option-scaffold focus test --full`

不要一上来整仓全量测试，除非任务明确要求。

## 文档与焦点同步

如果修改影响到 focus 导航的生成逻辑、测试模式、推荐入口或命令文案，需要同步检查：

- `focus/strategies/main/strategy.manifest.toml`
- `.focus/*`
- `README.md`

如果你改了 `src/main/focus/*`，通常应重新执行一次：

```powershell
option-scaffold focus refresh
```

## 建议交付格式

每次交付时，尽量包含以下信息：

1. 改动属于哪个 pack / 子系统
2. 主要修改了哪些入口
3. 跑了哪些验证
4. 是 smoke 通过，还是 full 也通过
5. 是否存在剩余风险或后续建议

## 非目标

本文件不要求：

- 现在就把 `.kiro/specs` 正式接入主工作流
- 重写 `create/init` 主链路
- 大规模重构现有目录结构
- 为了抽象整洁而引入新的中间层

当前优先级仍然是：**让现有 focus 工作流更适合高频、低摩擦的 vibe coding。**
