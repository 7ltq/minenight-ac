# Transaction timeout compatibility mitigation

The pinned TotemGuard watchdog disconnects a connection when its oldest pending transaction exceeds 30 seconds (120 seconds before the first observed reply). The exact disconnect message originates in TGPlayer.timedOut(). A conflict with Grim or PacketEvents has not been reproduced.

MineNight builds leave this additional disconnect disabled by default. Paper's own connection timeout and TotemGuard's packet processing and check implementations remain unchanged. This is a mitigation, not a verified repair of transaction accounting. To restore upstream watchdog enforcement for controlled testing, start Java with `-Dminenight.totemguard.enforce-transaction-timeout=true` before `-jar`.

Staging must verify pending transaction growth, callback processing, both engines' packet handling and AutoTotem detection before production deployment.
