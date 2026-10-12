"""
Predefined, selectable Telegram UI so users never have to remember commands.

Two layers:
1. COMMANDS  -> the persistent slash-command menu (the "/" button next to the
   text box). Register once via setMyCommands or paste BOTFATHER_COMMANDS into
   @BotFather > /setcommands.
2. KEYBOARDS -> inline button grids the bot sends inside messages. Every routine
   action is a tap. callback_data is what your handler receives on tap.
"""

# ---- Layer 1: persistent slash menu -------------------------------------
COMMANDS = [
    ("menu",     "📋 Open the main menu"),
    ("check",    "🔍 Check if a food is safe (photo/barcode/name)"),
    ("today",    "📊 Today's calories & macros"),
    ("week",     "📈 This week's calorie chart"),
    ("month",    "🗓 This month's trend"),
    ("plan",     "🍽 Plan / show my week of meals"),
    ("shopping", "🛒 My shopping list"),
    ("tonight",  "🌙 What am I cooking tonight?"),
    ("log",      "✍️ Log what I ate"),
    ("tired",    "😴 Too tired to cook — quick fallback"),
    ("symptom",  "🩺 Log a symptom (bloating, energy…)"),
    ("report",   "📑 My weekly report card"),
    ("card",     "🆘 Allergy card for restaurants/travel"),
    ("profile",  "⚙️ View / edit my profile & allergies"),
    ("help",     "❓ How this bot works"),
]
# Paste-ready for @BotFather /setcommands (command - description, no slash)
BOTFATHER_COMMANDS = "\n".join(f"{c} - {d}" for c, d in COMMANDS)

# ---- Layer 2: inline keyboards (tappable grids) -------------------------
def _kb(rows):  # rows: list of list of (label, callback_data)
    return {"inline_keyboard":
            [[{"text": t, "callback_data": cb} for t, cb in row] for row in rows]}

def main_menu():
    return _kb([
        [("🔍 Check a food", "act:check"), ("📊 Today", "act:today")],
        [("🍽 My plan", "act:plan"),       ("🛒 Shopping", "act:shopping")],
        [("🌙 Tonight", "act:tonight"),    ("😴 Too tired", "act:tired")],
        [("📈 Week", "act:week"),          ("🗓 Month", "act:month")],
        [("✍️ Log meal", "act:log"),       ("🩺 Symptom", "act:symptom")],
        [("📑 Report", "act:report"),      ("⚙️ Profile", "act:profile")],
    ])

# ---- Layer 3: persistent button grid under the chat input ----------------
# Reply keyboards are per chat: send on /start and /help. Labels carry no slash;
# bot.py maps the label's word ("📊 Today" -> today) back to its command.
def persistent_main_keyboard():
    rows = [["📋 Menu", "🔍 Check", "📊 Today"], ["🍽 Plan", "🛒 Shopping", "🌙 Tonight"],
            ["📈 Week", "🗓 Month", "✍️ Log"], ["😴 Tired", "🩺 Symptom", "📑 Report"],
            ["🆘 Card", "⚙️ Profile"]]
    return {"keyboard": [[{"text": t} for t in row] for row in rows],
            "resize_keyboard": True, "one_time_keyboard": False, "is_persistent": True,
            "input_field_placeholder": "Choose a NutriGent action…"}

def check_menu():
    return _kb([
        [("📷 Send a photo", "check:photo"), ("🔢 Scan barcode", "check:barcode")],
        [("⌨️ Type a food name", "check:text"), ("📋 Scan a menu", "check:menu")],
        [("⬅️ Back", "act:menu")],
    ])

# ---- Onboarding inline keyboards -----------------------------------------
# The onboarding handler asks one question at a time; these helpers provide the
# recommended tappable choices from AGENT_PROMPT.md / onboard-user.
def onboarding_severity_menu(allergen=None):
    suffix = f":{allergen}" if allergen else ""
    return _kb([
        [("Mild", f"onboard:severity:mild{suffix}"),
         ("Moderate", f"onboard:severity:moderate{suffix}")],
        [("Severe", f"onboard:severity:severe{suffix}"),
         ("Anaphylactic", f"onboard:severity:anaphylactic{suffix}")],
    ])

ONBOARDING_ALLERGENS = [("Milk", "milk"), ("Egg", "egg"), ("Peanut", "peanut"), ("Tree nuts", "tree nut"),
                        ("Wheat", "wheat"), ("Soy", "soy"), ("Fish", "fish"), ("Shellfish", "shellfish"),
                        ("Sesame", "sesame")]

def onboarding_allergy_menu(selected=()):
    """Tap to toggle; picked ones show a check mark."""
    btns = [(("✓ " if v in selected else "") + label, f"onboard:allergy:{v}") for label, v in ONBOARDING_ALLERGENS]
    rows = [btns[i:i + 3] for i in range(0, len(btns), 3)]
    rows.append([("None", "onboard:allergy:none"), ("✅ Done", "onboard:allergy:done")])
    return _kb(rows)

def onboarding_sex_menu():
    return _kb([[("Male", "onboard:sex:male"), ("Female", "onboard:sex:female")]])

def onboarding_diet_menu():
    return _kb([
        [("None", "onboard:diet:none"), ("Vegetarian", "onboard:diet:vegetarian")],
        [("Vegan", "onboard:diet:vegan"), ("Halal", "onboard:diet:halal")],
        [("Keto", "onboard:diet:keto"), ("Paleo", "onboard:diet:paleo")],
        [("Gluten-free", "onboard:diet:gluten_free"), ("Other (type)", "onboard:diet:other")],
    ])

def onboarding_goal_menu():
    return _kb([
        [("🔽 Lose weight", "onboard:goal:lose"),
         ("➡️ Maintain", "onboard:goal:maintain")],
        [("🔼 Gain muscle / weight", "onboard:goal:gain"),
         ("⚡ Energy / health", "onboard:goal:energy_health")],
    ])

def onboarding_activity_menu():
    return _kb([
        [("Sedentary", "onboard:activity:sedentary"),
         ("Light", "onboard:activity:light")],
        [("Moderate", "onboard:activity:moderate"),
         ("Active", "onboard:activity:active")],
        [("Athlete", "onboard:activity:athlete")],
    ])

def onboarding_cooking_skill_menu():
    return _kb([
        [("Beginner", "onboard:cooking_skill:beginner")],
        [("Intermediate", "onboard:cooking_skill:intermediate"),
         ("Confident", "onboard:cooking_skill:confident")],
    ])

def onboarding_cook_time_menu():
    return _kb([
        [("15 min", "onboard:max_minutes:15"), ("30 min", "onboard:max_minutes:30")],
        [("45 min", "onboard:max_minutes:45"), ("60+ min", "onboard:max_minutes:60")],
    ])

def onboarding_budget_menu():
    return _kb([
        [("Tight", "onboard:budget:tight"), ("Normal", "onboard:budget:normal")],
        [("Flexible", "onboard:budget:flexible")],
    ])

def onboarding_skip_menu(field):
    return _kb([[("Skip", f"onboard:{field}:skip")]])

def onboarding_pantry_menu():
    return _kb([
        [("📷 Send pantry photo", "onboard:pantry:photo"),
         ("⌨️ Type staples", "onboard:pantry:text")],
        [("Skip for now", "onboard:pantry:skip")],
    ])

def tonight_actions(date, meal):
    return _kb([
        [("✅ Cooking it", f"meal:cook:{date}:{meal}")],
        [("🔁 Swap meal", f"meal:swap:{date}:{meal}"), ("😴 Too tired", "act:tired")],
        [("📖 Show recipe", f"meal:recipe:{date}:{meal}")],
    ])

def log_meal_actions():
    return _kb([
        [("📷 Photo of plate", "log:photo"), ("⌨️ Type it", "log:text")],
        [("🎙 Voice note", "log:voice")],
        [("⬅️ Back", "act:menu")],
    ])

def shopping_item_button(item_id, name):
    return _kb([[("🛒 Got it", f"buy:{item_id}"), ("❌ Unavailable", f"nostock:{item_id}")]])

def symptom_picker():
    return _kb([
        [("😣 Bloating", "sym:bloating"), ("🔋 Low energy", "sym:low_energy")],
        [("🤕 Headache", "sym:headache"), ("🌿 Skin", "sym:skin")],
        [("Other", "sym:other"), ("⬅️ Back", "act:menu")],
    ])

def yes_no(action):
    return _kb([[("✅ Yes", f"{action}:yes"), ("❌ No", f"{action}:no")]])

def confirm_swap(date, meal):
    return _kb([[("🔁 Pick another", f"meal:reswap:{date}:{meal}"),
                 ("✅ Keep it", f"meal:cook:{date}:{meal}")]])

if __name__ == "__main__":
    print("=== Paste into @BotFather /setcommands ===\n")
    print(BOTFATHER_COMMANDS)
