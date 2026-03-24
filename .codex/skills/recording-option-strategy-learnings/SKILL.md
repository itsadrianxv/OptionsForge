---
name: recording-option-strategy-learnings
description: Use when turning plan mode conversations into reusable docs/learnt notes about option strategy edge cases, execution ownership, state ambiguity, or non-obvious risk controls.
---

# Recording Option Strategy Learnings

## Overview

把 plan mode 里的策略讨论沉淀成可复用知识，而不是会话流水账。核心原则是先保留语义边界，再写结论；先写失败风险，再写建议动作。

如果讨论里出现 STM、bucket、claim、冻结量、在途覆盖、未同步成交、持仓吸收、可用仓位等词，这个 skill 往往适用。

## When to Use

- 用户要“记录学到的东西”“整理 plan mode 对话”“沉淀策略细节考量”
- 讨论涉及 option strategy 的非显然约束，而不是单纯 API 用法
- 你需要把一句经验判断展开成场景拆分、设计规则和验证项
- 讨论里存在“同样的账户表象，对策略含义不同”的情况

不要用于：

- 普通会议纪要
- 纯实现日志
- 不涉及策略细节的通用产品文档

## Workflow

1. 先提炼触发问题，明确争议点是什么。
2. 做场景拆分，不要把不同语义的状态压成一个结论。
3. 对每个场景分别写清：
   - 外部账户视角看到了什么
   - STM 自身还持有什么在途状态
   - 当前动作能不能做
   - 为什么
4. 单独写出“错误捷径”。
   - 例如把 `available == 0` 直接等价为“可以 release claim / bucket”
5. 写出最小安全规则，明确 release、handoff、补单、回收 claim 的前置条件。
6. 落到 `docs/learnt/YYYY-MM-DD-<topic>.md`，语言跟随当前对话语言。

优先查看 [references/extraction-checklist.md](references/extraction-checklist.md)，再按 [references/entry-template.md](references/entry-template.md) 成文。

## Focus Points

- 语义边界：同一个“冻结归零”结论，可能对应不同业务状态
- 所有权：订单、成交、claim、bucket 当前归谁负责收尾
- 状态归属：哪些量属于外部冻结，哪些量属于 STM 自有在途覆盖
- 快照不足以判断：账户快照不能替代策略内生命周期
- 延迟吸收：未同步成交在被持仓吸收前，不能当作已经收尾
- 释放条件：release 之前必须确认没有 STM 自己的尾巴
- 回归用例：至少覆盖“只有外部冻结”和“外部冻结 + STM 在途”两类

## Output Contract

输出文档至少包含以下部分：

```markdown
# 标题

## 触发问题
- 这次在问什么

## 场景拆分
- 场景 A：...
- 场景 B：...

## 设计规则
- 不变量 / 前置条件 / release 规则

## 忽略后的风险
- 提前释放 claim
- 状态归属混乱
- 其他流程错误接管

## 验证清单
- 回归用例
- 待补监控
- 待确认问题
```

## Red Flags

- 直接把对话改写成时间顺序摘要
- 没有场景拆分，只写一句“应该怎么做”
- 把 `available == 0`、`short_frozen > 0`、`义务已被覆盖` 混成同义词
- 没有区分外部冻结和 STM 自有在途覆盖
- 没写 claim / bucket 的释放条件
- 没有列出验证用例

这些都说明记录还停留在“听懂了”，没有沉淀成“以后还能用”。

## Pressure Scenarios

1. 账户可用义务已经变成 0，但 STM 没有任何挂单。检查是否能明确写成“可以 release”。
2. 账户可用义务已经变成 0，但 STM 仍有 SPECIAL 覆盖单或未吸收成交。检查是否能阻止“立即 release”这种错误捷径。
3. 用户只给了一小段对话。检查是否仍能提炼出语义边界、失败风险和验证项，而不是退化成摘抄。

如果当前环境不能使用子代理，就显式说明完整压力测试未执行，并至少完成一次手工清单复核。

## Common Mistakes

- 只记“结论”，不记“为什么这个结论只在某个场景成立”
- 只记业务意图，不记状态归属和生命周期边界
- 只记规则，不记违反规则会造成什么错误
- 只记一个 happy path，不记相邻的反例
