# OBD-Insight Telegram Bot

A Telegram front end for OBD-Insight. Paste a FORScan log (or send it as a
`.txt` file) and get the same color-coded, plain-English triage as the
terminal prototype in `src/` - no install, right inside a chat.

## Why a Telegram bot

Research into Telegram's bot ecosystem and its 2024-era **Affiliate
Program** (BotFather -> Edit -> Affiliate Program, visible as "NEW" in
recent BotFather builds) turned up a clear pattern:

* The most profitable bots on Telegram cluster around a few categories -
  crypto trading/sniping bots, generic AI chat wrappers, paid-community
  and gated-content bots, and signal/alert bots. All of them monetize with
  **Telegram Stars** (in-chat purchases, `currency="XTR"`) and increasingly
  recruit **affiliates**: other channels or bots that share a referral
  link and earn a cut of every Star purchase made by users they bring in.
* Crypto trading and generic AI-chat bots are saturated and capital/legal
  heavy. Niche signal/utility bots with a clear, recurring value
  proposition and a low build cost are repeatedly called out as the best
  starting point for a new, focused bot.
* **Automotive/OBD-II diagnostics is an underserved niche on Telegram.**
  There are large FORScan, OBD-II, and car-forum communities on Telegram,
  but no dedicated bot that turns a raw scan log into an instant,
  prioritized, plain-English triage the way OBD-Insight already does on
  the desktop. That's the gap this bot fills, and it reuses the existing
  `parser.py`/`severity.py` engine instead of building a new one.

## What it does

* **Free tier** - paste a FORScan log or a single DTC (`/dtc P0300`) and get
  severity (Critical/Warning/Informational) plus a plain-English
  explanation, powered by `dtc_reference.py`.
* **Premium tier** (Telegram Stars subscription via `/upgrade`) - unlocks
  cross-scan history tracking (`storage.py`): whether each code is `NEW`,
  `REPEATED` (present last scan too), or `RETURNING` (came back after
  looking cleared). This is the exact "is this getting worse or was it
  never really fixed" value the main README describes as OBD-Insight's
  differentiator versus a one-time code lookup.
* **Affiliate-ready** - `/affiliate` explains how forum/channel owners can
  join this bot's BotFather Affiliate Program and earn a Star commission
  for every referred user who goes Premium, with zero custom referral
  code needed (Telegram handles attribution and payout natively).

## Setup

1. Create the bot with [@BotFather](https://t.me/BotFather) if you haven't
   already (`/newbot`), or reuse an existing one.
2. In BotFather, open your bot -> **Affiliate Program** and turn it on. Set
   a commission percentage and commission period (e.g. 20% for 90 days) -
   this is the toggle referenced above and is what lets other channels
   promote the bot for a cut of Premium purchases.
3. Install dependencies (a virtualenv is recommended):
   ```bash
   pip install -r telegram_bot/requirements.txt
   ```
4. Set environment variables:
   ```bash
   export BOT_TOKEN="123456:your-botfather-token"
   export PREMIUM_STARS_PRICE=199   # Telegram Stars per 30-day Premium period
   ```
5. Run it:
   ```bash
   python telegram_bot/bot.py
   ```

Scan history and premium status are stored in a local SQLite file at
`telegram_bot/data/bot_state.db` (created automatically, git-ignored).

## Commands

| Command | Description |
| --- | --- |
| `/start`, `/help` | Intro and command list |
| `/scan` | Paste a FORScan log, or just send the text/`.txt` file directly |
| `/dtc <code>` | Quick single-code severity + explanation lookup |
| `/upgrade` | Buy Premium with Telegram Stars |
| `/affiliate` | Instructions for promoting the bot and earning Stars |

## Tests

Business logic (`dtc_reference.py`, `storage.py`) is covered by
`tests/test_dtc_reference.py` and `tests/test_storage.py` in the repo root
and requires no Telegram token to run:

```bash
python -m unittest discover -s tests
```

`bot.py` itself is a thin wiring layer over `python-telegram-bot` and is
not unit tested here since it requires a live bot token to exercise.
