#!/usr/bin/env python3
"""Check requested packages before compilation and against the final firmware."""
import argparse
import json
from pathlib import Path
import re
import sys

ALIASES = {"luci-app-istore": "luci-app-store"}
NAME = re.compile(r"[A-Za-z0-9][A-Za-z0-9+_.-]*\Z")


def save(path, state):
    path.write_text(json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def prepare(args):
    text = args.config.read_text(encoding="utf-8")
    packages = []
    seen = set()

    def add(requested, reason):
        if not NAME.fullmatch(requested):
            raise ValueError(f"Invalid package name: {requested!r}; use comma or whitespace separators")
        resolved = ALIASES.get(requested, requested)
        if resolved in seen:
            return
        seen.add(resolved)
        packages.append({"requested": requested, "resolved": resolved, "reason": reason})
        if resolved != requested:
            print(f"Package alias: {requested} -> {resolved}")

    for name in re.split(r"[,\s]+", args.packages.strip()):
        if name:
            add(name, "extra")
    # Historical profiles select Argon already; audit that default as well.
    if re.search(r"^CONFIG_PACKAGE_luci-theme-argon=y$", text, re.M):
        add("luci-theme-argon", "profile")
    if seen.intersection({"luci-app-openclash", "luci-app-store"}):
        add("luci-compat", "dependency")

    symbols = {f"CONFIG_PACKAGE_{entry['resolved']}" for entry in packages}
    # Replace existing y/m/not-set lines, instead of appending duplicate assignments.
    kept = []
    for line in text.splitlines():
        symbol = re.match(r"^(?:# )?(CONFIG_PACKAGE_[^ =]+)(?:=| is not set$)", line)
        if not symbol or symbol.group(1) not in symbols:
            kept.append(line)
    kept.extend(f"CONFIG_PACKAGE_{entry['resolved']}=y" for entry in packages)
    args.config.write_text("\n".join(kept) + "\n", encoding="utf-8")
    save(args.state, {"format_version": 1, "packages": packages,
                      "config_verified": False, "manifest_verified": False})
    print("Packages to verify:", " ".join(p["resolved"] for p in packages) or "(none)")


def load_state(args):
    return json.loads(args.state.read_text(encoding="utf-8"))


def check_config(args):
    state = load_state(args)
    values = {}
    for line in args.config.read_text(encoding="utf-8").splitlines():
        if line.startswith("CONFIG_PACKAGE_") and "=" in line:
            name, value = line.split("=", 1)
            values[name.removeprefix("CONFIG_PACKAGE_")] = value
    failures = []
    report = ["# 软件包配置核验", "", "| 请求 | 实际包名 | defconfig 结果 |", "|---|---|---|"]
    for package in state["packages"]:
        name = package["resolved"]
        value = values.get(name, "未选中或不存在")
        package["config_value"] = value
        report.append(f"| {package['requested']} | {name} | {value} |")
        if value != "y":
            failures.append(name)
    state["config_verified"] = not failures
    state["manifest_verified"] = False
    save(args.state, state)
    args.report.write_text("\n".join(report) + "\n", encoding="utf-8")
    if failures:
        raise ValueError("defconfig did not select requested packages as y: " + ", ".join(failures)
                         + ". Check package sources, dependencies and target restrictions; refusing to compile an incomplete image.")
    print("All requested packages survived make defconfig as y.")


def check_manifest(args):
    state = load_state(args)
    if not state["config_verified"]:
        raise ValueError("Configuration must be verified before checking firmware manifests")
    failures = []
    manifests = []
    report = ["# 固件软件包核验", "", "| 固件清单 | 实际包名 | 已安装版本 |", "|---|---|---|"]
    for manifest in args.manifest:
        installed = {}
        for line in manifest.read_text(encoding="utf-8").splitlines():
            if " - " in line:
                name, version = line.split(" - ", 1)
                installed[name] = version
        versions = {}
        for package in state["packages"]:
            name = package["resolved"]
            version = installed.get(name)
            versions[name] = version
            report.append(f"| {manifest.name} | {name} | {version or '缺失'} |")
            if not version:
                failures.append(f"{manifest.name}: {name}")
        manifests.append({"file": manifest.name, "versions": versions})
    state["manifests"] = manifests
    state["manifest_verified"] = not failures
    save(args.state, state)
    args.report.write_text("\n".join(report) + "\n", encoding="utf-8")
    if failures:
        raise ValueError("Requested packages missing from firmware: " + ", ".join(failures))
    print("All requested packages are present in every firmware manifest.")


def release(args):
    state = load_state(args)
    if not state["config_verified"] or not state["manifest_verified"]:
        raise ValueError("Cannot publish package claims without both configuration and firmware verification")
    print("### 已验证内置的软件包\n")
    print("| 请求包名 | 实际包名 | 来源 | 固件内版本 |\n|---|---|---|---|")
    reasons = {"extra": "用户额外选择", "profile": "机型默认", "dependency": "兼容依赖"}
    for package in state["packages"]:
        name = package["resolved"]
        versions = ", ".join(dict.fromkeys(m["versions"][name] for m in state["manifests"]))
        print(f"| {package['requested']} | {name} | {reasons[package['reason']]} | {versions} |")
    if not state["packages"]:
        print("| 无 | 无 | 无额外或需核验的默认包 | — |")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name, action in [("prepare", prepare), ("check-config", check_config),
                         ("check-manifest", check_manifest), ("release", release)]:
        sub = commands.add_parser(name)
        sub.set_defaults(action=action)
        sub.add_argument("--state", type=Path, default=Path("package-selection.json"))
        if name in ("prepare", "check-config"):
            sub.add_argument("--config", type=Path, default=Path(".config"))
        if name == "prepare":
            sub.add_argument("--packages", default="")
        if name == "check-config":
            sub.add_argument("--report", type=Path, default=Path("package-selection-report.txt"))
        if name == "check-manifest":
            sub.add_argument("--manifest", nargs="+", type=Path, required=True)
            sub.add_argument("--report", type=Path, default=Path("package-manifest-report.txt"))
    args = parser.parse_args()
    try:
        args.action(args)
    except (ValueError, OSError, KeyError) as error:
        print(f"::error::{error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
