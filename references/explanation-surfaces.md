# 从同一份解释数据生成不同阅读界面

这是基于 Spec Lab 的实验性输出工具。它把 Router 的只读预览编译成一个
`repofoundry.explanation/v1` JSON，再从同一组事实、来源和限制生成 Mermaid、
HTML、p5.js 阅读界面或 Remotion 源码包。它不新增专业 Skill，也不修改 Harness、
Catalog、receipt 或制品生命周期。

v1 的生产者只支持 **Spec 激活预览**。它不会自动理解任意 ADR、Research 或
Benchmark；没有可靠提取器时，不能用猜测填充通用的 claim 或 causal link。
这不是新的规范或经过批准的决策模型，也不承诺本实验格式已经稳定。

## 直接从目标项目预览

目标项目必须已经安装、锁定 Engineering Specs。路径示例不表示项目一定有 Go
规范；先在 Spec Lab 中检查实际候选和 Requirement ID。

```bash
python3 -B <repo-foundry-ai-dir>/scripts/explain.py formats
python3 -B <repo-foundry-ai-dir>/scripts/explain.py spec \
  --repo <target-repository> --path service/main.go \
  --format html --output /tmp/rf-reading-view
```

默认只打印计划、输出文件名、字节数和摘要，不创建目录。确认输出位置后，加
`--apply` 创建一个**全新的**私有目录。输出父目录必须已存在，目标不能在 RF 源码
或本次读取的目标仓库内，不能穿过符号链接。已有目录不会被覆盖；更新视图应选择
新目录。写入前校验全部输出文件名；中途 I/O 失败时保留不完整目录供检查，
不自动删除，也不写入最后的完成清单。重试仍须选择新目录。不要把运行结果描述成
发布、安装或激活。

使用重复的 `--requirement ID` 选择实际 Requirement；legacy 规范使用
`--whole-spec ID`。该命令复用 Spec Lab 的 `build_preview`，不重写 Router 的路径
匹配或依赖算法。超限或源漂移时原样失败，不截断规范。

## 已捕获的预览与中间格式

可以用 Spec Lab 的 `--json` 先捕获预览，再编译为任意输出：

```bash
python3 -B <repo-foundry-ai-dir>/scripts/explain_spec_activation.py \
  --repo <target-repository> --json --path service/main.go > /tmp/preview.json

python3 -B <repo-foundry-ai-dir>/scripts/explain.py from-preview \
  --input /tmp/preview.json --format html --output /tmp/rf-html --apply

python3 -B <repo-foundry-ai-dir>/scripts/explain.py render \
  --input /tmp/rf-html/explanation.json \
  --format mermaid --output /tmp/rf-diagram --apply
```

离线输入只检查捕获数据的内部一致性，不重新访问原仓库，不声称源仍然最新。
JSON 解析拒绝重复键、非有限数字、过大数据和未知 IR 版本。IR 保留完整原始预览、
精确 capsule、source digest、源引用、observations、limitations 和阅读分镜。
每条事实用 JSON Pointer 指向捕获快照。v1 校验会重新生成投影；修改事实、删除限制、
移动分镜或更改摘要都必须重新编译，不能靠改一个 hash 绕过。

摘要不是数字签名。输入可以被外部作者伪造，因此内部一致性不证明来源可信、内容
正确或已有批准。派生图中的依赖箭头也不等于实验测得的因果关系。

## 输出与运行时

| 输出 | 本工具实际生成的内容 | 运行条件 |
|---|---|---|
| `json` | 完整 Explanation IR | 无额外运行时 |
| `mermaid` | 依赖图源码和同一份 IR | 使用已有 Mermaid 查看器 |
| `html` | 单文件阅读播放器、证据展开和精确 capsule | 直接打开 `index.html`，不需要联网 |
| `p5` | 同一播放器，加可拖动时间轴的依赖画布 | 显式提供可信的本地 p5.js |
| `remotion` | 1920×1080、30 fps 的可渲染源码包 | 使用现有 Remotion/React 工程；本工具不渲染 MP4 |

每个目录都有 `explanation.json`、`render-manifest.json` 和 `README.txt`。Manifest
记录 IR 摘要和每个输出文件的摘要；p5 还记录用户提供运行时的摘要。所有后端显示
相同的解释事实与无授权边界，完整源码证据仍在伴随 JSON 中。视频画面是摘要，不能
代替可检索原文。

`--format auto --goal relationships` 选择 Mermaid。其他 goal 选择无依赖 HTML；
它有播放、暂停、逐帧定位、场景跳转和来源展开。自动选择不会触发 npm、网络服务、
付费 TTS、浏览器安装或可选视频运行时。第一版不导出 PPTX、Manim 或语音。

### p5.js

```bash
python3 -B <repo-foundry-ai-dir>/scripts/explain.py render \
  --input /tmp/rf-html/explanation.json --format p5 \
  --p5-js /path/to/trusted/p5.min.js --output /tmp/rf-p5 --apply
```

供应你已安装且有权使用的 p5.js 文件。工具不下载、不执行或判断该文件是否可信；
浏览器会执行它。按生成目录的 README 启动只绑定 loopback 的静态服务器。没有 p5
时显式报错，不假装生成了可工作的交互画布，也不自动回退到 CDN。

画布位置由输入和 frame 直接计算，播放历史不会改变同一 frame 的布局。节点位置
不表示距离或耗时。超过 24 个节点时不画拥挤图，但完整依赖图和 capsule 仍保留。
阅读分镜不是模拟器，不在未测量的负载点上制造 Benchmark 数据。

### Remotion

```bash
python3 -B <repo-foundry-ai-dir>/scripts/explain.py render \
  --input /tmp/rf-html/explanation.json --format remotion \
  --output /tmp/rf-remotion --apply
```

把生成目录放进已有 Remotion 工程。在该工程中运行：

```bash
npx --no-install remotion render ./BUNDLE/index.mjs RFExplanation ./out.mp4
```

把 `BUNDLE` 替换成实际目录。先核对当前 Remotion 许可；本工具不代替许可评估，
也不把 Remotion 设为 RF 的依赖。入口使用 `useCurrentFrame()` 和同一个纯函数
frame model，不依赖随机数或墙上时钟。分镜固定为 6 个阅读步骤、共 36 秒；这只是
展示节奏，**不是系统执行耗时**。没有生成旁白，没有使用 API key。

## 来源、保密和写入边界

输出默认是可丢弃的阅读副本。它不会反向修改 ADR、Design、Research、规范或证据。
完整快照可能包含项目敏感信息；分享目录就会分享其中的源内容。没有遥测、远程字体、
CDN、自动上传或后台新鲜度监测。需要保留到项目中时，应另行按项目已有目录和所有权
约定处理，不能让解释视图变成第二份手工维护的事实源。

HTML 把源文本作为 JSON 和 textContent 处理，使用 CSP；不把源片段作为可执行代码。
Mermaid 使用生成的节点 ID 和编码标签，不接受源码中的 click/init 指令。
CLI 是本地受信任用户工具，不是多租户服务或安全沙箱。

## 代码与验证

- [CLI 与输出写入](../scripts/explain.py)
- [IR 编译与验证](../scripts/explanation_ir.py)
- [共享逐帧模型](../assets/explain/frame-model.mjs)
- [Python 回归测试](../tests/test_explanation_ir.py)
- [可选 Node 逐帧测试](../tests/explanation_frames.test.mjs)

```bash
python3 -B -m unittest discover -s tests -p test_explanation_ir.py -v
python3 -B scripts/check.py
node --test tests/explanation_frames.test.mjs
```

Python 测试覆盖真实 Router 到 IR 的原文一致性和只读性，以及重复键、摘要、依赖、
时间线、源引用、可选依赖缺失、脚本注入、预览/写入和覆盖保护。Node 测试检查反向
定位、边界帧和确定性，不作为核心 Python 工作流的新增硬依赖。依赖包未安装时，
源码包生成测试不能被报告为实际 p5 浏览器运行或 Remotion 视频渲染成功。

实现参考：[Remotion 参数化渲染](https://www.remotion.dev/docs/parameterized-rendering)、
[p5 noLoop](https://p5js.org/reference/p5/noLoop/)、
[p5 redraw](https://p5js.org/reference/p5/redraw/)。
