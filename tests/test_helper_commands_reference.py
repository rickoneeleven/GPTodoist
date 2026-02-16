import unittest

import helper_commands


class StartupCommandReferenceTests(unittest.TestCase):
    def test_reference_includes_due_commands(self):
        command_map = dict(helper_commands.STARTUP_COMMAND_REFERENCE)
        self.assertIn("due <due_string|day>", command_map)
        self.assertIn("due long <index> <due_text>", command_map)
        self.assertIn("time long <index> <schedule>", command_map)

    def test_print_startup_reference_does_not_raise(self):
        captured = []
        original_print = helper_commands.print
        try:
            helper_commands.print = lambda *args, **kwargs: captured.append(args[0] if args else "")  # type: ignore[assignment]
            helper_commands.print_startup_command_reference()
        finally:
            helper_commands.print = original_print  # type: ignore[assignment]

        self.assertTrue(any("Commands Quick Reference" in str(line) for line in captured))
        self.assertTrue(any("due long <index> <due_text>" in str(line) for line in captured))


if __name__ == "__main__":
    unittest.main()
