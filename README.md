# NutriGent — Agentic Diet & Allergy Assistant for Telegram

**Author:** Kiana Alian · **Status:** working pilot, deployed on a Linux server · **Language:** Python 3.11+

NutriGent is a self-hosted assistant that lives in Telegram. It checks whether a food is safe for
a user's allergies, plans meals, builds pantry-aware shopping lists and tracks calories and macros,
answering with images (verdict cards, dashboards, charts) instead of walls of text.

> **Core principle — the model proposes, deterministic code disposes.**
> A language model only *extracts* ingredients from a photo or a dish name. The safety verdict is
> issued by `shared/safety_gate.py`: plain, tested Python that is reproducible, auditable and
> **fails closed** (when unsure, the answer is *not safe*).

- Full feature list with honest status (working / partial / roadmap): **[FEATURES.md](FEATURES.md)**
- Project report (PDF): **[docs/NutriGent_Project_Report.pdf](docs/NutriGent_Project_Report.pdf)**

---

## What works today

| Area | What the user gets |
|---|---|
| Sign-up | One question at a time, mostly buttons: name, allergies + severity, diet, goal, sex, age, height, weight, activity, cooking time. Saved in the DB, so it survives restarts and never loops. |
| Food safety check | Photo, ingredient label or dish name → ingredients extracted → deterministic gate → **DO NOT EAT / CAUTION / SAFE / CAN'T VERIFY** card with the exact reason. |
| Hidden allergens | 145 label terms for 14 allergens (EU Annex II + FDA Top 9), e.g. whey → milk, Worcestershire sauce → fish, E1105 → egg; 23 false-positive guards (coconut milk ≠ milk, eggplant ≠ egg). |
| Calorie targets | Mifflin–St Jeor BMR × activity factor, goal adjustment, 30/40/30 macro split. |
| Charts | Today (calorie ring + macro bars), week (7-day bars vs target), month (30-day trend + weight), weekly safety donut. |
| Planning | `/plan` builds a 7-day plan, screens every recipe through the gate, and writes a shopping list = needed − pantry, grouped by store section. |
| Everyday tools | Allergy card for restaurants, symptom journal, "too tired" fallback, profile card. |
| UI | Persistent button grid under the chat input (no slash commands needed) + inline buttons. |
| Access control | Optional allow-list of Telegram IDs; users can only change their own data. |

See [FEATURES.md](FEATURES.md) for all 48 features, including what is partial and what is planned.

## How it works

```
Telegram user ──► Telegram Bot API ──► app/bot.py  (long polling — no public port needed)
                                           │  routes: sign-up · commands · buttons · photos · text
                                           ▼
                                   app/onboarding.py  ── step-by-step sign-up (state in SQLite)
                                   app/handlers.py    ── one function per action
                                      │         │
                       app/llm.py ◄───┘         └──► shared/safety_gate.py  (deterministic verdict)
                 (only OpenAI caller:                shared/nutrition.py    (targets)
                  extract / decompose / plan)        shared/visuals.py, charts.py (PNG cards)
                                                     shared/db.py → SQLite (13 tables)

Hermes Agent (GPT-5.5) + skills/ ── conversational layer: persona, memory, multilingual chat,
                                    scheduled jobs (being connected — see roadmap)
```

## Quick start

```bash
git clone <this repo> nutrigent && cd nutrigent
python3 -m venv .venv && . .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # fill in TELEGRAM_TOKEN (from @BotFather), optional OPENAI_API_KEY
set -a; . ./.env; set +a
python3 app/bot.py            # creates the database on first start, then polls Telegram
```

Open your bot in Telegram and send **/start**.
Without `OPENAI_API_KEY` the bot still runs: photo reading and meal planning use built-in sample
answers so the whole flow can be demonstrated offline.

### Configuration (`.env`)

| Variable | Meaning |
|---|---|
| `TELEGRAM_TOKEN` | Bot token from @BotFather (required) |
| `DIET_DB` | Path of the SQLite database (default `shared/diet.db`) |
| `OPENAI_API_KEY` | Enables real vision extraction and meal planning (optional) |
| `ALLOWED_TELEGRAM_IDS` | Comma-separated Telegram user IDs allowed to use the bot; empty = everyone |
| `OPENAI_VISION_MODEL`, `OPENAI_TEXT_MODEL`, `OPENAI_PLANNER_MODEL` | Model overrides (default `gpt-4o`) |

## Tests

```bash
python3 tests/test_safety_gate.py         # 21 safety fixtures (derivatives, traces, fail-closed, guards, typed names)
python3 tests/test_onboarding_flow.py     # sign-up conversation: full flow, no loop, bad input, resume, returning user
python3 tests/test_reply_keyboard.py      # button grid labels and routing
python3 tests/test_access.py              # allow-list and per-user data ownership
python3 tests/test_onboarding_buttons.py  # onboarding button layouts
python3 tests/test_bot_flow.py            # router → handler → image rendering, offline
python3 tests/e2e_fake_telegram.py        # 80 actions against a simulated Telegram API
```

All unit suites pass. The end-to-end run currently reports 66 correct replies, 13 buttons that do not
answer yet and 1 known escaping bug — these are listed as open work in [FEATURES.md](FEATURES.md#roadmap).

## Deployment

The pilot runs on Ubuntu 24.04 (1 vCPU, 2 GB RAM) as a hardened systemd service under a dedicated
unprivileged user — see [`deploy/nutrigent-bot.service`](deploy/nutrigent-bot.service). It uses about
70 MB of RAM when idle and ~120 MB at peak. Hermes Agent runs as the same user
([`deploy/hermes-wrapper.sh`](deploy/hermes-wrapper.sh)) with its own Telegram gateway disabled, so the
bot is the only program reading the bot token.

```bash
sudo useradd --system --create-home --home-dir /opt/nutrigent --shell /usr/sbin/nologin nutrigent
# copy the repo to /opt/nutrigent/app, create /opt/nutrigent/venv, put .env in /opt/nutrigent/.env (chmod 600)
sudo cp deploy/nutrigent-bot.service /etc/systemd/system/ && sudo systemctl enable --now nutrigent-bot
```

## Repository layout

```
app/        bot.py (router) · onboarding.py (sign-up) · handlers.py (actions) · llm.py (OpenAI adapter)
shared/     safety_gate.py · nutrition.py · visuals.py · charts.py · reporting.py · db.py
            telegram_io.py · telegram_menu.py · schema.sql · allergen_seed.sql · prompts/
skills/     15 Hermes Agent skills (one SKILL.md each)
tests/      unit suites + end-to-end test against a simulated Telegram
deploy/     systemd unit and Hermes wrapper used on the server
docs/       project report (PDF)
sample-visuals/, sample-charts/   example images produced by the bot
AGENT_PROMPT.md   system prompt for the Hermes agent persona
```

## Safety and privacy

NutriGent is an **assistive tool, not a medical device**. Every DO NOT EAT / CAN'T VERIFY verdict
carries emergency guidance. Health data stays in the local SQLite file on your own server; only the
image and the allergen names are sent to the model provider for extraction. Secrets (`.env`) and
databases are excluded from version control by `.gitignore`.
