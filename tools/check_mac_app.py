"""After PyInstaller on macOS: check that ClubTools.app runs on every Mac it's meant for.

Every compiled file (Mach-O) inside the app must contain both Apple Silicon (arm64) and Intel (x86_64)
code, and must not ask for a newer macOS than MIN_MACOS (macOS 12 Monterey: the oldest system we
promise). Usage: python tools/check_mac_app.py dist/ClubTools.app
"""
import os
import re
import subprocess
import sys

MIN_MACOS = (12, 0)
NEED_ARCHS = {"arm64", "x86_64"}


def macho(path):
    with open(path, "rb") as f:
        magic = f.read(4)
    return magic in (b"\xcf\xfa\xed\xfe", b"\xce\xfa\xed\xfe", b"\xca\xfe\xba\xbe", b"\xbe\xba\xfe\xca")


def min_versions(path):
    """The minimum macOS each architecture slice asks for (LC_BUILD_VERSION minos / LC_VERSION_MIN_MACOSX)."""
    out = subprocess.run(["otool", "-arch", "all", "-l", path], capture_output=True, text=True).stdout
    found, cmd = [], ""
    for line in out.splitlines():
        line = line.strip()
        if line.startswith("cmd "):
            cmd = line.split()[1]
        m = re.match(r"(minos|version) (\d+)\.(\d+)", line)
        if m and ((m.group(1) == "minos" and cmd == "LC_BUILD_VERSION") or (m.group(1) == "version" and cmd == "LC_VERSION_MIN_MACOSX")):
            found.append((int(m.group(2)), int(m.group(3))))
    return found


def main(app):
    bad, n, newest = [], 0, (0, 0)
    for root, _, files in os.walk(app):
        for name in files:
            p = os.path.join(root, name)
            if os.path.islink(p) or not macho(p):
                continue
            n += 1
            archs = set(subprocess.run(["lipo", "-archs", p], capture_output=True, text=True).stdout.split())
            if not NEED_ARCHS <= archs:
                bad.append(f"{os.path.relpath(p, app)}: architectures {sorted(archs)} (needs arm64 + x86_64)")
            for v in min_versions(p):
                newest = max(newest, v)
                if v > MIN_MACOS:
                    bad.append(f"{os.path.relpath(p, app)}: needs macOS {v[0]}.{v[1]} (must run on {MIN_MACOS[0]}.{MIN_MACOS[1]})")
    if not n:
        raise SystemExit(f"no compiled files found in {app}")
    if bad:
        print("\n".join(sorted(set(bad))[:60]))
        raise SystemExit(f"Mac app check failed: {len(set(bad))} problem(s)")
    print(f"MAC APP OK: {n} compiled files, all arm64 + x86_64, newest minimum macOS {newest[0]}.{newest[1]} "
          f"(limit {MIN_MACOS[0]}.{MIN_MACOS[1]})")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join("dist", "ClubTools.app"))
