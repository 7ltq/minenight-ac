# MineNightAC architecture

## Goals

- One independent Paper plugin, without MineNightAllInOne dependency.
- Keep **GrimAC and TotemGuard's exact original checks** where possible; changes are isolated in audited adapters.
- Shared branding, per-check settings, violation histories, minimal allocations in packet processing.
- A single permission and punishment layer, including a server-configurable external ban command.
- Support Paper 1.21.11 and Java 25; future versions require separate verified builds.

## Development stages

1. **Foundation (this branch):** pin Grim and TotemGuard sources; reproduce their builds; create GPL corresponding-source bundle; configure conservative alerts-only defaults.
2. **Engine host:** implement a single Bukkit loader/descriptor and two explicit engine lifecycles. Resolve Grim's internal packet listener / PacketEvents ownership and TotemGuard's PacketEvents plugin integration, then confirm no duplicate packet consumers cause inconsistent state. Verify all native checks and Paper reflection/remapping.
3. **Event bridge:** normalize flags into `Flag(player UUID, engine, check, VL, timestamp, metadata)`. Implement bounded queues, check-level rate limiting, async-safe staff notifications, counters that expire, and explicit deduplication for overlapping checks.
4. **Policy:** add config-driven moderation routing with reasonable defaults, opt-in automatic punishments, audit log, staff bypass and a fixed seven-day default ban. Prevent a kick, lag burst or reconnect from escalating into a ban.
5. **UI and tests:** implement `/mnac`, `/alerts`, `/sus`, reload, history and permissions; test legit crystal PvP, offhand swaps, RTP, kitroom, high latency and restarts. Publish only after repeatable tests.

## Event pipeline

```text
Grim check engine ───────┐
                         ├── flags → normalization → suppression/deduplication → staff alerts
TotemGuard check engine ─┘                                           └→ review → punishment adapter
```

**Important:** no combined event pipeline or single-plugin JAR exists yet in this commit. The two upstream engines are built separately for verification.

## Decisions

- Don't combine two shadow JARs by simply unzipping/overlaying them: classes, PacketEvents, authlib, service metadata, and plugin descriptors may conflict.
- Don't modify third-party checks just to make them appear more accurate.
- Don't auto-ban at three flags; keep sanction policy disabled until false-positive acceptance testing.
- Don't force any dependency on the old AllInOne. Any optional command handoff must be explicitly configured.
