from __future__ import annotations

import unittest

from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from flex_agent.ui.events import StepRecord, StepStatus, StreamEventParser
from flex_agent.ui.labels import summarize_tool_args, tool_label
from flex_agent.i18n import set_language


class StreamEventParserTests(unittest.TestCase):
    def test_tool_call_and_result_create_running_then_done_steps(self) -> None:
        parser = StreamEventParser()
        ai = AIMessage(
            content="",
            tool_calls=[
                {
                    "name": "batch_open_coding",
                    "args": {"text_ids": [1, 2, 3]},
                    "id": "call-1",
                }
            ],
        )
        tool = ToolMessage(content="OpenCoding processed 3/3 texts.", tool_call_id="call-1")

        first = parser.consume({"messages": [ai]})
        self.assertEqual(len(first.timeline), 1)
        self.assertIn("OpenCoding 批量编码", first.timeline[0].text)
        self.assertEqual(parser.steps["call-1"].status, StepStatus.RUNNING)

        second = parser.consume({"messages": [ai, tool]})
        self.assertEqual(parser.steps["call-1"].status, StepStatus.DONE)
        self.assertTrue(any("OpenCoding processed" in entry.text for entry in second.timeline))
        self.assertTrue(second.refresh_workspace)

    def test_todos_are_parsed_from_state(self) -> None:
        parser = StreamEventParser()
        update = parser.consume(
            {
                "messages": [],
                "todos": [
                    {"content": "init corpus", "status": "completed"},
                    {"content": "batch open coding", "status": "in_progress"},
                ],
            }
        )
        self.assertEqual(len(update.todos), 2)
        self.assertEqual(update.todos[0].status, "completed")
        self.assertEqual(update.todos[1].content, "batch open coding")

    def test_human_and_assistant_messages(self) -> None:
        parser = StreamEventParser()
        update = parser.consume(
            {
                "messages": [
                    HumanMessage(content="hello"),
                    AIMessage(content="world"),
                ]
            }
        )
        self.assertEqual([entry.kind for entry in update.timeline], ["user"])
        self.assertEqual(update.streaming_assistant, "world")
        flushed = parser.flush_assistant_text()
        self.assertEqual([entry.kind for entry in flushed.timeline], ["assistant"])

    def test_done_step_not_reappended_in_next_turn(self) -> None:
        parser = StreamEventParser()
        human1 = HumanMessage(content="hello")
        ai1 = AIMessage(
            content="",
            tool_calls=[
                {"name": "batch_open_coding", "args": {"text_ids": [1]}, "id": "call-1"}
            ],
        )
        tool1 = ToolMessage(content="done", tool_call_id="call-1")
        human2 = HumanMessage(content="thanks")
        ai2 = AIMessage(content="you're welcome")

        parser.consume({"messages": [human1, ai1]})
        parser.consume({"messages": [human1, ai1, tool1]})
        self.assertEqual(parser.steps["call-1"].status, StepStatus.DONE)

        update = parser.consume({"messages": [human1, ai1, tool1, human2, ai2]})

        step_entries = [
            e for e in update.timeline if e.kind == "step" and e.step_id == "call-1"
        ]
        self.assertEqual(
            len(step_entries),
            0,
            "DONE step must not be re-appended in next turn",
        )

    def test_note_user_message_deduplicates_stream_human(self) -> None:
        parser = StreamEventParser()
        noted = parser.note_user_message("once")
        streamed = parser.consume({"messages": [HumanMessage(content="once")]})
        self.assertEqual(len(noted.timeline), 1)
        self.assertEqual(len(streamed.timeline), 0)

    def test_note_user_message_emit_false_tracks_without_timeline(self) -> None:
        parser = StreamEventParser()
        noted = parser.note_user_message("once", emit=False)
        streamed = parser.consume({"messages": [HumanMessage(content="once")]})
        self.assertEqual(len(noted.timeline), 0)
        self.assertEqual(len(streamed.timeline), 0)

    def test_mark_interrupted_clears_pending_and_running_steps(self) -> None:
        parser = StreamEventParser()
        parser.pending_assistant_text = "partial"
        parser.steps["call-1"] = StepRecord(
            step_id="call-1",
            tool_name="task",
            label="子任务",
            summary="",
            status=StepStatus.RUNNING,
        )
        update = parser.mark_interrupted()
        self.assertEqual(parser.pending_assistant_text, "")
        self.assertEqual(update.steps["call-1"].status, StepStatus.ERROR)
        self.assertEqual(update.steps["call-1"].result_preview, "interrupted")
        self.assertEqual(update.activity_mode, "idle")

    def test_duplicate_messages_are_not_re_emitted(self) -> None:
        parser = StreamEventParser()
        message = HumanMessage(content="once")
        chunk = {"messages": [message]}
        first = parser.consume(chunk)
        second = parser.consume(chunk)
        self.assertEqual(len(first.timeline), 1)
        self.assertEqual(len(second.timeline), 0)

    def test_assistant_streaming_updates_text(self) -> None:
        parser = StreamEventParser()
        ai = AIMessage(content="hel")
        first = parser.consume({"messages": [ai]})
        second = parser.consume({"messages": [AIMessage(content="hello world")]})
        self.assertEqual(first.streaming_assistant, "hel")
        self.assertEqual(second.streaming_assistant, "hello world")
        self.assertEqual(len(second.timeline), 0)

    def test_replay_multi_turn_preserves_user_assistant_order(self) -> None:
        parser = StreamEventParser()
        update = parser.consume(
            {
                "messages": [
                    HumanMessage(content="first"),
                    AIMessage(
                        content="",
                        tool_calls=[
                            {
                                "name": "batch_open_coding",
                                "args": {},
                                "id": "call-1",
                            }
                        ],
                    ),
                    ToolMessage(content="ok", tool_call_id="call-1"),
                    AIMessage(content="answer one"),
                    HumanMessage(content="second"),
                    AIMessage(content="answer two"),
                ]
            }
        )
        flushed = parser.flush_assistant_text()
        timeline = update.timeline + flushed.timeline
        kinds_and_text = [(entry.kind, entry.text) for entry in timeline]
        self.assertEqual(kinds_and_text[0], ("user", "first"))
        self.assertEqual(kinds_and_text[-2], ("user", "second"))
        self.assertEqual(kinds_and_text[-1], ("assistant", "answer two"))
        assistant_texts = [text for kind, text in kinds_and_text if kind == "assistant"]
        self.assertEqual(assistant_texts, ["answer one", "answer two"])
        user_indices = [idx for idx, (kind, _text) in enumerate(kinds_and_text) if kind == "user"]
        assistant_indices = [
            idx for idx, (kind, _text) in enumerate(kinds_and_text) if kind == "assistant"
        ]
        self.assertTrue(user_indices[0] < assistant_indices[0])
        self.assertTrue(assistant_indices[0] < user_indices[1])
        self.assertTrue(user_indices[1] < assistant_indices[1])


class ToolLabelTests(unittest.TestCase):
    def test_tool_label_mapping(self) -> None:
        set_language("zh")
        self.assertEqual(tool_label("init_open_coding_run"), "初始化语料")
        self.assertEqual(tool_label("unknown_tool"), "unknown_tool")

    def test_tool_label_mapping_english(self) -> None:
        try:
            set_language("en")
            self.assertEqual(tool_label("init_open_coding_run"), "Initialize corpus")
            self.assertEqual(tool_label("batch_bob_code"), "Batch OpenCoding")
            self.assertEqual(
                summarize_tool_args("batch_open_coding", {"text_ids": [1, 2]}),
                "2 texts",
            )
        finally:
            set_language("zh")

    def test_task_summary(self) -> None:
        summary = summarize_tool_args(
            "task",
            {"subagent_type": "construct-induction", "description": "review codebook"},
        )
        self.assertIn("construct-induction", summary)


if __name__ == "__main__":
    unittest.main()
