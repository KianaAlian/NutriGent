"""Recommended onboarding inline keyboards are available for the onboarding flow."""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "shared"))

import telegram_menu as menu


def _labels(keyboard):
    return [button["text"] for row in keyboard["inline_keyboard"] for button in row]


def _callbacks(keyboard):
    return [button["callback_data"] for row in keyboard["inline_keyboard"] for button in row]


class OnboardingButtonTests(unittest.TestCase):
    def test_onboarding_choice_buttons_match_recommended_flow(self):
        expected = {
            "onboarding_severity_menu": ["Mild", "Moderate", "Severe", "Anaphylactic"],
            "onboarding_diet_menu": ["None", "Vegetarian", "Vegan", "Halal", "Keto", "Paleo", "Gluten-free", "Other (type)"],
            "onboarding_goal_menu": ["🔽 Lose weight", "➡️ Maintain", "🔼 Gain muscle / weight", "⚡ Energy / health"],
            "onboarding_activity_menu": ["Sedentary", "Light", "Moderate", "Active", "Athlete"],
            "onboarding_cooking_skill_menu": ["Beginner", "Intermediate", "Confident"],
            "onboarding_cook_time_menu": ["15 min", "30 min", "45 min", "60+ min"],
            "onboarding_budget_menu": ["Tight", "Normal", "Flexible"],
        }

        for function_name, labels in expected.items():
            with self.subTest(function_name=function_name):
                keyboard = getattr(menu, function_name)()
                self.assertEqual(_labels(keyboard), labels)
                self.assertTrue(all(callback.startswith("onboard:") for callback in _callbacks(keyboard)))

    def test_onboarding_free_text_helpers_include_skip_and_photo_options(self):
        self.assertEqual(_labels(menu.onboarding_skip_menu("health_flags")), ["Skip"])
        self.assertEqual(_callbacks(menu.onboarding_skip_menu("health_flags")), ["onboard:health_flags:skip"])

        self.assertEqual(_labels(menu.onboarding_pantry_menu()), ["📷 Send pantry photo", "⌨️ Type staples", "Skip for now"])
        self.assertEqual(_callbacks(menu.onboarding_pantry_menu()), [
            "onboard:pantry:photo",
            "onboard:pantry:text",
            "onboard:pantry:skip",
        ])


if __name__ == "__main__":
    unittest.main()
