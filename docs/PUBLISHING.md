# Publishing pipeline

Strategy: ship every finished game to the **free stores first**, watch the
numbers, and only pay for a store once an app has proven itself.

```
Unity build (Nitro) ──► publish job ──► itch.io (butler) / Amazon Appstore (API)
                                              │
                              publisher/tracker.py (Acer, cron)
                                              │
                              downloads ≥ threshold?
                                   │                │
                                  yes               no
                                   │                │
                    "PROMOTE: worth $25         keep watching /
                     Google Play"               kill the app
```

## The store ladder

| Rung | Store | Cost | Automated here? | Notes |
|---|---|---|---|---|
| 1 | itch.io | free | ✅ butler CLI | No review queue, instant, PC + Android + web builds |
| 1 | Amazon Appstore | free | ✅ Submission API | Android APKs; Fire tablets + Windows 11 |
| 1 | Samsung Galaxy Store | free | manual (seller portal) | Games need Samsung approval first |
| 1 | Huawei AppGallery | free | manual (AGC API exists) | Big audience outside the US |
| 1 | Aptoide / Uptodown / APKPure | free | manual upload | Open Android stores, low but real traffic |
| 1 | Web (itch.io HTML5 / your own site) | free | ✅ via itch.io | WebGL builds, zero friction to try |
| 2 | Google Play | $25 once | later (Play Publishing API) | Where the real Android traffic is |
| 3 | Apple App Store | $99/year | later (App Store Connect API) | Also needs a Mac (or a cloud Mac CI runner) to build iOS |

F-Droid is also free but only accepts open-source apps — skip unless you
want to open-source a title.

## Ads on free stores

Ad money comes from the **ad SDK inside the app**, not from the store, so
free-store distribution still pays:

- **Unity Ads / Unity LevelPlay** — works anywhere the game runs, no store
  requirement. The natural choice since the games are Unity.
- **AppLovin MAX** — also store-agnostic.
- **AdMob** — pays the best but is picky: it wants your app verifiably listed
  in a store it recognizes (Google Play / App Store, Amazon in some flows).
  Save AdMob for after an app graduates to Google Play.

So: bake Unity Ads into every title from day one; swap in AdMob mediation
when an app gets promoted to Play.

## One-time setup

1. **itch.io**: create account, make a page per game (only manual step),
   install butler on the Nitro, set `BUTLER_API_KEY` + `ITCHIO_USER`.
2. **Amazon**: free developer account, create the app listing once, attach an
   LWA security profile to the App Submission API, set
   `AMAZON_CLIENT_ID/SECRET`.
3. Cron the tracker on the Acer:
   `0 8 * * * cd ~/Video-game-App-builder && .venv/bin/python -m publisher.tracker`

## Checking performance

- CLI: `python -m publisher.tracker`
- API: `GET http://acer:8000/performance` — each app comes back with a
  `promote: true/false` verdict against `PROMOTE_DOWNLOAD_THRESHOLD`.
