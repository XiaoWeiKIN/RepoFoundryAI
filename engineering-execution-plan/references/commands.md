# epctl 命令与兼容操作

仅在需要命令示例、历史恢复或兼容处理时查阅。参数以 `epctl.py --help` 为准。

把 `<skill-dir>` 解析为本 skill 所在目录。所有命令在目标仓库根目录运行：

```bash
python3 <skill-dir>/scripts/epctl.py --repo . init
python3 <skill-dir>/scripts/epctl.py --repo . register-architecture-root \
  docs/design-docs

python3 <skill-dir>/scripts/epctl.py --repo . new-adr \
  --slug cache-topology --title "Choose cache topology" --research R-001 \
  --author "Codex" --owner "Cache Platform Owner" \
  --depends-on ADR-004 --amends ADR-003 \
  --amends-constraint ADR-003#C-002 \
  --design docs/design-docs/cache-topology.md
python3 <skill-dir>/scripts/epctl.py --repo . decide-adr ADR-001 \
  --outcome accepted --decision-maker "<explicit authority>"
python3 <skill-dir>/scripts/epctl.py --repo . transition-adr ADR-001 \
  --to under_review --decision-maker "<explicit authority>" \
  --reason "<new evidence>"
python3 <skill-dir>/scripts/epctl.py --repo . supersede-adr ADR-001 \
  --by ADR-002 --decision-maker "<explicit authority>" \
  --reason "<replacement rationale>"
python3 <skill-dir>/scripts/epctl.py --repo . register-adr-revision ADR-001 \
  --from-file evidence/adr-001-historical.md
python3 <skill-dir>/scripts/epctl.py --repo . register-adr-revision ADR-001 \
  --from-file evidence/adr-001-historical.md --apply

python3 <skill-dir>/scripts/epctl.py --repo . \
  register-checkpoint-recovery EP-001 CP-001 \
  --from-git-commit <full-ancestor-commit> \
  --attested-by "<explicit actor>" \
  --reason "<why the seal was invalid when introduced>"
python3 <skill-dir>/scripts/epctl.py --repo . \
  register-checkpoint-recovery EP-001 CP-001 \
  --from-git-commit <full-ancestor-commit> \
  --attested-by "<explicit actor>" \
  --reason "<why the seal was invalid when introduced>" --apply

python3 <skill-dir>/scripts/epctl.py --repo . adr-health --json
python3 <skill-dir>/scripts/epctl.py --repo . adr-maintenance --json
python3 <skill-dir>/scripts/epctl.py --repo . adr-maintenance --check
python3 <skill-dir>/scripts/epctl.py --repo . set-decision-view runtime \
  --title "Runtime decisions" --adr ADR-004 --adr ADR-005
python3 <skill-dir>/scripts/epctl.py --repo . set-decision-view runtime \
  --title "Runtime decisions" --adr ADR-004 --adr ADR-005 --apply
python3 <skill-dir>/scripts/epctl.py --repo . decision-capsule \
  --view runtime --constraint ADR-005#C-002 --json
python3 <skill-dir>/scripts/epctl.py --repo . decision-capsule \
  --view runtime --constraint ADR-005#C-002 \
  --materialization focused --focus-reason "Implement the selected boundary" \
  --json
python3 <skill-dir>/scripts/epctl.py --repo . adr-consolidation-plan \
  --view runtime --json
python3 <skill-dir>/scripts/epctl.py --repo . pack-historical-adrs \
  ADR-051 ADR-052 --packed-by "<explicit actor>" \
  --reason "<why these terminal files should be compacted>"
python3 <skill-dir>/scripts/epctl.py --repo . pack-historical-adrs \
  ADR-051 ADR-052 --packed-by "<explicit actor>" \
  --reason "<why these terminal files should be compacted>" --apply
python3 <skill-dir>/scripts/epctl.py --repo . unpack-adr-history-pack \
  sha256-<pack>.json --unpacked-by "<explicit actor>" \
  --reason "<recovery or downgrade reason>"

python3 <skill-dir>/scripts/epctl.py --repo . new-ep \
  --slug implement-cache --title "Implement cache topology" \
  --author "Codex" --owner "Cache Platform Owner" \
  --research R-001 --adr ADR-004 --adr ADR-005 \
  --design docs/design-docs/cache-topology.md \
  --architecture-entrypoint docs/design-docs/index.md \
  --benchmark-scenario BS-003 \
  --benchmark-scenario BS-004

python3 <skill-dir>/scripts/epctl.py --repo . validate
python3 <skill-dir>/scripts/epctl.py --repo . validate --fix-index
python3 <skill-dir>/scripts/epctl.py --repo . reindex
python3 <skill-dir>/scripts/epctl.py --repo . status
```

重复引用时重复写 `--research`、`--adr`、`--design` 或
`--benchmark-scenario`。注册信息写入
`docs/.epctl/config.json`，本地和 CI 因而使用同一组 architecture roots。如果某个
Gate 不需要正式制品：

```bash
python3 <skill-dir>/scripts/epctl.py --repo . new-ep \
  --slug local-cleanup --title "Clean up local adapter" \
  --research-not-required-reason "<specific existing evidence>" \
  --decision-not-required-reason "<why no durable choice exists>" \
  --architecture-not-applicable-reason "<why no existing architecture input applies>"
```

- 先运行 `init`；它只补缺失目录和索引，不覆盖已有内容。
- 用脚本分配 ADR/EP 等本 skill 拥有的 ID、复制 assets、迁移状态、封存
  payload、重建索引和验证引用。不要手工猜编号。
- `.epctl/state.json` 保存编号高水位。故障可以造成跳号，不能复用旧 ID。
- completed/cancelled EP 引用的旧 ADR payload 不再等于当前 ADR 时，先用
  `register-adr-revision` 预览，再以 `--apply` 写入 digest-addressed 的不可变
  repository evidence。也可以显式使用 `--from-git-blob <full-object-id>` 恢复
  Git blob；正常 `validate` 只读仓库文件，不依赖 Git。
- schema 1.2 Checkpoint 的 seal 若在首次引入该精确路径的 Git commit 中就已错误，
  不得改写历史文件。使用 `register-checkpoint-recovery` 预览并登记
  content-addressed receipt；工具只接受唯一错误为 payload mismatch、commit 为
  `HEAD` 祖先、父 commit 不含该路径且 commit blob 与当前原始字节完全一致的
  checkpoint。正常 `validate` 离线验证 receipt 与当前字节，不重新调用 Git。
- `validate --fix-index` 只修复派生索引，不改事实制品。
- 升级 RepoFoundry 后先运行 `reindex`；它会把旧 `Proposed` / `Decided` ADR 索引
  转为 Proposed / Effective / Review Required / Historical，并保留受管区域之外的
  人工内容。重复运行应无 diff。
- 脚本不可用时按 `assets/` 模板执行，并扫描文件系统、索引和高水位后取最大 ID +1。
- 不要求目标仓库使用 Git。
