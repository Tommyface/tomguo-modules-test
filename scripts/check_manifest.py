#!/usr/bin/env python3
"""校验站源模块 manifest（CI 用，严格模式）。

用法：
  python3 scripts/check_manifest.py modules/
  python3 scripts/check_manifest.py modules/ --strict   # capabilities 未知值也报错

规则与 native/core/module_loader.go 的 parseModule 对齐：
id 正则 / name 非空 / runtime=js / api=1 / adult 是 bool /
capabilities 白名单 / mainSha256 64 位十六进制且与 main.js 一致 /
main.js ≤ 4 MB / 目录名与 id 一致。
"""

import argparse
import hashlib
import json
import pathlib
import re
import sys

ID_PATTERN = re.compile(r"^[a-z0-9_\-]{1,32}$")
ENTRY_BYTES = 4 << 20
DIGEST_LEN = 64
CAPABILITIES = {
    "search", "suggestions", "recommendations", "danmaku",
    "rankings", "cover", "metadata", "catalogState",
}


def validate(directory: pathlib.Path, strict: bool):
    errors = []
    manifest_path = directory / "manifest.json"
    entry_path = directory / "main.js"
    if not manifest_path.exists():
        return [f"{directory}: 缺少 manifest.json"]
    if not entry_path.exists():
        return [f"{directory}: 缺少 main.js"]
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        return [f"{directory}: manifest.json 解析失败：{error}"]
    module_id = str(manifest.get("id") or "")
    if not ID_PATTERN.match(module_id):
        errors.append(f"{module_id or '(空)'}: 标识只能用小写字母、数字、下划线和连字符，最长 32 位")
    if directory.name != module_id:
        errors.append(f"{directory.name}: 目录名与 id「{module_id}」不一致")
    if not str(manifest.get("name") or "").strip():
        errors.append(f"{module_id}: 缺少名称")
    if manifest.get("runtime") != "js":
        errors.append(f"{module_id}: runtime 必须是 js")
    if manifest.get("api") != 1:
        errors.append(f"{module_id}: api 必须为 1")
    if not isinstance(manifest.get("adult"), bool):
        errors.append(f"{module_id}: adult 必须是布尔值")
    min_api = manifest.get("minApi", 0)
    if not isinstance(min_api, int) or min_api < 0 or min_api > 1:
        errors.append(f"{module_id}: minApi 必须是 0 或 1")
    capabilities = manifest.get("capabilities") or []
    if not isinstance(capabilities, list) or any(not isinstance(item, str) for item in capabilities):
        errors.append(f"{module_id}: capabilities 必须是字符串数组")
    else:
        for name in capabilities:
            if name not in CAPABILITIES:
                message = f"{module_id}: 未知能力「{name}」"
                if strict:
                    errors.append(message)
                else:
                    print(f"[提示] {message}（宽松模式忽略）")
    declared = str(manifest.get("mainSha256") or "").strip().lower()
    if len(declared) != DIGEST_LEN:
        errors.append(f"{module_id}: mainSha256 必须是 64 位十六进制")
    else:
        try:
            bytes.fromhex(declared)
        except ValueError:
            errors.append(f"{module_id}: mainSha256 不是合法十六进制")
    code = entry_path.read_bytes()
    if len(code) > ENTRY_BYTES:
        errors.append(f"{module_id}: main.js 超过 4 MB")
    actual = hashlib.sha256(code).hexdigest()
    if declared and declared != actual:
        errors.append(f"{module_id}: mainSha256 与 main.js 不一致")
    return errors


def main() -> int:
    parser = argparse.ArgumentParser(description="校验站源模块 manifest")
    parser.add_argument("paths", nargs="+")
    parser.add_argument("--strict", action="store_true", help="未知 capabilities 也报错")
    options = parser.parse_args()
    directories = []
    for raw in options.paths:
        root = pathlib.Path(raw)
        if (root / "manifest.json").exists():
            directories.append(root)
            continue
        directories.extend(sorted({p.parent for p in root.rglob("manifest.json")}))
    if not directories:
        print("[失败] 未找到任何模块")
        return 1
    failed = 0
    for directory in directories:
        errors = validate(directory, options.strict)
        if errors:
            failed += 1
            for message in errors:
                print(f"[失败] {message}")
        else:
            print(f"[通过] {directory.name}")
    print(f"\n校验完成：{len(directories)} 个模块，失败 {failed} 个")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
