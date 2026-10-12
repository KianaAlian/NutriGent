import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))
import db, safety_gate
from safety_gate import safety_verdict

os.environ["DIET_DB"] = "/tmp/test_diet.db"
db.DB_PATH = "/tmp/test_diet.db"
if os.path.exists("/tmp/test_diet.db"): os.remove("/tmp/test_diet.db")
safety_gate.conn = db.conn
db.init_db()

MILK_PEANUT = {"allergies": [{"allergen":"milk","severity":"mild"},
                             {"allergen":"peanut","severity":"anaphylactic"}]}

CASES = [
  # name, extraction, profile, expected_level
  ("direct milk via 'whey'",
   {"image_type":"ingredient_label","readability":0.95,
    "identified_ingredients":["sugar","whey powder","cocoa"]}, MILK_PEANUT, "UNSAFE"),
  ("hidden milk via 'casein'",
   {"image_type":"ingredient_label","readability":0.95,
    "identified_ingredients":["sodium caseinate","salt"]}, MILK_PEANUT, "UNSAFE"),
  ("anaphylactic peanut trace blocks",
   {"image_type":"ingredient_label","readability":0.95,
    "identified_ingredients":["oats","sugar"],
    "precautionary_warnings":["may contain traces of peanut"]}, MILK_PEANUT, "UNSAFE"),
  ("mild milk trace -> caution only",
   {"image_type":"ingredient_label","readability":0.95,
    "identified_ingredients":["rice","salt"],
    "precautionary_warnings":["may contain traces of milk"]}, MILK_PEANUT, "CAUTION"),
  ("blurry label fails closed",
   {"image_type":"ingredient_label","readability":0.40,
    "identified_ingredients":["sugar"]}, MILK_PEANUT, "UNVERIFIED"),
  ("cooked dish + anaphylaxis -> caution",
   {"image_type":"prepared_food","readability":0.9,
    "identified_ingredients":["rice","vegetables","chicken"]}, MILK_PEANUT, "CAUTION"),
  ("clean label is SAFE",
   {"image_type":"ingredient_label","readability":0.95,
    "identified_ingredients":["water","tomato","basil","salt"]}, MILK_PEANUT, "SAFE"),
  ("FALSE-POSITIVE GUARD: coconut milk not dairy",
   {"image_type":"ingredient_label","readability":0.95,
    "identified_ingredients":["coconut milk","rice","lime"]}, MILK_PEANUT, "SAFE"),
  ("FALSE-POSITIVE GUARD: nutmeg not tree nut",
   {"image_type":"ingredient_label","readability":0.95,
    "identified_ingredients":["flour-free oats","nutmeg","cinnamon"]},
   {"allergies":[{"allergen":"tree nut","severity":"severe"}]}, "SAFE"),
  ("worcestershire trips fish (anchovy)",
   {"image_type":"ingredient_label","readability":0.95,
    "identified_ingredients":["beef","worcestershire sauce"]},
   {"allergies":[{"allergen":"fish","severity":"moderate"}]}, "UNSAFE"),
  ("not_food fails closed",
   {"image_type":"not_food","readability":0.9}, MILK_PEANUT, "UNVERIFIED"),
  ("e-number sulphite exact match",
   {"image_type":"ingredient_label","readability":0.95,
    "identified_ingredients":["grapes","e220"]},
   {"allergies":[{"allergen":"sulphite","severity":"moderate"}]}, "UNSAFE"),
  # --- allergy names as users actually type them (must never fail open) ---
  ("'dairy' resolves to milk",
   {"image_type":"ingredient_label","readability":0.95,
    "identified_ingredients":["milk powder","sugar"]},
   {"allergies":[{"allergen":"dairy","severity":"severe"}]}, "UNSAFE"),
  ("'lactose' resolves to milk (whey)",
   {"image_type":"ingredient_label","readability":0.95,
    "identified_ingredients":["whey","sugar"]},
   {"allergies":[{"allergen":"lactose","severity":"severe"}]}, "UNSAFE"),
  ("plural 'Peanuts' resolves to peanut",
   {"image_type":"ingredient_label","readability":0.95,
    "identified_ingredients":["peanut butter"]},
   {"allergies":[{"allergen":"Peanuts","severity":"anaphylactic"}]}, "UNSAFE"),
  ("'gluten' resolves to wheat",
   {"image_type":"ingredient_label","readability":0.95,
    "identified_ingredients":["wheat flour","water"]},
   {"allergies":[{"allergen":"gluten","severity":"severe"}]}, "UNSAFE"),
  ("'nuts' covers tree nuts",
   {"image_type":"ingredient_label","readability":0.95,
    "identified_ingredients":["almonds","salt"]},
   {"allergies":[{"allergen":"nuts","severity":"severe"}]}, "UNSAFE"),
  ("'nuts' covers peanuts",
   {"image_type":"ingredient_label","readability":0.95,
    "identified_ingredients":["peanut oil"]},
   {"allergies":[{"allergen":"nuts","severity":"severe"}]}, "UNSAFE"),
  ("unknown allergen literal hit is UNSAFE",
   {"image_type":"ingredient_label","readability":0.95,
    "identified_ingredients":["kiwi fruit","sugar"]},
   {"allergies":[{"allergen":"kiwi","severity":"severe"}]}, "UNSAFE"),
  ("unknown allergen never yields SAFE",
   {"image_type":"ingredient_label","readability":0.95,
    "identified_ingredients":["water","salt"]},
   {"allergies":[{"allergen":"kiwi","severity":"mild"}]}, "CAUTION"),
  ("FALSE-POSITIVE GUARD: eggplant not egg",
   {"image_type":"ingredient_label","readability":0.95,
    "identified_ingredients":["eggplant","olive oil"]},
   {"allergies":[{"allergen":"egg","severity":"severe"}]}, "SAFE"),
]

passed = 0
for name, ext, prof, expected in CASES:
    v = safety_verdict(ext, prof)
    ok = v.level == expected
    passed += ok
    print(f"[{'PASS' if ok else 'FAIL'}] {name}: got {v.level}, expected {expected}")
    if not ok: print("   ->", v.message().replace("\n"," | "))

print(f"\n{passed}/{len(CASES)} passed")
# Safety-critical assertion: zero misses on seeded allergens
sys.exit(0 if passed == len(CASES) else 1)
