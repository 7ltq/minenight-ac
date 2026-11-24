from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
D = ROOT / "dist"
EXPECTED = ("MineNight-GrimAC.jar", "MineNight-TotemGuard.jar", "MineNightAC-corresponding-source.zip")

for filename in EXPECTED:
    p = D / filename
    if not p.is_file() or p.stat().st_size < 1000:
        raise SystemExit(f"Missing/empty: {p}")
    with zipfile.ZipFile(p) as archive:
        if archive.testzip() is not None:
            raise SystemExit(f"Invalid ZIP: {p}")

with zipfile.ZipFile(D / "MineNight-GrimAC.jar") as g:
    if not any(n.startswith("ac/grim/grimac/") and n.endswith(".class") for n in g.namelist()):
        raise SystemExit("Grim check engine missing")

with zipfile.ZipFile(D / "MineNight-TotemGuard.jar") as t:
    if "com/deathmotion/totemguard/paper/TGPaperPlatform.class" not in t.namelist():
        raise SystemExit("TotemGuard check engine missing")

print("Both original check engines are present. This is not yet a single combined plugin.")
