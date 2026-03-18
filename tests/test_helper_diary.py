import unittest
from datetime import date

import helper_diary


class PreviousDiaryTaglineTests(unittest.TestCase):
    def test_search_starts_from_yesterday_and_prints_latest_prior_objective(self):
        captured = []
        calls = []

        original_find = helper_diary.state_manager.find_most_recent_objective
        original_print = helper_diary.print
        try:
            def fake_find(start_date, lookback_days=30):
                calls.append((start_date, lookback_days))
                return "ref home assistant automations", date(2026, 3, 13)

            helper_diary.state_manager.find_most_recent_objective = fake_find  # type: ignore[assignment]
            helper_diary.print = lambda *args, **kwargs: captured.append(args[0] if args else "")  # type: ignore[assignment]

            helper_diary.show_previous_objective_tagline(reference_date=date(2026, 3, 16))  # Monday
        finally:
            helper_diary.state_manager.find_most_recent_objective = original_find  # type: ignore[assignment]
            helper_diary.print = original_print  # type: ignore[assignment]

        self.assertEqual(calls[0][0], date(2026, 3, 15))  # Sunday (yesterday), then fallback handled by finder
        self.assertTrue(any("Friday, 13 March 2026" in str(line) for line in captured))
        self.assertTrue(any("ref home assistant automations" in str(line) for line in captured))

    def test_prints_warning_when_no_prior_objective_exists(self):
        captured = []

        original_find = helper_diary.state_manager.find_most_recent_objective
        original_print = helper_diary.print
        try:
            helper_diary.state_manager.find_most_recent_objective = (  # type: ignore[assignment]
                lambda *_args, **_kwargs: (None, None)
            )
            helper_diary.print = lambda *args, **kwargs: captured.append(args[0] if args else "")  # type: ignore[assignment]

            helper_diary.show_previous_objective_tagline(reference_date=date(2026, 3, 16))
        finally:
            helper_diary.state_manager.find_most_recent_objective = original_find  # type: ignore[assignment]
            helper_diary.print = original_print  # type: ignore[assignment]

        self.assertTrue(any("No previous diary tagline found before today." in str(line) for line in captured))


if __name__ == "__main__":
    unittest.main()
