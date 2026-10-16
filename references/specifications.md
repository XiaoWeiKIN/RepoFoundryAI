# 管理 Engineering Specs

所有写操作默认只预览：

```bash
python3 <repo-foundry-ai-dir>/scripts/foundryctl.py --repo . spec plan
python3 <repo-foundry-ai-dir>/scripts/foundryctl.py --repo . \
  bootstrap --adapter codex --governance-profile adaptive \
  --spec languages/go --apply
python3 <repo-foundry-ai-dir>/scripts/foundryctl.py --repo . spec sync --apply
python3 <repo-foundry-ai-dir>/scripts/foundryctl.py --repo . \
  spec update --spec-version 1.9.0 --spec languages/go --apply
python3 <repo-foundry-ai-dir>/scripts/foundryctl.py --repo . spec validate
```

默认 Catalog 来自
`https://github.com/XiaoWeiKIN/EngineeringSpecifications.git`，默认固定版本为
`1.9.0`。`--spec-version MAJOR.MINOR.PATCH` 规范化为
`refs/tags/vMAJOR.MINOR.PATCH`，解析器必须验证 tag 与 `catalog_version` 一致。
首次初始化可用 `--spec-repository` 选择其他仓库；`--spec-ref` 只用于显式开发
分支、tag 或 commit。manifest 保存 Git URL/ref。`sync` 使用已有 lock 的 commit；
生产升级通过 `update --spec-version ...` 替换 source 并刷新已选内容，不会因检测
结果改变选择。Catalog 发生变化且出现尚未配置的可选 Spec 时，dry-run 的
`selection_decision.status` 为 `required`；必须向用户展示每个 candidate 的 ID、
描述和依赖，并让用户明确选择完整 `--spec` 集合、`--required-only` 或
`--keep-selection`。在用户作答前不得传 `--apply`，也不得替用户推断
`--keep-selection`。`update --spec ...` 预览并替换完整可选集合，
`--required-only` 回到仅必选集合；`--keep-selection` 明确保留既有直接选择。
依赖闭包自动补齐。`spec validate` 完全离线。Bootstrap
不替换漂移的托管文件；显式 `spec sync/update --apply` 才能在预览后恢复
`docs/agent-guides/managed/`。

## 交互理解激活流程

需要查看路径如何匹配候选、Requirement 如何引入依赖、capsule 实际包含什么时，
使用 [Spec 激活解释界面](spec-activation-explainer.md)。它复用本地 Router 的读取与
编译函数，不创建 receipt，也不替代正式激活、授权或交接。

要把同一份预览导出为图、离线 HTML、p5.js 交互视图或可选 Remotion 源码包，
使用 [Explanation IR 与多种阅读界面](explanation-surfaces.md)。输出默认先预览，
显式应用后写入新的可丢弃目录，不改变规范或激活状态。

## Spec Tag 驱动的 RF 发行

正式 Catalog Tag 发布后，EngineeringSpecifications 的
`notify-rf-on-spec-tag` 工作流通过 `repository_dispatch` 通知 RF。
RF 的 `release-rf-from-spec-tag` 工作流独立验证远端 annotated Tag、
所属 main 提交及 Catalog/Spec 摘要。仅在新版本高于当前默认 Catalog 时，
才准备新的 RF patch 版本、修改默认 Spec pin，并运行完整仓库检查、
Node 视图测试及使用真实 Spec 的临时项目 Bootstrap/Validate。
任何步骤失败都停止，不发布 RF Tag。

全部验证通过后，由同一受控工作流提交 RF 版本变更、发布独立的
annotated RF Tag 和 GitHub Release。重复事件不得回退 Catalog，也不应
创建重复版本。RF 使用内置 `GITHUB_TOKEN` 发布的提交不会触发其他
push CI，因此发布工作流自身必须完成上述检查。
旧版一次性 `publish-0.15.0` 工作流仍保留历史发布身份。

跨仓库通知需要在 **EngineeringSpecifications** 的 GitHub Actions
Secrets 配置 `RF_DISPATCH_TOKEN`，权限仅限 **RepoFoundryAI / Contents:
Read and write**。缺少凭据时 Spec Tag 仍有效，但事件通知失败；
修复后可对已发布的 Spec Tag 手动触发通知工作流重试。
如果 Spec Tag 是被默认 `GITHUB_TOKEN` 的发布工作流创建，
发布者需在成功验证 Tag 后显式调用该 `workflow_dispatch` 入口，
因为 GitHub 不会为该 Token 创建的 Tag 再触发普通 push 工作流。

此链路不自动迁移已有项目的 Spec manifest/lock。发生兼容性失败时
不会生成新的 RF Tag，应修复消费端并重新验证。
