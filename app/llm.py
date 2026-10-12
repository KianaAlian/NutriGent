"""
OpenAI engine adapter for NutriGent.

This is the ONLY runtime module that talks to OpenAI. The rest of the bot treats
these functions as pure extract/generate helpers and always routes safety through
shared/safety_gate.py. If OPENAI_API_KEY is not set, deterministic offline stubs
are used so the demo/test suite still runs without network access.
"""
import os, json, base64

PROMPTS = os.path.join(os.path.dirname(__file__), "..", "shared", "prompts")


def _client():
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        return None
    from openai import OpenAI
    return OpenAI(api_key=key)


def _read_prompt(name):
    with open(os.path.join(PROMPTS, name), encoding="utf-8") as f:
        return f.read()


def _offline_image_stub(image_path, allergens):
    return {
        "image_type": "ingredient_label",
        "language_detected": "en",
        "ocr_text": "sugar, whey powder, cocoa",
        "identified_ingredients": ["sugar", "whey powder", "cocoa"],
        "likely_hidden_ingredients": [],
        "precautionary_warnings": [],
        "menu_items": [],
        "readability": 0.95,
        "notes": "Offline stub: set OPENAI_API_KEY for real vision extraction.",
    }


def extract_from_image(image_path, allergens):
    """Send a food/label/menu photo to the vision model. Returns extraction dict."""
    client = _client()
    if client is None:
        return _offline_image_stub(image_path, allergens)

    with open(image_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode()

    resp = client.chat.completions.create(
        model=os.environ.get("OPENAI_VISION_MODEL", "gpt-4o"),
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _read_prompt("extractor.txt")},
            {"role": "user", "content": [
                {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{b64}"}},
                {"type": "text", "text": (
                    "User allergens for context only (do NOT decide safety; "
                    f"deterministic code does that): {json.dumps(allergens)}"
                )},
            ]},
        ],
        max_tokens=1000,
    )
    return json.loads(resp.choices[0].message.content)


def _offline_text_stub(text):
    lower = (text or "").lower()
    ingredients = [text]
    hidden = []
    if "peanut" in lower:
        ingredients += ["peanut"]
    if any(w in lower for w in ("cookie", "cake", "tiramisu", "cream", "butter")):
        hidden += ["wheat flour", "butter", "egg", "milk"]
    return {
        "image_type": "prepared_food",
        "language_detected": "en",
        "ocr_text": text,
        "identified_ingredients": ingredients,
        "likely_hidden_ingredients": hidden,
        "precautionary_warnings": [],
        "menu_items": [],
        "readability": 1.0,
        "notes": "Offline text decomposition stub: set OPENAI_API_KEY for full extraction.",
    }


def extract_from_text(text):
    """Decompose a dish name into likely ingredients. Returns extraction dict."""
    client = _client()
    if client is None:
        return _offline_text_stub(text)

    resp = client.chat.completions.create(
        model=os.environ.get("OPENAI_TEXT_MODEL", "gpt-4o"),
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _read_prompt("extractor.txt")},
            {"role": "user", "content": (
                f"The user is asking about: {text!r}. This is a text description, not an image. "
                "Return the same JSON schema as if it were an image, set image_type to "
                "prepared_food, and list typical observed and likely hidden ingredients. "
                "Readability = 1.0; be thorough about sauces, stocks, coatings, garnishes."
            )},
        ],
        max_tokens=800,
    )
    return json.loads(resp.choices[0].message.content)


def _offline_week_stub(profile, pantry):
    titles = [
        "Chickpea spinach curry", "Turkey rice bowls", "Egg-free pesto pasta",
        "Leftover curry wrap", "Cod with potatoes", "Tofu stir-fry", "Bean chili",
    ]
    days = []
    for i, title in enumerate(titles):
        days.append({
            "date": None,
            "meals": [{
                "meal_type": "dinner",
                "title": title,
                "cook_minutes": [25, 40, 15, 10, 35, 20, 45][i],
                "kcal": [620, 700, 540, 560, 610, 480, 650][i],
                "protein_g": 30,
                "carbs_g": 70,
                "fat_g": 18,
                "ingredients": [
                    {"name": "chickpeas", "qty": 200, "unit": "g"},
                    {"name": "spinach", "qty": 150, "unit": "g"},
                ],
                "steps": ["Cook safely; verify packaged ingredients against your profile."],
                "uses_pantry": [],
                "leftover_of": "Tue batch" if i == 3 else None,
                "fallback_candidate": i == 2,
            }],
        })
    return {"days": days, "shopping_additions_hint": ["olive oil"]}


def generate_week(profile, pantry):
    """Generate a 7-day meal plan. Result must still be re-screened by the gate."""
    client = _client()
    if client is None:
        return _offline_week_stub(profile, pantry)

    inputs = json.dumps({
        "profile": profile,
        "pantry": pantry,
        "preferences": {},
        "constraints": {
            "meals_per_day": 1,
            "batch_mode": False,
            "leftover_policy": "chain_at_day_2",
            "calendar_events": [],
        },
    }, default=str)

    resp = client.chat.completions.create(
        model=os.environ.get("OPENAI_PLANNER_MODEL", "gpt-4o"),
        response_format={"type": "json_object"},
        messages=[
            {"role": "system", "content": _read_prompt("planner.txt")},
            {"role": "user", "content": inputs},
        ],
        max_tokens=4000,
    )
    return json.loads(resp.choices[0].message.content)
