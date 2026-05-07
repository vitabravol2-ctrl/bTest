# Binance Safety (v0.5.0)

- v0.5.0 does **not** enable automatic trading.
- Live mode is disabled by default (`live_enabled=false`).
- Use testnet first (`https://testnet.binance.vision`).
- Never commit API keys; local file: `data/settings/binance_settings.json` (gitignored).
- Manual live BUY requires explicit `BUY` confirmation and enabled live checkbox.

## v0.5.1.1 checklist
1. Use Testnet OFF for real mainnet
2. LIVE ENABLE ON
3. Load balances
4. Load filters
5. Validate order
6. Type BUY BTCUSDT
7. MANUAL BUY becomes READY
8. After position opens, type SELL BTCUSDT
9. SELL NOW becomes READY
