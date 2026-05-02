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

    def test_compact_memory_keeps_head_and_tail(self):
        content = "a" * 3000 + "b" * 3000 + "c" * 3000
        compact = all_ai.compact_memory(content, limit=4000)
        self.assertIn("[...older middle content omitted for prompt size...]", compact)
        self.assertTrue(compact.startswith("a"))
        self.assertTrue(compact.endswith("c" * 100))

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
                    {"file": str(path), "agent": "manual", "response_file": str(response)},
                )
            )
            content = path.read_text(encoding="utf-8")
            self.assertIn("## Turn 1 - manual", content)
            self.assertIn("좋은 질문", content)


if __name__ == "__main__":
    unittest.main()

