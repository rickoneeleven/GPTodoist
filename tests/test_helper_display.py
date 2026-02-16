import unittest

import helper_display


class HelperDisplayTests(unittest.TestCase):
    def test_derive_today_overdue_query_intersects_active_filter(self):
        self.assertEqual(
            helper_display._derive_today_overdue_query("(no due date | today | overdue) & #RCP"),
            "(today | overdue) & ((no due date | today | overdue) & #RCP)",
        )

    def test_derive_today_overdue_query_falls_back_without_project_tag(self):
        self.assertEqual(helper_display._derive_today_overdue_query(None), "today | overdue")
        self.assertEqual(helper_display._derive_today_overdue_query("today | overdue"), "today | overdue")


if __name__ == "__main__":
    unittest.main()
