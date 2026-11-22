#!/usr/bin/env python3
"""为站源模块回填 / 校验 mainSha256。

用法：
  python3 scripts/fill_module_digest.py modules/            # 回填并写回 manifest.json
  python3 scripts/fill_module_digest.py modules/ --check    # 只校验，CI 用；不一致退出 1
  python3 scripts/fill_module_digest.py modules/huangdou/   # 只处理单个模块

规则：
  - 只处理同时含 manifest.json 与 main.js 的目录；
  - 目录名必须与 manifest.id 一致（避免装错位置）；
  - 摘要按 main.js 原始字节计算（UTF-8，不做换行归一），与 Go 侧 sha256.Sum256 一致。
"""

import argparse
import hashlib
import json
import pathlib
import sys


def find_modules(root: pathlib.Path):
    if not root.is_dir():
        return []
    out = []
    if (root / "manifest.json").exists() and (root / "main.js").exists():
        out.append(root)
        return out
    for manifest in sorted(root.rglob("manifest.json")):
        directory = manifest.parent
        if (directory / "main.js").exists():
            out.append(directory)
    return out


def digest(path: pathlib.Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def load_manifest(path: pathlib.Path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise SystemExit(f"{path} 不是合法 JSON：{error}")


def dump_manifest(path: pathlib.Path, manifest: dict):
    text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    path.write_text(text, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="回填或校验站源模块的 mainSha256")
    parser.add_argument("paths", nargs="+", help="模块目录或包含多个模块的根目录")
    parser.add_argument("--check", action="store_true", help="只校验，不写回")
    options = parser.parse_args()

    total = 0
    changed = 0
    failed = 0

    for raw_root in options.paths:
        for directory in find_modules(pathlib.Path(raw_root)):
            total += 1
            manifest_path = directory / "manifest.json"
            manifest = load_manifest(manifest_path)
            module_id = str(manifest.get("id") or "")
            actual = digest(directory / "main.js")
            declared = str(manifest.get("mainSha256") or "").lower()

            if directory.name != module_id:
                print(f"[警告] {directory}: 目录名与 id「{module_id}」不一致")
            if len(declared) not in (0, 64):
                print(f"[失败] {module_id}: mainSha256 必须是 64 位十六进制")
                failed += 1
                continue

            if options.check:
                if not declared:
                    print(f"[失败] {module_id}: 缺少 mainSha256")
                    failed += 1
                elif declared != actual:
                    print(f"[失败] {module_id}: 摘要不一致（清单 {declared[:12]}… 实际 {actual[:12]}…）")
                    failed += 1
                else:
                    print(f"[通过] {module_id} {actual[:12]}…")
                continue

            if declared == actual:
                print(f"[跳过] {module_id} 摘要已是最新")
                continue
            manifest["mainSha256"] = actual
            dump_manifest(manifest_path, manifest)
            changed += 1
            print(f"[写入] {module_id} → {actual[:12]}…")

    verb = "校验" if options.check else "回填"
    print(f"\n{verb}完成：共 {total} 个模块，变更 {changed} 个，失败 {failed} 个")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
