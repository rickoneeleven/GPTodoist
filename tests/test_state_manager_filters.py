import unittest

import state_manager


class StateManagerFilterTests(unittest.TestCase):
    def test_get_active_filter_details_accepts_string_flag(self):
        original_get_filters = state_manager.get_filters
        try:
            state_manager.get_filters = lambda: [  # type: ignore[assignment]
                {"id": 1, "filter": "A", "isActive": "0", "project_id": None},
                {"id": 2, "filter": "B", "isActive": "1", "project_id": "p"},
            ]
            flt, proj = state_manager.get_active_filter_details()
        finally:
            state_manager.get_filters = original_get_filters  # type: ignore[assignment]

        self.assertEqual(flt, "B")
        self.assertEqual(proj, "p")

    def test_get_active_filter_details_accepts_boolean_flag(self):
        original_get_filters = state_manager.get_filters
        try:
            state_manager.get_filters = lambda: [  # type: ignore[assignment]
                {"id": 1, "filter": "A", "isActive": False, "project_id": None},
                {"id": 2, "filter": "B", "isActive": True, "project_id": None},
            ]
            flt, proj = state_manager.get_active_filter_details()
        finally:
            state_manager.get_filters = original_get_filters  # type: ignore[assignment]

        self.assertEqual(flt, "B")
        self.assertIsNone(proj)


if __name__ == "__main__":
    unittest.main()
