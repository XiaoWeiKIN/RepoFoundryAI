# 交互预览 Spec 激活流程

Spec Lab 是实验性的本机阅读界面。输入计划修改的文件路径，选择要探索的
Requirement，然后查看依赖闭包和 Router 实际编译的 context capsule。

它不正式激活规范，不创建 receipt，不运行 Hook，不修改仓库，也不替用户判断
哪些要求在语义上适用。页面中的选择与正式激活是两个独立操作。

## 启动

使用包含本工具的 RF 源码或发行包，在一个**已经安装并锁定 Engineering Specs**
的目标仓库上运行。工具不会为缺少 Specs 的仓库自动 bootstrap。

```bash
python3 -B <repo-foundry-ai-dir>/scripts/explain_spec_activation.py --repo <target-repository>
```

终端会输出带随机访问令牌的 `http://127.0.0.1:<port>/#<token>` 地址。把完整地址
复制到本机浏览器。不要转发该地址，不要把服务代理到公网。`Ctrl-C` 停止服务。
不需要 Node、前端构建步骤、外部字体、CDN 或 API key；服务只绑定 IPv4 loopback。

在页面中输入最多 8 个精确路径，每行一个。可以输入尚未创建的文件，例如
`service/main.go`，但原型不展开目录或通配符。占位路径只是输入示例，不表示目标
仓库中存在该文件，也不表示目标仓库安装了 Go 规范。

```mermaid
flowchart LR
    P["计划路径"] --> C["Router 路径匹配候选"]
    C --> S["用户选择预览项"]
    S --> D["Router 依赖闭包"]
    D --> T["精确原文 capsule"]
    T --> V["字节数、摘要与来源"]
    V -. "不创建 receipt" .-> H["正式激活仍走原工作流"]
```

## 阅读界面

候选卡片显示 Spec 的路径范围和 Requirement 的 Activation 提示。这些卡片用于
导航，不是规范原文。空选择不会被记成正式的 `none` 决定。

依赖图的箭头从 Requirement 指向它所需的 Requirement。完整列表同时显示 direct
与 context dependency、源码字节范围及摘要。超过 24 个节点时只展示完整列表，
不缩减依赖闭包或 capsule。没有 Requirement 索引的旧规范可用 whole-Spec 模式
预览；其依赖按 Router 的整份规范规则展开。重复覆盖会被拒绝。

capsule 直接使用发行包内 Router 5 / protocol 2 的编译结果，包括解释框架、选中
Requirement、依赖原文和 Verification 行。默认预算为 32 KiB，可在页面上降低。
超限、摘要漂移或元数据在读取过程中变化时，预览失败；工具不截断原文，也不扩大
正式激活预算。卡片展示不是向模型交付上下文，不替代 Router 的 card-budget 校验。

## 来源与有效期

每次请求重新读取并验证本地 Spec 源。页面标明 Catalog revision、Router 版本与
源码摘要、本地 Git HEAD、dirty 状态、检查时间和本次源集合的 SHA-256。

HEAD 只标识提交，不能单独代表含未提交修改的工作树。源集合摘要绑定本次读取的
manifest、lock、Requirement index 和 Spec 文件；它也不是整个仓库的快照。
没有 Git 信息时显示 unknown，不假装仓库 clean。

页面没有后台刷新或持续漂移检测。源变化后重新检查路径。输入路径变化时，旧选择
和旧 capsule 立即撤下。较早返回的网络请求不能覆盖较新的预览。

## 一次性 JSON 预览

用于排查或比较原文时，可以只输出一次 JSON，不启动 HTTP 服务：

```bash
python3 -B <repo-foundry-ai-dir>/scripts/explain_spec_activation.py \
  --repo <target-repository> --json --path service/main.go
```

从实际返回的卡片中选取 Requirement ID，再加入重复的 `--requirement ID`。
旧规范使用 `--whole-spec ID`。`--budget-bytes` 允许 1 到 32768 字节。
不要使用示例 ID 冒充目标仓库的真实要求。

JSON 和 HTML 都是可丢弃的派生说明，没有审批权限或证据封存含义。未提供正式激活
所需的 per-Requirement reason，也未执行路径变更 audit。完成阅读后仍按原工作流
运行 begin、适用性判断、activate、验证与交接。

## 实现和验证边界

入口是 [explain_spec_activation.py](../scripts/explain_spec_activation.py)，页面是
[spec-activation.html](../assets/explain/spec-activation.html)。工具只导入本发行包的
[共享 Router](../assets/core/engineering-specs/spec_router.py)，不执行目标仓库中的
Router 文件，也不在 JavaScript 中重写路径匹配或 capsule 编译算法。

本机 API 要求匹配的 Host、Origin 和随机令牌，禁止跨域读取，不提供任意文件服务，
也没有写入接口。源文本经 JSON 传递，前端用 textContent 显示。页面使用 CSP，
不运行规范中的 HTML 或脚本。这是本机开发工具，不是多用户托管服务或安全沙箱。

运行新增测试或完整仓库检查：

```bash
python3 -B -m unittest discover -s tests -p test_spec_activation_explainer.py -v
python3 -B scripts/check.py
```

测试使用明确标记的 Catalog fixture，覆盖 canonical Router 字节一致性、根路径、
空选择、legacy whole-Spec、无关要求、超限、源漂移、符号链接、元数据竞争、只读性
和本机 API 边界。它们不证明模型遵守了规范，也不测量读者理解效果。

本原型不增加 Skill、Catalog Spec、Harness schema、Core seed 或生命周期状态。
没有发布新版本，也没有在用户环境中安装服务。HTML/JSON 只在用户请求时生成；
本轮不包含视频、语音、全仓库仪表盘或浏览器中的正式激活功能。
