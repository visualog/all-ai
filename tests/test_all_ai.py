import tempfile
import unittest
from pathlib import Path

import all_ai


class WorkbenchTests(unittest.TestCase):
    def test_next_agent_cycles_from_turn_count(self):
        state = all_ai.TopicState(Path("x.md"), "topic", [], "# Topic\n\ntopic\n")
        self.assertEqual(all_ai.next_agent(state, None), "architect")

        state.turns = ["architect", "explorer"]
        self.assertEqual(all_ai.next_agent(state, None), "researcher")

    def test_build_prompt_preserves_current_topic(self):
        state = all_ai.TopicState(Path("x.md"), "원래 주제", [], "# Topic\n\n원래 주제\n")
        prompt = all_ai.build_prompt(state, "architect")
        self.assertIn("Current topic:\n원래 주제", prompt)
        self.assertIn("Do not replace it with an unrelated example topic.", prompt)

    def test_compact_memory_keeps_head_and_tail(self):
        content = "a" * 3000 + "b" * 3000 + "c" * 3000
        compact = all_ai.compact_memory(content, limit=4000)
        self.assertIn("[...older middle content omitted for prompt size...]", compact)
        self.assertTrue(compact.startswith("a"))
        self.assertTrue(compact.endswith("c" * 100))

    def test_compact_memory_rejects_tiny_limit(self):
        with self.assertRaises(ValueError):
            all_ai.compact_memory("abc", limit=100)

    def test_init_and_add_turn(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "topic.md"
            all_ai.init_topic(type("Args", (), {"file": str(path), "topic": "테스트 주제", "force": False}))
            self.assertTrue(path.exists())

            response = Path(tmp) / "response.md"
            response.write_text("## New Contribution\n좋은 질문", encoding="utf-8")
            all_ai.add_turn(
                type(
                    "Args",
                    (),
                    {"file": str(path), "agent": "manual", "response_file": str(response), "response": None},
                )
            )
            content = path.read_text(encoding="utf-8")
            self.assertIn("## Turn 1 - manual", content)
            self.assertIn("좋은 질문", content)

    def test_add_turn_from_direct_response(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "topic.md"
            all_ai.init_topic(type("Args", (), {"file": str(path), "topic": "direct", "force": False}))
            all_ai.add_turn(
                type(
                    "Args",
                    (),
                    {"file": str(path), "agent": "quick", "response_file": None, "response": "Direct answer"},
                )
            )
            self.assertIn("Direct answer", path.read_text(encoding="utf-8"))

    def test_prompt_can_write_to_output_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "topic.md"
            out = Path(tmp) / "prompt.md"
            all_ai.init_topic(type("Args", (), {"file": str(path), "topic": "prompt output", "force": False}))
            all_ai.print_prompt(type("Args", (), {"file": str(path), "agent": "architect", "output": str(out)}))
            self.assertTrue(out.exists())
            self.assertIn("Your role:\narchitect", out.read_text(encoding="utf-8"))

    def test_export_defaults_next_to_topic_file(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "nested" / "topic.md"
            all_ai.init_topic(type("Args", (), {"file": str(path), "topic": "custom export", "force": False}))
            all_ai.export_summary(type("Args", (), {"file": str(path), "output": None}))
            self.assertTrue((path.parent / "custom-export-export.md").exists())


if __name__ == "__main__":
    unittest.main()
