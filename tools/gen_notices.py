"""Write THIRD_PARTY_NOTICES.txt: the license of every component shipped inside ClubTools.exe.

Run in the build environment, after `pip install`, before PyInstaller (the build workflows do this).
Fails if a shipped component has no license text, or if a package is installed that this script
doesn't know about - so a new dependency can't slip into the exe without its notice.
"""
import importlib.metadata as md
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)

# packages that end up inside the exe, with what they are for
SHIPPED = {
    "pywebview": "desktop window",
    "pythonnet": "pywebview's bridge to .NET on Windows",
    "clr_loader": "used by pythonnet",
    "cffi": "used by clr_loader",
    "pycparser": "used by cffi",
    "bottle": "used by pywebview",
    "proxy_tools": "used by pywebview",
    "typing_extensions": "used by pywebview",
    "pyobjc-core": "pywebview's bridge to the macOS window and WebKit (Mac app only)",
    "pyobjc-framework-Cocoa": "used by pywebview on macOS",
    "pyobjc-framework-Quartz": "used by pywebview on macOS",
    "pyobjc-framework-WebKit": "used by pywebview on macOS",
    "pyobjc-framework-Security": "used by pywebview on macOS",
    "pyobjc-framework-UniformTypeIdentifiers": "used by pywebview on macOS",
    "pyinstaller": "bootloader that starts the exe (GPL-2.0-or-later with the Bootloader Exception)",
    "pyinstaller-hooks-contrib": "runtime hooks included in the exe",
}
WIN_ONLY = {"pythonnet", "clr_loader", "cffi", "pycparser"}   # cffi + pycparser come with clr_loader
MAC_ONLY = {"pyobjc-core", "pyobjc-framework-Cocoa", "pyobjc-framework-Quartz", "pyobjc-framework-WebKit",
            "pyobjc-framework-Security", "pyobjc-framework-UniformTypeIdentifiers"}
# installed only to build or test, never shipped
BUILD_ONLY = {"pip", "setuptools", "wheel", "packaging", "altgraph", "pefile", "pywin32-ctypes", "macholib",
              "importlib-metadata", "zipp"}
# license texts that are not inside the installed package
VENDORED = {"proxy_tools": "legal/proxy_tools-LICENSE.txt",
            # PyObjC is MIT; these wheels don't carry the text (the Cocoa/WebKit/Quartz ones do)
            "pyobjc-core": "legal/pyobjc-LICENSE.txt", "pyobjc-framework-Security": "legal/pyobjc-LICENSE.txt",
            "pyobjc-framework-UniformTypeIdentifiers": "legal/pyobjc-LICENSE.txt"}
EXTRA = [("Microsoft WebView2 SDK", "shipped inside pywebview (Core, WinForms and Loader DLLs)",
          "legal/webview2-LICENSE.txt"),
         ("Inter font 4.x (@fontsource-variable/inter 5.3.0)", "the app's typeface (assets/fonts)", "legal/inter-OFL.txt"),
         ("flag-icons 7.5.0", "nation flags (assets/flags)", "legal/flag-icons-LICENSE.txt"),
         ("Lucide icons (lucide-static 1.55.0)", "interface icons, embedded in ui.html", "legal/lucide-LICENSE.txt")]


def norm(name):
    return name.lower().replace("_", "-")


def license_texts(dist):
    out = []
    for f in dist.files or []:
        base = os.path.basename(str(f)).upper()
        if base.startswith(("LICENSE", "LICENCE", "COPYING", "NOTICE")) or (base.startswith("AUTHORS") and "licenses" in str(f)):
            p = dist.locate_file(f)
            try:
                out.append(open(p, encoding="utf-8", errors="replace").read().strip())
            except OSError:
                pass
    return out


def main():
    allow_missing_python = "--allow-missing-python" in sys.argv   # local runs on Linux
    installed = {norm(d.metadata["Name"]): d for d in md.distributions()}
    unknown = sorted(set(installed) - {norm(n) for n in SHIPPED} - {norm(n) for n in BUILD_ONLY})
    if unknown:
        raise SystemExit("Unknown packages in the build environment (add them to SHIPPED or BUILD_ONLY): " + ", ".join(unknown))

    parts = ["ClubTools includes the following third-party software. Each is used under the license shown.",
             "ClubTools itself is proprietary; these licenses apply only to the components named.", ""]

    py_lic = os.path.join(sys.base_prefix, "LICENSE.txt")
    if not os.path.exists(py_lic):   # python.org's macOS framework build keeps it with the standard library
        py_lic = os.path.join(sys.base_prefix, "lib", f"python{sys.version_info[0]}.{sys.version_info[1]}", "LICENSE.txt")
    if os.path.exists(py_lic):
        parts.append(f"=== Python {sys.version.split()[0]} (runtime and standard library, including the third-party "
                     "libraries it bundles such as OpenSSL, libffi, zlib, bzip2, xz and expat) ===\n")
        parts.append(open(py_lic, encoding="utf-8", errors="replace").read().strip())
    elif not allow_missing_python:
        raise SystemExit(f"Python's LICENSE.txt not found at {py_lic}")

    for name, why in SHIPPED.items():
        d = installed.get(norm(name))
        if d is None and name in WIN_ONLY and os.name != "nt":
            continue   # only installed (and shipped) on Windows
        if d is None and name in MAC_ONLY and sys.platform != "darwin":
            continue   # only installed (and shipped) on macOS
        if d is None:
            raise SystemExit(f"{name} is listed as shipped but is not installed")
        texts = license_texts(d)
        if name in VENDORED:
            texts.append(open(os.path.join(ROOT, VENDORED[name]), encoding="utf-8").read().strip())
        if not texts:
            raise SystemExit(f"No license text found for {name}")
        lic = d.metadata.get("License-Expression") or d.metadata.get("License") or ""
        parts.append(f"\n\n=== {d.metadata['Name']} {d.version} - {why} ===\nDeclared license: {lic.splitlines()[0] if lic else 'see text'}\n")
        parts.append("\n\n".join(texts))

    for title, why, path in EXTRA:
        parts.append(f"\n\n=== {title} - {why} ===\n")
        parts.append(open(os.path.join(ROOT, path), encoding="utf-8").read().strip())

    out = os.path.join(ROOT, "THIRD_PARTY_NOTICES.txt")
    with open(out, "w", encoding="utf-8", newline="\n") as f:
        f.write("\n".join(parts) + "\n")
    print(f"Wrote {out} ({len(SHIPPED) + len(EXTRA) + 1} components)")


if __name__ == "__main__":
    main()
