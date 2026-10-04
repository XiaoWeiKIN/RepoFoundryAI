"""Deterministic reading-language projections. Never translate the source IR."""
from __future__ import annotations

from explanation_ir import IRError, validate

LANGUAGES = ("en", "zh-CN")
FONT_FAMILY = 'system-ui, "Noto Sans CJK SC", "PingFang SC", "Microsoft YaHei", sans-serif'
# One dictionary serves HTML/SVG, p5, Mermaid, Remotion, and bundle instructions.
LABELS = {
    "en": {
        "page_title": "RF / Explanation Studio",
        "brand": "REPOFOUNDRY / EXPLANATION STUDIO",
        "badge": "DERIVED · NO AUTHORITY",
        "eyebrow": "ONE SOURCE / MULTIPLE READING SURFACES",
        "intro": "Explore a captured Spec Lab result. The same source-backed statements drive this page, the dependency diagram, and the optional video composition.",
        "steps": "Explanation steps",
        "reading": "Reading sequence, not a recording of execution time. Playback is off by default.",
        "current_scene": "Current scene",
        "play": "Play",
        "pause": "Pause",
        "frame": "Explanation frame",
        "boundary": "Derived preview only. No activation receipt, approval, or execution authority.",
        "evidence": "Evidence for this scene",
        "full": "Inspect the full explanation",
        "captured": "CAPTURED SOURCE / NOT LIVE",
        "digest": "EXPLANATION SHA-256",
        "hash_note": "Hashes establish internal consistency, not authenticity or technical correctness. Regenerate after relevant source changes.",
        "capsule": "Exact capsule (never a replacement for formal activation)",
        "snapshot": "Complete embedded source snapshot",
        "source_note": "Only the reading interface is localized. Source excerpts, IDs, paths, and hashes stay unchanged; this explanation does not replace the original requirements.",
        "footer": "Disposable output. No remote assets, telemetry, automatic installation, or background freshness checks.",
        "observation": "Observation",
        "limitation": "Limitation",
        "direct": "direct",
        "dependency": "dependency",
        "graph": "Requirement dependencies",
        "graph_title": "Direct Requirements and their dependencies",
        "relationships": "Dependency relationships in text",
        "requires": "requires",
        "seek_hint": "Seek to step 04 to inspect the dependency closure.",
        "empty_graph": "No Requirement dependency graph; inspect the source for whole-Spec or empty selection.",
        "large_graph": "The graph exceeds the readable label budget. The complete graph remains in the embedded source.",
        "graph_note": "Arrows point to required dependencies. Position is a reading aid, not a measured distance.",
        "p5_pan_hint": "The graph keeps its text size. Scroll inside it; with keyboard focus, use the arrow keys. Full relationships are also listed below.",
        "p5_missing": "p5 did not load. Check the supplied local runtime; textual evidence remains available.",
        "p5_description": "Selected Requirements and their dependencies. The complete graph is also available in the source snapshot.",
        "timeline": "Reading order, not observed execution time. Source snapshot is in the companion bundle.",
        "confidential": "Source data may be confidential. Sharing a bundle shares its embedded source.",
        "do_not_edit": "Do not edit the generated IR or treat it as an ADR, approval, or sealed evidence.",
        "runtime": "Runtime",
        "runtime_none": "none",
        "runtime_p5": "User-supplied p5; SHA-256",
        "runtime_remotion": "Existing Remotion + React project; no installation or video render performed",
        "json_help": "Read explanation.json and presentation.json. The former keeps the exact source; the latter contains localized reading text.",
        "mermaid_help": "Open diagram.mmd with your existing Mermaid viewer. Retain the companion JSON files.",
        "html_help": "Open index.html in your browser. No web server or network is required.",
        "p5_help": "From this directory run `python3 -m http.server 8000 --bind 127.0.0.1`, then open http://127.0.0.1:8000/. Stop with Ctrl-C. Only use a p5.js runtime you trust and have permission to redistribute.",
        "remotion_help": "Place this bundle inside an existing local Remotion project. Run `npx --no-install remotion render ./BUNDLE/index.mjs RFExplanation ./out.mp4` there; replace BUNDLE with this directory. Review the Remotion license and install a suitable local font first. No dependencies are installed and no MP4 or narration has been created by this export.",
    },
    "zh-CN": {
        "page_title": "RF / 解释工作台",
        "brand": "REPOFOUNDRY / 解释工作台",
        "badge": "派生解释 · 无授权效力",
        "eyebrow": "同一来源 / 多种阅读方式",
        "intro": "阅读已捕获的 Spec Lab 结果。此页面、依赖图和可选视频使用同一组有来源依据的解释。",
        "steps": "解释步骤",
        "reading": "时间轴表示阅读顺序，不表示系统执行耗时。默认不自动播放。",
        "current_scene": "当前章节",
        "play": "播放",
        "pause": "暂停",
        "frame": "解释时间轴",
        "boundary": "仅为派生预览。不生成正式激活记录，不构成批准，也不授予执行权限。",
        "evidence": "本节依据",
        "full": "查看完整解释",
        "captured": "已捕获的来源 / 非实时数据",
        "digest": "解释数据 SHA-256",
        "hash_note": "摘要只校验内部一致性，不证明来源可信或技术正确。相关来源改变后应重新生成。",
        "capsule": "精确上下文原文（不替代正式激活）",
        "snapshot": "完整来源快照",
        "source_note": "仅对阅读界面和解释进行本地化。规范原文、标识符、路径和摘要保持不变；中文解释不替代原始要求。",
        "footer": "可丢弃的阅读副本。不加载远程资源，不发送遥测，不自动安装依赖或在后台检查来源更新。",
        "observation": "观察结果",
        "limitation": "限制说明",
        "direct": "直接选择",
        "dependency": "上下文依赖",
        "graph": "规范要求依赖关系",
        "graph_title": "直接选择的要求及其依赖",
        "relationships": "依赖关系文字列表",
        "requires": "依赖",
        "seek_hint": "跳至第 04 节，查看所选要求及其依赖。",
        "empty_graph": "没有要求依赖图。请查看来源中的整份规范选择或空选择。",
        "large_graph": "图形超出易读标签范围，完整关系仍保留在来源快照中。",
        "graph_note": "箭头指向所依赖的要求。位置只辅助阅读，不表示测量距离或因果关系。",
        "p5_pan_hint": "图形保持原字号。可在图内滚动；键盘聚焦图形后使用方向键。下方也有完整的文字关系列表。",
        "p5_missing": "p5 未加载。请检查提供的本地运行时；仍可阅读文字依据。",
        "p5_description": "所选规范要求及其依赖。完整关系也保留在来源快照中。",
        "timeline": "时间轴表示阅读顺序，不表示观测到的执行耗时。来源快照在配套文件中。",
        "confidential": "来源数据可能包含敏感信息。分享文件包也会分享其中的来源内容。",
        "do_not_edit": "不要手工改写生成的 IR，也不要将它视为 ADR、批准记录或封存证据。",
        "runtime": "运行条件",
        "runtime_none": "无需额外运行时",
        "runtime_p5": "用户提供的 p5；SHA-256",
        "runtime_remotion": "已有 Remotion + React 工程；未安装依赖或渲染视频",
        "json_help": "阅读 explanation.json 和 presentation.json。前者保留精确来源，后者提供中文阅读文本。",
        "mermaid_help": "使用已有 Mermaid 查看器打开 diagram.mmd，并保留配套 JSON 文件。",
        "html_help": "在浏览器中打开 index.html。无需服务器或联网。",
        "p5_help": "在本目录运行 `python3 -m http.server 8000 --bind 127.0.0.1`，再打开 http://127.0.0.1:8000/；用 Ctrl-C 停止。仅使用可信且有权分发的 p5.js。",
        "remotion_help": "将文件包放入已有的本地 Remotion 工程。在该工程运行 `npx --no-install remotion render ./BUNDLE/index.mjs RFExplanation ./out.mp4`，将 BUNDLE 替换为本目录。先核对 Remotion 许可，并确保本地字体含中文字形。此次导出未安装依赖，也未生成 MP4 或旁白。",
    },
}
ZH_SCENES = {
    "paths": "01 / 计划修改的文件", "candidates": "02 / 候选规范",
    "selection": "03 / 本次选择", "closure": "04 / 所选要求及其依赖",
    "capsule": "05 / 精确上下文", "authority": "06 / 此预览不构成正式激活或批准",
}


def language(value: str) -> str:
    if value not in LANGUAGES:
        raise IRError("Unsupported reading language; choose en or zh-CN.")
    return value


def presentation(ir: dict, lang: str = "en") -> dict:
    """Project validated v1 facts by stable ID; do not edit or rehash that IR."""
    language(lang)
    validate(ir)
    ui = dict(LABELS[lang])
    texts = {s["id"]: s["text"] for s in ir["statements"]}
    titles = {s["id"]: s["title"] for s in ir["scenes"]}
    title = ir["subject"]["title"]
    if lang == "zh-CN":
        source = ir["source"]["snapshot"]
        capsule = source["capsule"]
        texts = {
            "paths": f"预览包含 {len(source['paths'])} 个计划文件路径。",
            "candidates": f"路径匹配得到 {len(source['specs'])} 份候选规范。",
            "selection": f"本次直接选择了 {len(source['direct'])} 条要求；整份规范的依赖闭包包含 {len(source['whole_specs'])} 份规范。",
            "closure": f"所选要求及其依赖共包含 {len(source['resolved'])} 条要求、{len(source['edges'])} 条依赖关系。",
            "capsule": (f"精确上下文包含 {capsule['bytes']} 个 UTF-8 字节，预算为 {capsule['budget_bytes']} 字节。" if capsule else "尚未编译上下文。空选择不构成正式的无适用规范判断。"),
            "authority": ui["boundary"],
            "applicability": "路径候选不代表语义上适用。正式激活仍需说明与当前任务有关的理由。",
            "freshness": "这是已捕获的本地快照，不是实时视图。仅凭 HEAD 无法确定尚未提交的来源字节。",
        }
        titles = dict(ZH_SCENES)
        title = "从计划文件到精确上下文"
    return {
        "schema": "repofoundry.presentation/v1", "language": lang,
        "authority": "none", "ir_sha256": ir["sha256"],
        "source_sha256": ir["source"]["sha256"], "title": title,
        "font_family": FONT_FAMILY, "labels": ui,
        "statements": texts, "scenes": titles,
    }
