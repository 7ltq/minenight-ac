# MineNight AntiCheat

Independent Paper anti-cheat project using the open-source GrimAC and TotemGuard check engines, with MineNight-branded alerts and a unified release/build workflow.

**Status:** Integration foundation. This repository builds and packages the two upstream engines, but it is **not yet a verified single-plugin runtime**. Neither the release nor the merged check event pipeline should be advertised as complete until the staging checks and runtime integration tests pass.

## Engines

| Source | Commit | Scope |
|---|---|---|
| [GrimAC](https://github.com/GrimAnticheat/Grim) | `5483971b62a6291093444c3c061f5e3db8261765` | Packet simulation, movement, reach, hitboxes, etc. |
| [TotemGuard](https://github.com/Bram1903/TotemGuard) | `48655b552acd33db01b0f60056fa2e96abacc5a5` | AutoTotem, inventory, protocol, tick and mod checks |

The source is fetched at pinned commits, then the engine-specific messages and thresholds are prepared as MineNight build overlays. No copied or fabricated detection logic is used.

## Build

Prerequisites: Git, JDK 25, Python 3, and a network connection for Gradle. On Windows run `build.bat`; on Linux run `python3 tools/build.py`. GitHub Actions also runs this script.

Build output (once successful):
- `dist/MineNight-GrimAC.jar`
- `dist/MineNight-TotemGuard.jar`
- `dist/MineNightAC-corresponding-source.zip`

These are **two independent engine JARs** in the first integration stage, not one completed `MineNightAC.jar`. Never rename either JAR to imply that it contains the other engine.

## Planned single-plugin integration

The final `MineNightAC.jar` needs explicit classloader and PacketEvents ownership, deterministic lifecycle ordering, merged permission/command registration, event aggregation with deduplication and cooldowns, unified staff alerts, safe false-positive handling, and one punishment policy. In particular, launching both engines on the same player connection without checking packet listener conflicts is not acceptable.

The intended final command interface is `/mnac`, `/alerts`, `/sus <player>`, `/mnac reload` and `/mnac checks`. Until the runtime integration is complete, these are a **design target**, not implemented commands.

## Moderation

The independent AntiCheat must **not require MineNightAllInOne**. The build stage leaves automatic bans disabled. The eventual adapter can use a configurable console command (for example `ban %player% cheating 7d`) when the relevant moderation plugin is installed. This must be controlled by configuration and tested; it must not assume that `minenightallinone:ban` exists.

## False positives and deployment

Use staging with punishments disabled. Review checks individually, especially AutoTotemB (heuristic), Inventory/Protocol combinations and unusual high-ping clients. Do not automatically ban on three raw alerts from different sources: those are not independently confirmed cheat events. Keep enough context to explain staff decisions.

## Licensing

Both upstream engines are GPL-3.0 projects. Preserve their authorship notices, corresponding source, license and modified-source attribution when publishing or distributing releases. Inspect and honor requirements of their dependencies as well. Build artifacts include an archive of both checked-out source trees with a manifest of the pinned versions. This repository's integration files are available under GPL-3.0-or-later.

See [ARCHITECTURE.md](ARCHITECTURE.md).
