# Telegram persistent buttons for NutriGent

Session lesson: the user wanted the command grid buttons to appear for **all users**, not only the current chat.

## Durable rule
Telegram has two different button surfaces:

1. **Bot-wide slash menu** (`setMyCommands` / BotFather `/setcommands`)
   - Shows commands in Telegram's `/` menu for everyone using the bot.
   - Does **not** create the big persistent keyboard under the message input.

2. **Per-chat reply keyboard** (`ReplyKeyboardMarkup` with `is_persistent=True`)
   - Creates the tappable grid under the user's input field.
   - Must be sent to each chat at least once.
   - Sending it to one user does not make it appear for every user.

## Recommended implementation
Add a helper in `shared/telegram_menu.py`:

```python
def persistent_main_keyboard():
    return {
        "keyboard": [
            [{"text":"📋 /menu"}, {"text":"🔍 /check"}, {"text":"📊 /today"}],
            [{"text":"🍽 /plan"}, {"text":"🛒 /shopping"}, {"text":"🌙 /tonight"}],
            [{"text":"📈 /week"}, {"text":"🗓 /month"}, {"text":"✍️ /log"}],
            [{"text":"😴 /tired"}, {"text":"🩺 /symptom"}, {"text":"📑 /report"}],
            [{"text":"🆘 /card"}, {"text":"⚙️ /profile"}],
        ],
        "resize_keyboard": True,
        "one_time_keyboard": False,
        "is_persistent": True,
        "input_field_placeholder": "Choose a NutriGent action…",
    }
```

Send this keyboard on:
- `/start` for every new user
- `/menu` for any existing user who asks
- onboarding completion
- optional broadcast/migration to known pilot chats when first introducing the keyboard

Inline keyboards can still be used inside individual messages for actions like `Got it`, `Unavailable`, `Swap`, or onboarding choices. Reply keyboards are for persistent global navigation.
