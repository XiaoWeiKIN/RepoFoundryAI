# 管理 Engineering Specs

所有写操作默认只预览：

```bash
python3 <repo-foundry-ai-dir>/scripts/foundryctl.py --repo . spec plan
python3 <repo-foundry-ai-dir>/scripts/foundryctl.py --repo . \
  bootstrap --adapter codex --governance-profile adaptive \
  --spec languages/go --apply
python3 <repo-foundry-ai-dir>/scripts/foundryctl.py --repo . spec sync --apply
python3 <repo-foundry-ai-dir>/scripts/foundryctl.py --repo . \
  spec update --spec-version 1.5.0 --spec languages/go --apply
python3 <repo-foundry-ai-dir>/scripts/foundryctl.py --repo . spec validate
```

默认 Catalog 来自
`https://github.com/XiaoWeiKIN/EngineeringSpecifications.git`，默认固定版本为
`1.5.0`。`--spec-version MAJOR.MINOR.PATCH` 规范化为
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
