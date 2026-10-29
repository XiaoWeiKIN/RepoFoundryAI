"""One-shot, branch-scoped integration edit; removed before the PR is opened."""
import ast
import hashlib
from pathlib import Path


def read_checked(name, expected_blob):
    raw = Path(name).read_bytes()
    blob = hashlib.sha1(b'blob ' + str(len(raw)).encode() + b'\0' + raw).hexdigest()
    if blob != expected_blob:
        raise RuntimeError(f'Original source changed: {name}: {blob}')
    return raw.decode('utf-8')


def once(text, old, new):
    if text.count(old) != 1:
        raise RuntimeError(f'Ambiguous edit anchor: {old[:100]!r}')
    return text.replace(old, new, 1)


router_path = 'assets/core/engineering-specs/spec_router.py'
r = read_checked(router_path, '0c10ff7715014be50efd11b6081eb52e3c5921a2')
r = once(r, 'import hashlib\n', 'import hashlib\nimport importlib.util\n')
r = once(r, '    existing = _load_runtime(root, adapter_id, session_id, turn_id)\n    if existing is not None:\n', '''    prompt = payload.get("prompt", "")
    direct_ep_refs = sorted({
        f"EP-{int(number):03d}" for number in _SESSION_EP_RE.findall(prompt)
    }) if isinstance(prompt, str) else []
    existing = _load_runtime(root, adapter_id, session_id, turn_id)
    if existing is not None:
''')
r = once(r, '''        if payload.get("event") in {"subagent_start", "context_resume"}:
            epoch = existing.get("context_epoch")''', '''        if payload.get("event") in {"subagent_start", "context_resume"}:
            prior = existing.get("context_direct_ep_refs", [])
            if not isinstance(prior, list) or any(not isinstance(item, str) for item in prior):
                prior = []
                existing["context_direct_ep_overflow"] = True
            protected = sorted(set(prior) | set(direct_ep_refs))
            existing["context_direct_ep_refs"] = protected[:32]
            existing["context_direct_ep_overflow"] = bool(
                existing.get("context_direct_ep_overflow") or len(protected) > 32
            )
            epoch = existing.get("context_epoch")''')
r = once(r, '        "context_ep_ref": ep_refs[0] if ep_refs else None,\n', '''        "context_ep_ref": ep_refs[0] if ep_refs else None,
        "context_direct_ep_refs": direct_ep_refs[:32],
        "context_direct_ep_overflow": len(direct_ep_refs) > 32,
''')
helper = '''def _apply_memory_runtime(
    root: Path, runtime: dict[str, object], payload: dict[str, object],
    baseline: dict[str, object],
) -> dict[str, object]:
    """Optional Core extension; an invalid baseline never reaches this call."""
    config = root / ".repo-foundry/memory-context.json"
    if not config.exists() and not config.is_symlink():
        return baseline
    previous = sys.dont_write_bytecode
    sys.dont_write_bytecode = True
    try:
        path = Path(__file__).with_name("memory_runtime.py")
        if path.is_symlink() or not path.is_file():
            raise ValueError("MEMORY_RUNTIME_UNAVAILABLE")
        spec = importlib.util.spec_from_file_location("_repoharness_memory_runtime", path)
        if spec is None or spec.loader is None:
            raise ValueError("MEMORY_RUNTIME_UNAVAILABLE")
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module.apply_context(
            sys.modules[__name__], root, runtime, baseline,
            as_of=payload.get("memory_as_of"),
        )
    except (OSError, ImportError, ValueError, RuntimeError, SyntaxError, AttributeError, TypeError):
        return {**baseline, "memory": {
            "schema_version": 1, "status": "baseline_fallback",
            "reason": "MEMORY_RUNTIME_UNAVAILABLE", "saved_bytes": 0,
            "protected_core_unchanged": True, "authority_changed": False,
        }}
    finally:
        sys.dont_write_bytecode = previous


'''
r = once(r, 'def _route_context(\n', helper + 'def _route_context(\n')
r = once(r, '    context = str(context_plan["text"])\n    activation = runtime.get("activation")', '''    context_plan = _apply_memory_runtime(root, runtime, payload, context_plan)
    context = str(context_plan["text"])
    activation = runtime.get("activation")''')
ast.parse(r)

foundry_path = 'scripts/foundryctl.py'
f = read_checked(foundry_path, '283fd461ce1f7491771610198baaa38250028cd4')
f = once(f, 'CORE_HARNESS_VERSION = "1.5.6"', 'CORE_HARNESS_VERSION = "1.6.0"')
f = once(f, 'CORE_FILE_ASSETS = (\n', '''CORE_MEMORY_INTRODUCED = "1.6.0"
CORE_MEMORY_FILE_ASSETS = (
    (
        ".repo-foundry/engineering-specs/memory_retrieval.py",
        "core/engineering-specs/memory_retrieval.py",
    ),
    (
        ".repo-foundry/engineering-specs/memory_runtime.py",
        "core/engineering-specs/memory_runtime.py",
    ),
)
CORE_FILE_ASSETS = (
    *CORE_MEMORY_FILE_ASSETS,
''')
f = once(f, '''        if relative != CORE_PROJECT_SKILL_PATH
        or semver_tuple(core_version, "core.version") >= core_cutoff
''', '''        if (
            relative != CORE_PROJECT_SKILL_PATH
            or semver_tuple(core_version, "core.version") >= core_cutoff
        ) and (
            relative not in {path for path, _ in CORE_MEMORY_FILE_ASSETS}
            or semver_tuple(core_version, "core.version") >= semver_tuple(
                CORE_MEMORY_INTRODUCED, "Core memory runtime introduction"
            )
        )
''')
f = once(f, 'CORE_TEMPLATE_IDS = {\n', '''CORE_TEMPLATE_IDS = {
    ".repo-foundry/engineering-specs/memory_retrieval.py": "core/engineering-specs-memory-retrieval",
    ".repo-foundry/engineering-specs/memory_runtime.py": "core/engineering-specs-memory-runtime",
''')
f = once(f, 'CORE_GENERATED_FILES = frozenset(\n    {\n', '''CORE_GENERATED_FILES = frozenset(
    {
        ".repo-foundry/engineering-specs/memory_retrieval.py",
        ".repo-foundry/engineering-specs/memory_runtime.py",
''')
ast.parse(f)

changes = {router_path: r, foundry_path: f}
for name in ('tests/test_foundryctl.py', 'tests/test_writing_routes.py'):
    original = Path(name).read_text()
    updated = original.replace('"1.5.6"', '"1.6.0"').replace('to-1.5.6', 'to-1.6.0')
    if original == updated:
        raise RuntimeError(f'Expected current-version assertions missing: {name}')
    ast.parse(updated)
    changes[name] = updated
name = 'references/bootstrap.md'
s = Path(name).read_text()
s = once(s, '当前源码的 Core `1.5.6`', '当前源码的 Core `1.6.0`')
s += '\n## 可选运行时记忆降温\n\nCore 1.6.0 增加两个版本化 memory 模块，但不创建配置、不默认开启降温。\n显式配置、升级和回退边界见 [运行时记忆](../engineering-execution-plan/references/memory-runtime.md)。\n'
changes[name] = s
name = 'engineering-execution-plan/SKILL.md'
s = Path(name).read_text()
s = once(s, '[检索预览](references/memory-context.md) |', '[检索预览](references/memory-context.md)；[运行时降温](references/memory-runtime.md) |')
changes[name] = s
for name, text in changes.items():
    Path(name).write_text(text, encoding='utf-8')
print('Prepared exactly:', ', '.join(changes))
