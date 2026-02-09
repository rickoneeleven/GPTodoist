import os
import tempfile
import unittest

import module_call_counter


class ModuleCallCounterTests(unittest.TestCase):
    def test_decorated_function_recovers_from_invalid_counter_file(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            counter_path = os.path.join(tmp_dir, "calls.json")
            with open(counter_path, "w") as f:
                f.write("")

            original_json_file = module_call_counter.json_file
            try:
                module_call_counter.json_file = counter_path

                def sample_fn():
                    return "ok"

                wrapped = module_call_counter.call_counter_decorator(sample_fn)
                self.assertEqual(wrapped(), "ok")

                loaded = module_call_counter._load_counts_unlocked()
                expected_key = f"{os.path.basename(sample_fn.__code__.co_filename)}:{sample_fn.__name__}"
                self.assertIn(expected_key, loaded)
                self.assertEqual(loaded[expected_key], 1)
            finally:
                module_call_counter.json_file = original_json_file


if __name__ == "__main__":
    unittest.main()
