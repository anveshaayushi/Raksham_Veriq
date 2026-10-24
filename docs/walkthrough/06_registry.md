# Cross-victim registry: has someone else reported this payee?

## Plain words
Plain words: if two independent people report the same UPI ID or account, the next person is warned. The file stores
only keyed fingerprints (HMAC-SHA256), never the ID itself. One person reporting twenty times, or a burst of new
"reporters" in one minute, counts once. Payment-gateway IDs are never stored. If the registry is broken, VERIQ says
"unavailable", never "clean".

| | |
|---|---|
| Code | `registry/` |
| Goes in | a payee identifier; a report from a session |
| Comes out | linked / clean (= no reports, not 'safe') / unavailable |
| Can do | link after 2 independent reporters or a reviewer; resist poisoning |
| Cannot say | that a payee is a criminal (reports are not convictions) |
| Tests / numbers | `registry/tests/` (poisoning tests), privacy proof (C-31) |
| Known limit | Keyed hashes are pseudonymisation, not anonymity: whoever holds the key can test a guess. |
