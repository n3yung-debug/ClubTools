"""After PyInstaller: check what actually went into ClubTools.exe.

Every bundled module must come from the Python standard library, ClubTools itself, or a package listed
as shipped in gen_notices.py (so THIRD_PARTY_NOTICES.txt covers it). PyInstaller's own Python package
must not be inside: only its bootloader is covered by the Bootloader Exception; the rest is plain GPL.
Usage: python tools/check_bundle.py build/ClubTools/PYZ-00.toc
"""
import ast
import importlib.metadata as md
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_notices import SHIPPED, norm  # noqa: E402

OWN = {"chem_builder", "chem_engine"}


def main(toc_path):
    with open(toc_path, encoding="utf-8") as f:
        toc = ast.literal_eval(f.read())
    modules = sorted({entry[0] for entry in toc[1] if entry[2] == "PYMODULE"})
    owners = md.packages_distributions()   # top-level import name -> distributions providing it
    stdlib = set(sys.stdlib_module_names)
    shipped = {norm(n) for n in SHIPPED}
    found, bad = {}, []
    for m in modules:
        top = m.split(".")[0]
        if (top in OWN or top in stdlib or top.startswith(("_pyi", "pyimod", "_sysconfigdata"))
                or top == "sitecustomize"):   # Python runtime pieces
            continue
        dists = {norm(d) for d in owners.get(top, [])} or {"(unknown: " + top + ")"}
        for d in dists:
            found.setdefault(d, set()).add(top)
            if d not in shipped:
                bad.append((m, d))
    print("Bundled third-party packages: " + ", ".join(f"{d} ({', '.join(sorted(t))})" for d, t in sorted(found.items())))
    if any(m == "PyInstaller" or m.startswith("PyInstaller.") for m in modules):
        bad.append(("PyInstaller.*", "pyinstaller (GPL Python modules - only the bootloader may ship)"))
    if bad:
        for m, d in bad[:40]:
            print(f"  NOT ALLOWED IN THE EXE: {m}  <- {d}")
        raise SystemExit("Bundle check failed: exclude these modules or list the package in tools/gen_notices.py SHIPPED")
    print(f"BUNDLE OK: {len(modules)} modules, all covered by THIRD_PARTY_NOTICES.txt")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else os.path.join("build", "ClubTools", "PYZ-00.toc"))
