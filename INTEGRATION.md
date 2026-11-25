# Shared MineNight staff alerts and sanctions

The pinned Grim and TotemGuard engines are still distributed as separate JARs. Both Paper adapters forward local flags to MineNightAllInOne through a runtime-checked optional bridge. No compile-time core dependency is added. If the matching core is absent or incompatible, checks still run but centralized staff messages and automatic sanctions are unavailable. The old engine command names remain; their separate alert subscriptions no longer control normal flag delivery.

Install both updated engines and the updated MineNightAllInOne together on a staging server. Enable /staffmode (alias /sfmode) with minenight.staff.mode. The core combines repeated alerts by engine, UUID and check; a bounded queue protects against chat overload. Standard native flag punishment dispatch is routed away from the original engines. TotemGuard native punishment commands are disabled by default; do not enable the native-punishments JVM property while using central punishment policy. Engine-native packet mitigation is not changed.

Configure MineNightAllInOne/moderation/config.yml:
```yaml
anticheat:
  automatic-bans: false
  allowed-checks: []
  thresholds: {}
```

After staging has verified a non-experimental check, add its exact engine:check stable key to allowed-checks and set an appropriate per-check threshold below thresholds.<engine>.<check>. The core requires a native VL threshold and repeated distinct one-second windows in a 120-second observation period. No check is enabled for automatic sanctions by default. Existing active bans are not replaced by automatic sanctions.

Grim uses its stable check key and TotemGuard its check name; experimental and TotemGuard heuristic/mod checks are excluded. The central bridge is for local single-server operation, not a verified Redis/proxy aggregation implementation. Console/Discord flag delivery is not enabled by this integration. Paper runtime, compatibility, permissions, false-positive scenarios, native packet processing and the upstream build must be verified before production. The transaction watchdog change is a mitigation, not proof that the pending-transaction cause is repaired.
