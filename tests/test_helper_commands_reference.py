import unittest

import helper_commands


class StartupCommandReferenceTests(unittest.TestCase):
    def test_reference_includes_due_commands(self):
        command_map = dict(helper_commands.STARTUP_COMMAND_REFERENCE)
        self.assertIn("due <due_string|day>", command_map)
        self.assertIn("due long <index> <due_text>", command_map)
        self.assertIn("time long <index> <schedule>", command_map)
        self.assertIn("done long <index>", command_map)

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
        self.assertTrue(any("done long <index>" in str(line) for line in captured))

    def test_done_long_dispatches_to_complete_task(self):
        calls = []
        original_complete_task = helper_commands.helper_todoist_long.complete_task
        original_subprocess_call = helper_commands.subprocess.call
        try:
            helper_commands.helper_todoist_long.complete_task = (  # type: ignore[assignment]
                lambda api, index, skip_logging=False: calls.append((api, index, skip_logging))
            )
            helper_commands.subprocess.call = lambda *_args, **_kwargs: 0  # type: ignore[assignment]
            handled = helper_commands.process_command(api=object(), user_message="done long 12")
        finally:
            helper_commands.helper_todoist_long.complete_task = original_complete_task  # type: ignore[assignment]
            helper_commands.subprocess.call = original_subprocess_call  # type: ignore[assignment]

        self.assertTrue(handled)
        self.assertEqual(len(calls), 1)
        self.assertEqual(calls[0][1], 12)
        self.assertFalse(calls[0][2])


if __name__ == "__main__":
    unittest.main()
