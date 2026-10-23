# rankingco-reviews-feed
Public Google review feeds for the RankingCo Duda reviews widget: `https://kerry-rco.github.io/rankingco-reviews-feed/reviews/<slug>.json`.
- Add a client in `clients.json`. The daily Action (04:00 AEST) refreshes every client. A client that fails keeps its last file, and if no secrets are set the run skips.
- Secrets (Settings → Secrets and variables → Actions): `GBP_CLIENT_ID`, `GBP_CLIENT_SECRET`, `GBP_REFRESH_TOKEN`, `PLACES_API_KEY`.
