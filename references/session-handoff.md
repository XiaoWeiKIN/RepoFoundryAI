# Session Handoff / Resume v1（显式 CLI）

目标：在**同一 Git 工作树**中，将尚未完成的普通 Explore/Build 任务交给下一个会话或 Agent。不会自动创建 ExecPlan、Checkpoint、ADR、验证 Receipt 或新的任务权威。已有 Governed EP 的正式状态、Spec 激活与写入门禁仍以现有工具为准。

实现：发行包 `scripts/session_handoff.py`（Python 3.10+，标准库），按需调用。默认无 Hook、无后台进程、无项目配置；本功能不要求安装任何 Agent adapter。首次版本仅支持同一工作树的本地交接，不声明跨设备/跨克隆兼容。

## 捕获

在目标仓库根目录运行，替换发行包目录及任务内容：

```bash
python3 -B <distribution>/scripts/session_handoff.py --repo . capture \
  --task "修复游标边界错误" \
  --next-action "运行游标回归测试" \
  --path src/cursor.py \
  --evidence "pytest tests/test_cursor.py（仅为引用，非已验证结果）"
```

默认只向 stdout 输出 JSON，**不写入文件**。要明确保存交接，先准备好仓库外的私有目录，再使用 `--output`：

```bash
python3 -B <distribution>/scripts/session_handoff.py --repo . capture \
  --task "修复游标边界错误" --next-action "运行游标回归测试" \
  --output /tmp/cursor-handoff.json
```

输出文件只能新建，不覆盖现有文件，权限为 `0600`。不自动建目录，也不提交 Git。推荐把文件放在目标仓库外，以避免保存记录本身造成工作树变化。任务、阻塞和证据引用是操作者输入的说明，可能含敏感信息，须使用可信的本地存储与保留策略。

捕获的版本化 JSON 包括：

- 任务与精确下一步、人工提供的阻塞项和证据指针（最多各 16 个）。
- 当前 checkout 的绝对根路径、Git 分支及 HEAD。
- `git status --porcelain=v1 -z --untracked-files=all` 的可见变化、重命名来源、变化文件的当前字节 SHA-256。
- 用户额外通过 `--path` 指定的工作文件摘要（包括没有修改的文件）；对于 symlink 仅哈希链接文本，不读取外部目标。
- 记录自身的 SHA-256，用于识别意外损坏。**摘要不是身份认证、代码验证或 Owner 授权**。

观察范围有意有限：Git 忽略的其他文件、远程状态、未列出的外部系统、实际模型上下文、Spec 生效条件以及先前测试的真实性，不在本次快照中。

## 恢复

```bash
python3 -B <distribution>/scripts/session_handoff.py --repo . resume \
  --input /tmp/cursor-handoff.json
```

只读重新读取当前 HEAD、分支、可见变更与所有先前观察文件。输出：

| 字段 | 含义 |
|---|---|
| `state: matching_snapshot` | 在**列明的观察范围内**，当前 checkout 与交接时一致 |
| `state: stale` | Checkout、HEAD、分支、状态或观察文件字节不同；列出确切原因 |
| `verification: unknown` | 快照一致，但**不能证明测试通过** |
| `verification: stale` | 快照不一致，先前引用不能作为当前代码的有效验收 |
| `source_integrity: digest_checked_not_authenticated` | JSON 自摘要匹配；没有证明写入者身份或事实真实性 |

退出码 `0` 表示快照一致，`1` 表示 stale，`2` 表示非法记录、来源不可读或观察不完整。**退出码 0 不代表任务完成、测试通过或 Spec 已激活。**

Resume 只能提供下一步和风险提示；下一个 Agent 必须依照仓库真实代码、当前 Spec Router 和工作流重新建立任务上下文。对于已归档或受治理的内容，仍从权威 EP、ADR 和密封证据解析，不把 Handoff 当作替代物。

## 安全及兼容边界

- 只读捕获（不带 `--output`）和恢复不应修改工作树。无隐式外部网络请求。
- 拒绝路径越界、源文件的 symlink 父目录、输入/输出文件 symlink、损坏 JSON、重复字段、未来 schema 与超出大小限制的输入。快照在捕获前后独立重放；观测到漂移即报错。
- 对未提交变更和非忽略的 untracked 文件执行内容摘要核对；对 Git 已忽略的未声明文件不作完整性保证。普通任务如依赖忽略文件，可显式添加 `--path`。
- 捕获与恢复均不执行验证命令，也不重新激活 Requirements。Codex 的原生 Spec Hook 和 Claude/Portable 的 CLI/advisory 保障强度保持不变。
- 此 v1 不是跨机器共享协议，不是完整工作区的事务快照，也没有并发恶意修改者隔离。
- 下一阶段的 Revision-bound Verification Receipt 可负责记录实际运行的测试、完整变更身份和 Spec 版本。本 v1 **不声称该能力已经实现**。

对应原有 [Issue #87](https://github.com/XiaoWeiKIN/RepoHarnessKit/issues/87) 的第二阶段。与现有 `context_resume` 的关系：后者恢复规范化 Core 路由与 Capsule；本 CLI 恢复**人工任务进度描述及可核验的 Git 快照**，两者不互相替代。
