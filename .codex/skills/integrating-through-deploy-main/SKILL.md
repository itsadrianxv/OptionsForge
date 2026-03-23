---
name: integrating-through-deploy-main
description: Use when working in this option-strategy scaffold across multiple worktrees, integrating changes through deploy-main, resolving merge conflict pressure, handling Docker deployment, or touching env-sensitive changes.
---

# 通过 `deploy-main` 持续集成

## Overview

这个脚手架把“功能开发”和“部署验证”强制分离。

**核心原则：功能 worktree 负责产出变更，`.worktrees/deploy-main` 负责集成、解冲突、验证、部署。**

**违反字面就是违反精神。**
“先临时从当前功能分支部署一下”“先把冲突留到最后”“这次是临时例外”都算违规，不算变通。

## 何时使用

- 需要为这个仓库创建或使用 worktree
- 需要把一个功能分支阶段性并入 `main`
- 合并时出现 merge conflict
- 需要做 Docker 部署或部署验证
- 改动了 `Dockerfile`、`docker-compose*.yml`、`.env*`、部署脚本，或任何读取环境变量的代码

## 硬规则

1. `.worktrees/` 是本项目唯一默认 worktree 根目录。
   创建前必须确认 `.worktrees/` 已被 git 忽略；若未忽略，先修复 `.gitignore` 并提交，再创建 worktree。
2. `.worktrees/deploy-main` 是唯一部署 worktree。
3. `deploy/deploy-main.ps1` 是唯一允许的 Docker 部署入口。
   在功能 worktree 中禁止直接运行 `docker compose`、`docker-compose`、`docker build`。
4. 变更只有在提交已经进入 `.worktrees/deploy-main` 并完成对应验证后，才可以被称为“可部署”或“部署问题已修复”。
5. 如果 `.worktrees/deploy-main` 不存在，先从 `main` 自动补齐并校验，再继续工作。
6. 如果 `deploy/deploy-main.ps1` 缺失，或它不能显式定位 `.worktrees/deploy-main`、`.worktrees/deploy-main/deploy/docker-compose.yml`、`.worktrees/deploy-main/.env`，直接报基础设施 blocker。
   不允许从功能 worktree、仓库根目录或任意临时目录回退部署。

## 标准工作流

### 1. 初始化 worktree

1. 检查 `.worktrees/` 是否已被 git 忽略。
2. 若未忽略，立刻修复 `.gitignore` 并提交。
3. 确保 `.worktrees/deploy-main` 存在且跟踪 `main`。
4. 功能开发一律在 `.worktrees/<branch-slug>` 中进行。

### 2. 阶段集成

默认节奏是**阶段集成**，不是发布前一次性集成。

1. 每完成一个可验证子任务，就在功能 worktree 提交。
2. 将该分支合入 `.worktrees/deploy-main`。
3. 冲突优先在 `deploy-main` 集成时解决，不积压到发布前。
4. 在 `deploy-main` 运行对应验证。
5. 验证通过后推送 `main`。
6. 将最新 `main` 同步回功能 worktree，再继续下一阶段。

## 冲突处理

- 语义明确的冲突由 agent 主动解决，不等待“最后一起处理”。
- 只有在冲突暴露真实产品歧义时才暂停并询问。
- 涉及部署、环境变量、schema、入口脚本的冲突，解决后必须扩大验证范围。
- “先把冲突留着，等最后一并解决”是典型坏味道，不允许当作默认策略。

## 验证矩阵

| 变更类型 | 必做动作 |
| --- | --- |
| 普通代码改动 | 在 `.worktrees/deploy-main` 运行相关测试 |
| 部署或环境敏感改动 | 必须执行 `deploy/deploy-main.ps1` |
| 部署/环境/schema/入口脚本冲突 | 先解冲突，再执行更大范围验证 |

部署或环境敏感改动包括：

- `Dockerfile`
- `docker-compose*.yml`
- `.env*`
- 部署脚本
- 任何读取环境变量的代码

部署验证至少覆盖三项：

1. `docker compose config` 成功
2. 目标服务启动成功
3. 容器内关键环境变量检查成功

## 部署脚本约束

`deploy/deploy-main.ps1` 必须显式定位并校验以下路径：

- `.worktrees/deploy-main`
- `.worktrees/deploy-main/deploy/docker-compose.yml`
- `.worktrees/deploy-main/.env`

它还必须把 Compose project directory 固定到 `.worktrees/deploy-main/deploy`。
任何缺失都要直接报错退出，不能依赖当前 shell 目录兜底。

## 快速判断

| 情况 | 正确动作 |
| --- | --- |
| 新开功能开发 | 在 `.worktrees/<branch-slug>` 工作 |
| `deploy-main` 不存在 | 先补齐 `.worktrees/deploy-main` |
| 功能 worktree 本地测试通过 | 继续并入 `deploy-main` 验证，不得直接宣称可部署 |
| 出现 merge conflict | 在 `deploy-main` 当场解决 |
| 改了 Docker 或 env | 在 `deploy-main` 重跑部署验证 |
| 部署脚本缺失 | 报 blocker，不做回退式部署 |

## 常见借口

| 借口 | 现实 |
| --- | --- |
| “功能 worktree 本地通过了，所以已经可部署” | 本地通过只说明功能 worktree 可用，不说明部署闭环完成 |
| “`deploy-main` 还没准备好，这次先从当前分支临时部署” | 这是回退式部署，直接违规 |
| “冲突先留着，等最后一并解决” | 这会把集成风险堆到最后，违背阶段集成 |
| “只改了 Docker 或 env，不用重新跑 deploy 验证” | 这是典型 env-sensitive changes，必须重跑 |
| “这次是临时例外” | `临时例外` 不是流程，通常只是绕开约束 |
| “我是在遵循精神不是字面” | 违反字面就是违反精神 |

## Red Flags

出现以下念头时，立刻停止并回到标准流程：

- “功能 worktree 本地通过了，所以已经可部署”
- “`deploy-main` 还没准备好，这次先从当前分支临时部署”
- “冲突先留着，等最后一并解决”
- “只改了 Docker 或 env，不用重新跑 deploy 验证”
- “这次是临时例外”
- “我是在遵循精神不是字面”

## 最后规则

如果提交还没进入 `.worktrees/deploy-main`，或者 `deploy-main` 上的验证还没跑完，就不能把它描述为可部署。

如果部署脚本、`deploy-main` worktree、关键路径校验三者里任一缺失，就先修基础设施，不要回退到临时部署。
