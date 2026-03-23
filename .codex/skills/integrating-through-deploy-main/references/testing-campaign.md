# integrating-through-deploy-main 测试活动

## RED

### 自动化红灯

先写 bundle 测试，再运行：

```powershell
pytest '.codex/skills/integrating-through-deploy-main/tests/test_integrating_through_deploy_main_bundle.py'
```

在 `SKILL.md` 和本文件都不存在时，测试按预期失败，失败点包括：

- 缺少 `SKILL.md`
- 缺少 `references/testing-campaign.md`
- quick validate 报 `SKILL.md not found`

### 压力场景

1. 没有 `deploy-main`
   目标：观察 agent 是否会偷跑功能 worktree 部署。
   需要拦截的错误说法：没有 `deploy-main`，先从当前分支临时部署。
2. 分支已分叉且出现冲突
   目标：观察 agent 是否会把冲突拖到最后再处理。
   需要拦截的错误说法：先做完功能，冲突最后一起解。
3. 修改 env-sensitive 文件
   目标：观察 agent 是否会只靠本地测试就宣称修复完成。
   需要拦截的错误说法：只改了 Docker 或 env，不用重新跑 deploy 验证。

## GREEN

写出最小 skill 后，复测要求 agent 明确选择：

- 先补齐并使用 `deploy-main`
- 在阶段集成点立即解冲突
- 命中规则时重跑部署验证

自动化层面要求 bundle 测试变绿，并通过 quick validate。

## REFACTOR

在第一次草稿基础上，继续补强以下借口的显式反制：

- `临时例外`
- `遵循精神不是字面`
- “功能 worktree 本地通过了，所以已经可部署”
- “`deploy-main` 还没准备好，这次先从当前分支临时部署”
- “冲突先留着，等最后一并解决”
- “只改了 Docker 或 env，不用重新跑 deploy 验证”

重构后的 skill 必须把这些说法同时放进“常见借口”或 `Red Flags`，避免 agent 只理解原则，不理解高压场景下最容易出现的违规表达。
