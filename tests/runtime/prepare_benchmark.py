"""Prepare synthetic progressive Benchmark explanation views for browser tests."""
from __future__ import annotations

import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
WORK = Path(os.environ["RF_RUNTIME_WORK"]).resolve()
SCRIPT_DIR = ROOT / "engineering-benchmark" / "scripts"
sys.path.insert(0, str(SCRIPT_DIR))
import benchctl

SPEC = importlib.util.spec_from_file_location(
    "explain_benchmark", SCRIPT_DIR / "explain_benchmark.py"
)
assert SPEC and SPEC.loader
EXPLAIN = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(EXPLAIN)

run_dir = WORK / "synthetic-benchmark-run"
artifacts = run_dir / "artifacts"
artifacts.mkdir(parents=True)
(run_dir / "SCENARIO.md").write_text("# Synthetic scenario\n", encoding="utf-8")
(run_dir / "RESULT.md").write_text("# Synthetic result\n", encoding="utf-8")
(artifacts / "measurements.json").write_text(
    '{"baseline":120,"candidate":74}\n', encoding="utf-8"
)
(artifacts / "profile.txt").write_text("allocs/op 18 -> 6\n", encoding="utf-8")
(artifacts / "source.txt").write_text("candidate reuses the buffer\n", encoding="utf-8")
metadata = {
    "schema_version": "1.1",
    "metadata_schema": "1",
    "artifact_type": "benchmark-result",
    "id": "BR-900",
    "suite_id": "B-900",
    "scenario_id": "BS-900",
    "status": "sealed",
    "outcome": "passed",
    "title": "Synthetic runtime candidate",
    "author": "Runtime fixture",
    "owner": "Runtime fixture",
    "created": "2026-01-01T00:00:00Z",
    "updated": "2026-01-01T00:10:00Z",
    "completed": "2026-01-01T00:10:00Z",
    "executed_by": "Runtime fixture",
    "subject_revision": "git:synthetic-subject",
    "harness_revision": "git:synthetic-harness",
    "supersedes": [],
    "manifest": "EVIDENCE_MANIFEST.json",
}
run = benchctl.Record("BR", "BR-900", run_dir / "RESULT.md", metadata)
manifest = benchctl.build_manifest(
    run, metadata, metadata["completed"], metadata["executed_by"]
)
(run_dir / "EVIDENCE_MANIFEST.json").write_text(
    json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
)
assert benchctl.verify_manifest(run) == []

base = {
    "schema": EXPLAIN.SCHEMA,
    "authority": "none",
    "language": "en",
    "source": {
        "run_id": "BR-900",
        "suite_id": "B-900",
        "scenario_id": "BS-900",
        "outcome": "passed",
        "subject_revision": "git:synthetic-subject",
        "harness_revision": "git:synthetic-harness",
        "manifest_payload_sha256": manifest["payload_sha256"],
    },
    "subject": {
        "title": "Synthetic latency comparison",
        "question": "Does buffer reuse reduce latency under this fixture?",
        "summary": "The candidate is faster in this synthetic fixture.",
    },
    "evidence": [
        {"id": "m1", "kind": "measurement", "label": "Latency samples", "path": "artifacts/measurements.json"},
        {"id": "d1", "kind": "diagnostic", "label": "Allocation profile", "path": "artifacts/profile.txt"},
        {"id": "s1", "kind": "source", "label": "Version-matched source", "path": "artifacts/source.txt"},
        {"id": "scenario", "kind": "scenario", "label": "Scenario", "path": "SCENARIO.md"},
    ],
    "predictions": [
        {
            "id": "P1",
            "text": "Candidate latency is lower than baseline under the fixed workload.",
            "falsifier": "Candidate latency is not lower under the declared comparison.",
            "status": "supported",
            "evidence_ids": ["scenario", "m1"],
        }
    ],
    "claims": [
        {"id": "obs", "kind": "observation", "text": "Candidate latency is lower.", "evidence_ids": ["m1"]},
        {"id": "delta", "kind": "derived", "text": "Median decreases by 46 ms.", "derivation": "120 - 74 = 46 ms", "evidence_ids": ["m1"]},
        {"id": "hyp", "kind": "hypothesis", "text": "Lower allocation pressure may contribute.", "evidence_ids": ["scenario", "m1"]},
        {"id": "mechanism", "kind": "mechanism", "text": "Allocation reduction is consistent with buffer reuse.", "evidence_ids": ["m1", "d1", "s1"]},
    ],
    "metrics": [
        {
            "id": "latency",
            "title": "Median latency",
            "unit": "ms",
            "baseline": {"label": "Baseline", "value": 120, "samples": 8, "uncertainty": "synthetic ±4 ms", "evidence_id": "m1"},
            "candidate": {"label": "Candidate", "value": 74, "samples": 8, "uncertainty": "synthetic ±3 ms", "evidence_id": "m1"},
        }
    ],
    "mechanism_steps": [
        {"label": "Buffer lifecycle", "baseline": "allocate and copy", "candidate": "reuse existing buffer", "claim_id": "mechanism"}
    ],
    "limitations": ["Synthetic fixture only; no production causality is claimed."],
}

translations = {
    "en": base,
    "zh-CN": {
        **base,
        "language": "zh-CN",
        "subject": {
            "title": "合成延迟对比",
            "question": "在该测试夹具中，复用缓冲区是否降低延迟？",
            "summary": "候选实现在该合成夹具中的实测延迟更低。",
        },
        "evidence": [
            {"id": "m1", "kind": "measurement", "label": "延迟样本", "path": "artifacts/measurements.json"},
            {"id": "d1", "kind": "diagnostic", "label": "分配诊断", "path": "artifacts/profile.txt"},
            {"id": "s1", "kind": "source", "label": "对应版本源码", "path": "artifacts/source.txt"},
            {"id": "scenario", "kind": "scenario", "label": "预声明 Scenario", "path": "SCENARIO.md"},
        ],
        "predictions": [
            {
                "id": "P1",
                "text": "在固定工作负载下，候选延迟低于基线。",
                "falsifier": "候选延迟在声明的比较中没有低于基线。",
                "status": "supported",
                "evidence_ids": ["scenario", "m1"],
            }
        ],
        "claims": [
            {"id": "obs", "kind": "observation", "text": "候选实现的实测延迟更低。", "evidence_ids": ["m1"]},
            {"id": "delta", "kind": "derived", "text": "中位延迟下降 46 ms。", "derivation": "120 - 74 = 46 ms", "evidence_ids": ["m1"]},
            {"id": "hyp", "kind": "hypothesis", "text": "较低的分配压力可能贡献于延迟下降。", "evidence_ids": ["scenario", "m1"]},
            {"id": "mechanism", "kind": "mechanism", "text": "分配下降与该版本中的缓冲区复用机制一致。", "evidence_ids": ["m1", "d1", "s1"]},
        ],
        "metrics": [
            {
                "id": "latency",
                "title": "中位延迟",
                "unit": "ms",
                "baseline": {"label": "基线", "value": 120, "samples": 8, "uncertainty": "合成离散度 ±4 ms", "evidence_id": "m1"},
                "candidate": {"label": "候选", "value": 74, "samples": 8, "uncertainty": "合成离散度 ±3 ms", "evidence_id": "m1"},
            }
        ],
        "mechanism_steps": [
            {"label": "缓冲区生命周期", "baseline": "分配并复制", "candidate": "复用已有缓冲区", "claim_id": "mechanism"}
        ],
        "limitations": ["仅为合成测试夹具，不声明生产环境因果关系。"],
    },
}

reports = []
for language, document in translations.items():
    document = json.loads(json.dumps(document, ensure_ascii=False))
    document["sha256"] = EXPLAIN.sha256(EXPLAIN.canonical(document))
    EXPLAIN.validate(document, run, manifest)
    destination = WORK / "generated" / f"benchmark-{language}"
    destination.parent.mkdir(exist_ok=True)
    files = EXPLAIN.output_files(document)
    EXPLAIN.publish(destination, files, run.path.parent)
    rendered = json.loads((destination / "render-manifest.json").read_text(encoding="utf-8"))
    for name, expected in rendered["files"].items():
        assert hashlib.sha256((destination / name).read_bytes()).hexdigest() == expected
    reports.append(
        {
            "language": language,
            "document_sha256": document["sha256"],
            "manifest_payload_sha256": manifest["payload_sha256"],
            "files": sorted(path.name for path in destination.iterdir()),
        }
    )
print(json.dumps({"views": reports}, ensure_ascii=False))
