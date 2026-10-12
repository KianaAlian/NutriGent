# NutriGent — Features, Workflows & Roadmap

**Author:** Kiana Alian

NutriGent is designed as an *agent*, not a chatbot: it owns goals (keep the user safe from their
allergens, keep their weekly nutrition on target), keeps state about the real world (pantry, plan,
shopping list, food log) and is meant to act on a schedule without being asked. This document lists
every designed feature and says honestly how far each one is built.

| Status | Meaning |
|---|---|
| ✅ **Working** | Implemented in the bot's code and exercised by the automated tests or the end-to-end run |
| 🟡 **Partial** | Part of it works, or it is performed by the Hermes agent following a skill rather than by tested code |
| 🔵 **Roadmap** | Designed (skill, prompt or database field exists), not built yet |

**Summary of the 48 designed features:** 18 ✅ working · 8 🟡 partial · 22 🔵 roadmap — plus 9 features
added during this phase (section 2), all ✅.

---

## 1. Feature catalogue

### Safety

| # | Feature | Status | What exists today |
|---|---|---|---|
| F1 | Photo safety check | ✅ | Photo → vision extraction (`app/llm.py`) → gate → verdict card. Real reading needs `OPENAI_API_KEY`; offline a sample extraction is used. |
| F2 | Barcode safety check (Open Food Facts) | 🔵 | Procedure written in the `food-safety-check` skill; `pyzbar` in requirements; no code path yet. |
| F3 | Text safety check ("can I eat tiramisu?") | ✅ | Dish decomposed into typical + likely-hidden ingredients, same gate. |
| F4 | Hidden-allergen synonyms | ✅ | **145** label terms → 14 allergens: whey, casein, E966, lactitol → milk; albumin, lysozyme, E1105 → egg; Worcestershire sauce, fish sauce, surimi, anchovy → fish; lecithin, E322, tamari, miso, edamame, natto → soy; semolina, spelt, durum, bulgur, seitan, farro, kamut → wheat. |
| F5 | False-positive guards | ✅ | **23** patterns: coconut/almond/oat milk, cocoa butter, nutmeg, water chestnut, buckwheat, eggplant… |
| F6 | Per-allergen severity policy | ✅ | mild / moderate / severe / anaphylactic decide how traces are treated. |
| F7 | Fail-closed on unreadable input | ✅ | Readability < 0.85, `unreadable` or `not_food` → **CAN'T VERIFY** (treat as not safe). |
| F8 | Restaurant menu scan | 🟡 | Procedure in the `eating-out` skill (agent); the bot's "Scan a menu" button is not wired yet. |
| F9 | Allergy card (`/card`) | 🟡 | English card with severe allergens highlighted. Local language and emergency number: roadmap. |
| F10 | Cross-contamination guard | ✅ | "May contain" lines block at severe/anaphylactic, caution otherwise. |
| F11 | Multi-language labels | 🟡 | Extraction prompt transcribes any language and translates; not yet validated on real foreign labels. |

### Planning & meals

| # | Feature | Status | What exists today |
|---|---|---|---|
| F12 | Weekly meal plan | 🟡 | `/plan` builds 7 dinners, screens each recipe through the gate, stores the schedule and builds the shopping list. Macro ±5 %, expiring-first and calendar constraints are only requested in the planner prompt, not enforced. Known issue: recipes are screened like cooked-dish photos, so for severe allergies every meal is flagged. |
| F13 | Swap a single meal | 🔵 | "Swap" button exists, no handler. |
| F14 | Leftover chaining | 🟡 | Planner prompt asks for leftover remixes; shown as a tag on the plan card; not enforced. |
| F15 | Recipe import & make-safe | 🟡 | `import-recipe` skill (agent); no bot code. |
| F16 | Symptom–food correlation | 🔵 | Symptoms are stored (`/symptom`); the weekly analysis is not built. |

### Calorie & macro tracking

| # | Feature | Status | What exists today |
|---|---|---|---|
| F17 | Personal calorie target (Mifflin–St Jeor) | ✅ | Calculated at sign-up from sex, age, height, weight, activity and goal. Manual override: roadmap. |
| F18 | Daily macro dashboard | ✅ | Calorie ring + protein/carb/fat bars from `food_log`, colour-coded against target. |
| F19 | Meal logging (text / photo / barcode / voice) | 🟡 | Text logging works but records a fixed 500 kcal placeholder; photo, barcode and voice: roadmap. |
| F20 | Dynamic weekly rebalancing | 🔵 | — |
| F21 | Adaptive recalibration from weight trend | 🔵 | Weight is stored and charted; recalibration not built. |

### Shopping & pantry

| # | Feature | Status | What exists today |
|---|---|---|---|
| F22 | Pantry-aware shopping list | ✅ | Needed − pantry, exact quantities, grouped by store section, sent as an image. Marking items bought works by button; per-item buttons under the card: roadmap. |
| F23 | Pantry sync 4×/week | 🔵 | `pantry-sync` skill written; schedule not registered. |
| F24 | Spoilage routing (use expiring items first) | 🔵 | Expiry dates stored; not enforced by the planner. |
| F25 | Macro-preserving substitutions ("salmon sold out") | 🔵 | Described in the `handle-friction` skill. |
| F26 | Saturday shopping reminder | 🔵 | Part of the planned schedule. |

### Daily autonomous actions

| # | Feature | Status | What exists today |
|---|---|---|---|
| F27 | 16:00 tonight's-meal preview | 🔵 | `daily-nudge` skill written; schedule not registered. |
| F28 | 17:30 full recipe delivery | 🔵 | Same. |
| F29 | "Too tired" fallback | 🟡 | Pauses tonight's planned meal. The quick-meal suggestion is fixed text, not yet chosen from the user's pantry and allergies. |

### Visuals (every structured answer is an image)

| # | Feature | Status | What exists today |
|---|---|---|---|
| F30 | Verdict card | ✅ | Red / amber / green / grey band, item, reasons (matched term → allergen, severity, where found), disclaimer. |
| F31 | Today dashboard | ✅ | Calorie ring + macro bars. |
| F32 | Weekly bar chart | ✅ | 7 days vs target line, colour by 85–115 % band. |
| F33 | Monthly trend chart | ✅ | 30 days, 7-day rolling average, target, weight on a second axis. |
| F34 | Safety-check donut | ✅ | Safe / caution / unsafe checks of the week. |
| F35 | Meal plan card | ✅ | One row per day: title, minutes, kcal, tags. |
| F36 | Shopping card | ✅ | Grouped by store section with quantities. |
| F37 | Profile card | ✅ | Allergies with severity colours, diet, goal, targets, cooking time. |

### Smart adaptations

| # | Feature | Status | What exists today |
|---|---|---|---|
| F38 | Batch-cooking mode | 🔵 | Planner constraint exists but is off. |
| F39 | Cooking-skill progression | 🔵 | `cooking_skill` field in the profile. |
| F40 | Eating window / fasting | 🔵 | `eating_window` field in the profile. |
| F41 | Health-flag support (e.g. low ferritin) | 🔵 | `health_flags` field in the profile. |
| F42 | Medication–food interaction flags | 🔵 | — |

### Integrations (via Hermes MCP servers)

| # | Feature | Status |
|---|---|---|
| F43 | Google Calendar (eating out, gym days) | 🔵 |
| F44 | Weather (hot day → cold meals, hydration) | 🔵 |
| F45 | To-do apps (mirror the shopping list) | 🔵 |
| F46 | Notes (recipe book in Notion / Obsidian) | 🔵 |
| F47 | Email weekly summary | 🔵 |
| F48 | Smart scale / Home Assistant weight logging | 🔵 |

---

## 2. Added in this phase (all ✅)

| # | Feature | Details |
|---|---|---|
| N1 | Step-by-step sign-up | 11 questions, mostly buttons; progress saved in `onboarding_state`; survives restarts; commands mid-sign-up resume the current question; bad numbers re-asked; `/start` for registered users says "Welcome back". |
| N2 | Allergy names as people type them | "dairy", "lactose" → milk; "gluten" → wheat; "nuts" → tree nut **and** peanut; plurals ("Peanuts"). Fixes a fail-open defect where these matched nothing. |
| N3 | Unknown allergens never SAFE | An allergen without a synonym list (e.g. kiwi) is matched literally and caps the verdict at CAUTION. |
| N4 | Eggplant ≠ egg | New false-positive guard, also migrated into existing databases. |
| N5 | Button grid without slashes | Persistent keyboard under the input ("📊 Today", "🍽 Plan"…); typing "today" works too. |
| N6 | Allow-list | `ALLOWED_TELEGRAM_IDS` restricts who can use the bot. |
| N7 | Per-user data ownership | A user can only mark their own shopping items as bought. |
| N8 | End-to-end test with a simulated Telegram | `tests/e2e_fake_telegram.py`: 80 scripted actions through the real polling loop. |
| N9 | Hardened deployment + restored agent | systemd service as an unprivileged user; Hermes Agent with persona, memory and 947 messages of history restored from backup. |

---

## 3. Commands and buttons

| Command / button | Status | What happens |
|---|---|---|
| **Start** | ✅ | Sign-up for new users; "Welcome back" + menu for registered users |
| **Menu** · **Help** | ✅ | 12-button inline menu · short explanation |
| **Check** | ✅ | Dish name → verdict card; photo → verdict card. Sub-buttons (photo / barcode / text / menu): 🔵 |
| **Today** · **Week** · **Month** | ✅ | Dashboard · weekly chart · monthly trend |
| **Plan** | 🟡 | 7-day plan card + shopping card (see F12) |
| **Shopping** | ✅ | Shopping card |
| **Tonight** | 🟡 | Currently shows today's dashboard; tonight's meal with Cooking / Swap / Recipe buttons: 🔵 |
| **Log** | 🟡 | Text log with placeholder calories (see F19) |
| **Tired** | 🟡 | See F29 |
| **Symptom** | ✅ | `/symptom bloating after lunch` is stored. Symptom picker buttons: 🔵 |
| **Report** | ✅ | Week chart + month chart + safety donut |
| **Card** | ✅ | Allergy card text |
| **Profile** | ✅ | Profile card. Editing: 🔵 |
| Free text | 🟡 | "can I eat…", "tired", "plan" are recognised; everything else is treated as a food check until the Hermes chat bridge is connected |

---

## 4. Workflows

### 4.1 Sign-up
`/start` → welcome + disclaimer → name → allergies (tap or type, Done / None) → severity for each
allergy → diet → goal → sex → age → height → weight → activity → cooking time → targets calculated
→ profile card + menu. Each answer is stored in `onboarding_state` before the next question is asked.

### 4.2 Food safety check
```
input ──► 1. classify: photo · dish name · (barcode: roadmap)
      ──► 2. model extracts JSON: image_type, readability, identified_ingredients,
             likely_hidden_ingredients, precautionary_warnings          ← the model's ONLY job
      ──► 3. safety_gate.py: normalise → resolve the user's allergy names → match 145 synonyms
             → skip 23 false-positive patterns → apply the policy, strictest first
      ──► 4. verdict card (PNG) + text reasons + disclaimer → logged in food_log
```
Policy: unusable input → CAN'T VERIFY · declared allergen → DO NOT EAT · trace at severe/anaphylactic →
DO NOT EAT · trace or likely-hidden at lower severity → CAUTION · allergen without synonym list →
CAUTION · cooked dish + severe allergy → CAUTION · cooked dish otherwise → LIKELY SAFE · full clean
label → SAFE.

### 4.3 Weekly plan and shopping
Profile + pantry → planner model returns 7 days of recipes → every recipe re-screened by the gate →
`recipes` + `meal_schedule` written → shopping list = required − pantry, grouped by section → plan card +
shopping card.

### 4.4 Calorie maths
BMR = 10·kg + 6.25·cm − 5·age + 5 (men) / − 161 (women) · TDEE = BMR × 1.2 / 1.375 / 1.55 / 1.725 / 1.9
· target = TDEE × 0.80 (lose) / 1.00 (maintain) / 1.12 (gain) · macros 30 % protein, 40 % carbs, 30 % fat
(4 / 4 / 9 kcal per gram).

### 4.5 Planned autonomous schedule (🔵)

| When | Action |
|---|---|
| Sunday 09:00 | Weekly plan + shopping list |
| Daily 16:00 / 17:30 / 21:30 | Tonight's preview · full recipe · one gentle follow-up |
| Saturday 18:00 | Shopping reminder for pending items |
| Sunday 20:00 | Weekly report: 3 charts + symptom correlation |
| Mon / Wed / Fri / Sun 23:00 | Pantry sync + distilled memory update |

---

## 5. The 15 Hermes skills

| Skill | Trigger | Job |
|---|---|---|
| onboard-user | /start, new user | Interview → profile → menu |
| food-safety-check | photo, "can I eat X?" | Extract → gate → verdict card |
| charts-dashboard | /today /week /month | food_log → chart → photo |
| weekly-plan | Sunday 09:00, "plan my week" | Profile + pantry → plan → re-screen → card |
| shopping-assistant | /shopping, Saturday 18:00 | Pantry diff → grouped list → reminder |
| daily-nudge | 16:00 / 17:30 / 21:30 | Preview → recipe → follow-up |
| log-meal | /log, plate photo, voice | Estimate macros → food_log → dashboard |
| handle-friction | "tired", "sold out" | Fallback meal or substitution + rebalance |
| pantry-sync | Mon/Wed/Fri/Sun 23:00 | Reconcile → subtract → expiry flags → memory |
| weekly-report | Sunday 20:00 | Aggregate → 3 charts → correlation → recalibrate |
| update-profile | "I'm also allergic to…" | Patch profile → re-screen the week |
| eating-out | menu photo, /card | Per-dish gate → safe / ask / avoid |
| import-recipe | recipe URL, "make safe" | Extract → screen → substitute → rescale |
| life-sync | calendar / weather / todo / email | Integrations via MCP servers |
| visual-output | every structured reply | Convention: answer with images |

---

## Roadmap

| Phase | Scope | Status |
|---|---|---|
| **1. Safety core & pilot** | Deterministic gate, synonyms and guards, charts and cards, sign-up, button grid, access control, tests, server deployment, agent restored | ✅ done |
| **2. Core flows** (design agreed) | Engine that returns replies (testable without Telegram) + CLI for the agent; bot as front door with a Hermes bridge for free chat (per-user sessions, "typing…", fallback when the agent is down); wire the 13 silent buttons; real meal-logging estimates; HTML escaping; screen planned recipes as labels; real "Tonight" and pantry-based "Too tired" | next |
| **3. Better inputs** | Barcode → Open Food Facts (F2), menu scan in the bot (F8), swap one meal (F13), photo / voice logging (F19) | planned |
| **4. Autonomy** | Hermes cron jobs calling the CLI: daily nudges, Sunday plan and report, Saturday reminder, pantry sync, preference memory (F23, F26–F28) | planned |
| **5. Insights & adaptation** | Symptom–food correlation (F16), weekly rebalancing (F20), weight-based recalibration (F21), profile editing, Persian interface | planned |
| **6. Integrations & scale** | Calendar, weather, to-do, notes, email, smart scale (F43–F48); health flags and medication information (F41–F42); PostgreSQL and webhooks beyond a 3–10 user pilot | planned |

---

*NutriGent is an assistive tool, not a medical device. It does not diagnose, treat or replace a
dietitian, allergist or doctor, and it cannot guarantee allergy safety — it reduces risk.*
