from __future__ import annotations

import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import zipfile

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / ".build"
DIST = ROOT / "dist"
SOURCES = {
    "grim": ("https://github.com/GrimAnticheat/Grim.git", "5483971b62a6291093444c3c061f5e3db8261765"),
    "totemguard": ("https://github.com/Bram1903/TotemGuard.git", "48655b552acd33db01b0f60056fa2e96abacc5a5"),
}

def configure_java() -> None:
    candidates = []
    if os.environ.get("JAVA_HOME"):
        candidates.append(Path(os.environ["JAVA_HOME"]))
    if os.name == "nt":
        for base in {os.environ.get("ProgramFiles", ""), os.environ.get("ProgramW6432", "")}:
            if base:
                for vendor in ("Eclipse Adoptium", "Java", "Microsoft", "Amazon Corretto", "BellSoft"):
                    candidates.extend(sorted((Path(base) / vendor).glob("*"), reverse=True))
    else:
        candidates.extend(Path("/usr/lib/jvm").glob("*"))
    java = shutil.which("java")
    if java:
        candidates.append(Path(java).resolve().parent.parent)
    exe = "java.exe" if os.name == "nt" else "java"
    compiler = "javac.exe" if os.name == "nt" else "javac"
    for home in candidates:
        binary = home / "bin" / exe
        if not binary.is_file() or not (home / "bin" / compiler).is_file():
            continue
        result = subprocess.run([str(binary), "-version"], capture_output=True, text=True)
        match = re.search(r'version "(\d+)', result.stderr + result.stdout)
        if result.returncode == 0 and match and int(match.group(1)) == 25:
            os.environ["JAVA_HOME"] = str(home)
            os.environ["PATH"] = str(home / "bin") + os.pathsep + os.environ.get("PATH", "")
            print(f"[INFO] Java 25: {home}", flush=True)
            return
    raise RuntimeError("JDK 25 not found. Set JAVA_HOME to your JDK 25 installation.")

def run(*args: str, cwd: Path = ROOT) -> None:
    subprocess.run([str(a) for a in args], cwd=cwd, check=True)

def run_gradle(args: list[str], cwd: Path) -> None:
    for attempt in range(3):
        rate_limited = False
        with subprocess.Popen(args, cwd=cwd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, encoding="utf-8", errors="replace") as process:
            for line in process.stdout:
                print(line, end="", flush=True)
                if "status code 429" in line or "429 Too Many Requests" in line:
                    rate_limited = True
            code = process.wait()
        if code == 0:
            return
        if not rate_limited or attempt == 2:
            raise subprocess.CalledProcessError(code, args)
        delay = 30 * (2 ** attempt)
        print(f"[WARN] Repository rate limited Gradle; retrying in {delay}s ({attempt + 2}/3).", flush=True)
        time.sleep(delay)

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

def replace_between(path: Path, start: str, end: str, replacement: str) -> None:
    content = path.read_text(encoding="utf-8")
    if content.count(start) != 1 or content.count(end) != 1:
        raise RuntimeError(f"Unexpected upstream structure: {path}")
    begin = content.index(start)
    finish = content.index(end, begin)
    path.write_text(content[:begin] + replacement + content[finish:], encoding="utf-8")

def paper_bridge(engine: str) -> str:
    return """    @Override
    public boolean publishMineNightFlag(java.util.UUID target, String check, int vl, boolean eligible, net.kyori.adventure.text.Component message) {
        org.bukkit.plugin.Plugin core = org.bukkit.Bukkit.getPluginManager().getPlugin("MineNightAllInOne");
        if (core == null || !core.isEnabled()) return false;
        try {
            String serialized = net.kyori.adventure.text.minimessage.MiniMessage.miniMessage().serialize(message);
            core.getClass().getMethod("publishMineNightAlert", String.class, java.util.UUID.class, String.class, String.class, int.class, boolean.class)
                .invoke(core, "%s", target, check, serialized, vl, eligible);
            return true;
        } catch (ReflectiveOperationException | LinkageError ex) {
            return false;
        }
    }

""" % engine

def grim_staff_bridge(folder: Path) -> None:
    common = folder / "common/src/main/java/ac/grim/grimac"
    api = common / "platform/api/PlatformServer.java"
    replace(api, "    double getTPS();", """    default boolean publishMineNightFlag(java.util.UUID target, String check, int vl, boolean eligible, net.kyori.adventure.text.Component message) { return false; }

    double getTPS();""")
    server = folder / "bukkit/src/main/java/ac/grim/grimac/platform/bukkit/BukkitPlatformServer.java"
    anchor = "    @Override\n    public double getTPS()"
    replace(server, anchor, paper_bridge("Grim") + anchor)
    manager = common / "manager/PunishmentManager.java"
    replace_between(manager, "    public boolean handleAlert(GrimPlayer player, Supplier<String> verbose, Check check) {",
                    "    private static String safeGet", """    public boolean handleAlert(GrimPlayer player, Supplier<String> verbose, Check check) {
        for (PunishGroup group : groups) {
            if (!group.checks.contains(check)) continue;
            int vl = getViolations(group, check);
            String rendered = safeGet(verbose);
            Component message = MessageUtil.miniMessage(replaceAlertPlaceholders("[alert]", vl, check, rendered));
            return GrimAPI.INSTANCE.getPlatformServer().publishMineNightFlag(player.uuid, check.getStableKey(), vl, !check.isExperimental(), message);
        }
        return false;
    }

""")
    alert_manager = common / "manager/AlertManagerImpl.java"
    anchor = "            HashSet<PlatformPlayer> listeners = new HashSet<>(players);"
    replace(alert_manager, anchor, "            if (this != BRAND) return new HashSet<>();\n" + anchor)

def totem_staff_bridge(folder: Path) -> None:
    common = folder / "common/src/main/java/com/deathmotion/totemguard/common"
    platform = common / "TGPlatform.java"
    anchor = "    public abstract void dispatchCommand(String command);"
    replace(platform, anchor, """    public boolean publishMineNightFlag(java.util.UUID target, String check, int vl, boolean eligible, net.kyori.adventure.text.Component message) { return false; }

""" + anchor)
    paper = folder / "platforms/paper/src/main/java/com/deathmotion/totemguard/paper/TGPaperPlatform.java"
    anchor = "    @Override\n    public void dispatchCommand(String command)"
    replace(paper, anchor, paper_bridge("TotemGuard") + anchor)
    alerts = common / "features/alert/AlertRepositoryImpl.java"
    replace_between(alerts, "        realtimeRoster.deliver(violatorUuid, realtimeMessage);", "        platform.getDatabaseRepository().recordAlert(", """        platform.publishMineNightFlag(violatorUuid, check.getName(), violations,
                !check.isExperimental() && !check.isHeuristic() && check.getType() != CheckType.MOD, realtimeMessage);

""")
    replace(alerts, "            platform.getDiscordWebhookService().sendAlert(check, violations, debug);\n            punishmentRepository.punish(check, violations, debug, compiledDebug);\n", "")
    replace_between(alerts, "    public void acceptRemoteFocusAlert(SyncFocusAlertPacket.Payload payload) {", "    private void sendStatusMessage", """    public void acceptRemoteFocusAlert(SyncFocusAlertPacket.Payload payload) {
    }

""")
    replace(alerts, "        enabledAlerts.values().forEach(player -> player.sendMessage(message));", '        platform.publishMineNightFlag(new UUID(0L, 0L), "Broadcast", 0, false, message);')
    replace_between(alerts, "    private void deliverToBroadcastViewers(@Nullable UUID violatorUuid, Component message, boolean remote) {", "    @Override\n    public void onPlayerOffline", """    private void deliverToBroadcastViewers(@Nullable UUID violatorUuid, Component message, boolean remote) {
    }

""")
    roster = common / "features/alert/RealtimeAlertRoster.java"
    replace_between(roster, "    public void deliver(@Nullable UUID violatorUuid, @NotNull Component message) {", "    public @NotNull Set<UUID> focusTargets()", """    public void deliver(@Nullable UUID violatorUuid, @NotNull Component message) {
    }

""")
    punishment = common / "features/punishment/PunishmentRepositoryImpl.java"
    anchor = "        TGPlayer player = check.player;\n        UUID playerUuid = player.getUuid();"
    replace(punishment, anchor, """        if (!Boolean.getBoolean("minenight.totemguard.native-punishments")) return;
""" + anchor)

def grim_overlay(folder: Path) -> None:
    grim_staff_bridge(folder)
    for source in (folder / "common/src/main/java/ac/grim/grimac/command").rglob("*.java"):
        content = source.read_text(encoding="utf-8")
        updated = content.replace('commandBuilder("grim", "grimac")', 'commandBuilder("mngrim", "grim", "grimac")')
        if updated != content:
            source.write_text(updated, encoding="utf-8")
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
    totem_staff_bridge(folder)
    res = folder / "common/src/main/resources"
    watchdog = folder / "common/src/main/java/com/deathmotion/totemguard/common/player/latency/TransactionTimeoutWatchdog.java"
    replace(watchdog, "                player.timedOut();", """                if (Boolean.getBoolean("minenight.totemguard.enforce-transaction-timeout")) {
                    player.timedOut();
                }""")
    replace(res / "config.yml", "server: Default", "server: MineNight")
    replace(res / "config.yml", "update-checker:\n  enabled: true", "update-checker:\n  enabled: false")
    replace(res / "config.yml", "ban-animation:\n  enabled: true", "ban-animation:\n  enabled: false")
    replace(res / "config.yml", "debug-modifier-kick:\n  enabled: true", "debug-modifier-kick:\n  enabled: false")
    replace(res / "messages.yml", 'prefix: "&#FBAF00&lTG &r&#6E6651»"', 'prefix: "&9MineNight &8»"')
    replace(folder / "platforms/paper/src/main/resources/plugin.yml", "name: TotemGuard", "name: MineNightTotem")
    defaults = folder / "common/src/main/java/com/deathmotion/totemguard/common/commands/CommandDefaults.java"
    replace(defaults, 'OPTIONS.base().isBlank() ? "totemguard" : OPTIONS.base()', '"mntotemguard"')
    replace(defaults, 'OPTIONS.aliases().stream()', 'java.util.stream.Stream.concat(java.util.stream.Stream.of("mntg"), OPTIONS.aliases().stream())')
    replace(res / "messages.yml", '%prefix% &#FEE067%tg_player%&#B8AC8F failed &#FBAF00%tg_check_name% &#B8AC8FVL[&#FBAF00%tg_check_violations%&#B8AC8F/&#FBAF00%tg_check_max_violations%&#B8AC8F]', '%prefix% &f%tg_player% &7failed &e%tg_check_name% &7(VL %tg_check_violations%)')
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
    run_gradle(cmd + [task, "-Dorg.gradle.java.home=" + os.environ["JAVA_HOME"], "--no-daemon", "--no-configuration-cache"], cwd=folder)
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
    configure_java()
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
