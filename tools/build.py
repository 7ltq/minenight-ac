from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".build"
DIST = ROOT / "dist"
SOURCES = {
    "grim": ("https://github.com/GrimAnticheat/Grim.git", "5483971b62a6291093444c3c061f5e3db8261765"),
    "totemguard": ("https://github.com/Bram1903/TotemGuard.git", "48655b552acd33db01b0f60056fa2e96abacc5a5"),
}

def run(*args: str, cwd: Path = ROOT) -> None:
    subprocess.run([str(a) for a in args], cwd=cwd, check=True)

def replace(path: Path, old: str, new: str) -> None:
    content = path.read_text(encoding="utf-8")
    if content.count(old) != 1:
        raise RuntimeError(f"Missing or ambiguous upstream pattern in {path}: {old[:100]}")
    path.write_text(content.replace(old, new), encoding="utf-8")

def prepare(name: str) -> Path:
    url, revision = SOURCES[name]
    folder = WORK / name
    if folder.exists():
        shutil.rmtree(folder)
    folder.parent.mkdir(parents=True, exist_ok=True)
    run("git", "init", str(folder))
    run("git", "-C", str(folder), "remote", "add", "origin", url)
    run("git", "-C", str(folder), "fetch", "--depth", "1", "origin", revision)
    run("git", "-C", str(folder), "checkout", "--detach", "FETCH_HEAD")
    actual = subprocess.check_output(["git", "-C", str(folder), "rev-parse", "HEAD"], text=True).strip()
    if actual != revision:
        raise RuntimeError(f"Revision mismatch: {name}")
    return folder

def grim_overlay(folder: Path) -> None:
    messages = folder / "common/src/main/resources/messages/en.yml"
    replace(messages, 'prefix: "&bGrim &8\\u00BB"', 'prefix: "&9MineNight &8\\u00BB"')
    main = folder / "common/src/main/resources/config/en.yml"
    replace(main, "check-for-updates: true", "check-for-updates: false")
    build = folder / "bukkit/build.gradle.kts"
    replace(build, '    name = "GrimAC"', '    name = "MineNightGrim"')
    replace(build, '    author = "GrimAC"', '    author = "GrimAC contributors and MineNight"')
    command = folder / "common/src/main/resources/punishments/en.yml"
    content = command.read_text(encoding="utf-8")
    if "Punishments:" not in content:
        raise RuntimeError("Grim config changed")
    content = re.sub(r'(?m)^\s*- "(\d+:\d+) \[webhook\]"\s*\n', '\n', content)
    content = re.sub(r'(?m)^\s*- "(\d+:\d+) \[proxy\]"\s*\n', '\n', content)
    command.write_text(content, encoding="utf-8")

def totem_overlay(folder: Path) -> None:
    res = folder / "common/src/main/resources"
    replace(res / "config.yml", "server: Default", "server: MineNight")
    replace(res / "config.yml", "update-checker:\n  enabled: true", "update-checker:\n  enabled: false")
    replace(res / "config.yml", "ban-animation:\n  enabled: true", "ban-animation:\n  enabled: false")
    replace(res / "config.yml", "debug-modifier-kick:\n  enabled: true", "debug-modifier-kick:\n  enabled: false")
    replace(res / "messages.yml", 'prefix: "&#FBAF00&lTG &r&#6E6651»"', 'prefix: "&#6685E8&lMineNight &r&#8298C4»"')
    replace(folder / "platforms/paper/src/main/resources/plugin.yml", "name: TotemGuard", "name: MineNightTotem")
    checks = res / "checks.yml"
    content = checks.read_text(encoding="utf-8")
    if content.count("punishable: true") < 10:
        raise RuntimeError("Unexpected TotemGuard check config")
    checks.write_text(content.replace("punishable: true", "punishable: false"), encoding="utf-8")
    mods = res / "mods.yml"
    content = mods.read_text(encoding="utf-8")
    content = content.replace("kick-command:", "kick-command:")
    mods.write_text(content, encoding="utf-8")

def build(name: str, folder: Path) -> Path:
    gradlew = folder / ("gradlew.bat" if os.name == "nt" else "gradlew")
    if os.name != "nt":
        gradlew.chmod(0o755)
    cmd = ["cmd", "/c", str(gradlew)] if os.name == "nt" else [str(gradlew)]
    task = ":bukkit:shadowJar" if name == "grim" else ":platforms:paper:shadowJar"
    run(*(cmd + [task, "--no-daemon", "--no-configuration-cache"]), cwd=folder)
    if name == "grim":
        candidates = [p for p in folder.glob("bukkit/build/libs/*.jar") if "sources" not in p.name and "javadoc" not in p.name and "plain" not in p.name]
        dest = DIST / "MineNight-GrimAC.jar"
    else:
        candidates = list((folder / "build").glob("TotemGuard-Paper-*.jar"))
        dest = DIST / "MineNight-TotemGuard.jar"
    candidates = [p for p in candidates if p.stat().st_size > 100_000]
    if not candidates:
        raise RuntimeError(f"No full {name} shadow JAR found")
    source = max(candidates, key=lambda p: p.stat().st_size)
    shutil.copy2(source, dest)
    return dest

def corresponding_source(folders: dict[str, Path]) -> None:
    target = DIST / "MineNightAC-corresponding-source.zip"
    with zipfile.ZipFile(target, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, folder in folders.items():
            tracked = subprocess.check_output(["git", "-C", str(folder), "ls-files", "-z"]).decode().split("\x00")
            for relative in tracked:
                if relative and (folder / relative).is_file():
                    archive.write(folder / relative, f"{name}/{relative}")
        archive.write(Path(__file__), "tools/build.py")
        archive.writestr("UPSTREAM_COMMITS.txt", "".join(f"{name}: {SOURCES[name][0]} @ {SOURCES[name][1]}\n" for name in folders))

def main() -> None:
    if DIST.exists():
        shutil.rmtree(DIST)
    DIST.mkdir(parents=True)
    folders = {}
    for name in SOURCES:
        folders[name] = prepare(name)
        if name == "grim":
            grim_overlay(folders[name])
        else:
            totem_overlay(folders[name])
        result = build(name, folders[name])
        print(f"Built {result.name}")
    corresponding_source(folders)
    from importlib.util import spec_from_file_location, module_from_spec
    spec = spec_from_file_location("validate", ROOT / "tools/validate.py")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    print("Two engine builds completed. One-plugin integration remains unfinished.")

if __name__ == "__main__":
    main()
