import os
import tempfile
import unittest
from collections import deque
from datetime import datetime
from unittest.mock import Mock, mock_open, patch

import jimbo


def log_time(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


class DialogueTests(unittest.TestCase):
    def test_all_historical_ai_profiles_are_predefined(self):
        self.assertEqual(
            set(jimbo.ai_profiles), {"openai", "deepseek", "groq", "ollama"}
        )
        self.assertEqual(
            jimbo.ai_profiles["openai"]["model"], "openai/gpt-5.4-mini"
        )
        self.assertEqual(
            jimbo.ai_profiles["deepseek"]["model"], "deepseek-v4-flash-free"
        )
        self.assertEqual(
            jimbo.ai_profiles["ollama"]["model"], "qwen2.5-32b-ctx32k"
        )
        self.assertEqual(
            jimbo.ai_profiles["groq"]["model"], "openai/gpt-oss-120b"
        )
        self.assertEqual(
            jimbo.ai_profiles["deepseek"]["provider"], "openai-compatible"
        )
        self.assertEqual(
            jimbo.ai_profiles["deepseek"]["base_url"],
            "https://opencode.ai/zen/v1",
        )
        self.assertEqual(jimbo.ai_profiles["deepseek"]["auth_provider"], "opencode")
        self.assertEqual(jimbo.ai_profiles["groq"]["provider"], "openai-compatible")
        self.assertEqual(
            jimbo.ai_profiles["groq"]["base_url"],
            "https://api.groq.com/openai/v1",
        )
        self.assertEqual(
            os.path.basename(jimbo.ai_profiles["groq"]["api_key_path"]),
            "groq-api-key.txt",
        )
        self.assertEqual(jimbo.ai_profiles["ollama"]["provider"], "ollama")
        self.assertEqual(
            jimbo.ai_profiles["ollama"]["host"], "http://127.0.0.1:11434"
        )
        self.assertIs(jimbo.ai_profile, jimbo.ai_profiles[jimbo.ai_profile_name])
        self.assertEqual(jimbo.model_name, jimbo.ai_profile["model"])
        self.assertEqual(jimbo.model_identity, jimbo.ai_profile["identity"])

    def test_ai_profile_selects_its_provider_adapter(self):
        cases = (
            ("openai", "ask_opencode"),
            ("deepseek", "ask_openai_compatible"),
            ("groq", "ask_openai_compatible"),
            ("ollama", "ask_ollama"),
        )
        for profile_name, adapter_name in cases:
            profile = jimbo.ai_profiles[profile_name]
            with self.subTest(profile=profile_name):
                with patch.object(jimbo, "ai_profile", profile), patch.object(
                    jimbo, adapter_name, return_value="response"
                ) as adapter:
                    response = jimbo.ask_ai("prompt")

                self.assertEqual(response, "response")
                adapter.assert_called_once_with("prompt", profile)

    def test_deepseek_adapter_uses_historical_endpoint_without_sdk_retries(self):
        profile = jimbo.ai_profiles["deepseek"]
        result = Mock()
        result.choices = [Mock(message=Mock(content=" response "))]
        with patch("builtins.open", mock_open(
            read_data='{"opencode": {"key": "secret"}}'
        )), patch("openai.OpenAI") as constructor:
            constructor.return_value.chat.completions.create.return_value = result

            response = jimbo.ask_openai_compatible("prompt", profile)

        self.assertEqual(response, "response")
        constructor.assert_called_once_with(
            api_key="secret",
            base_url="https://opencode.ai/zen/v1",
            timeout=120,
            max_retries=0,
        )
        constructor.return_value.chat.completions.create.assert_called_once_with(
            model="deepseek-v4-flash-free",
            messages=[{"role": "user", "content": "prompt"}],
        )

    def test_groq_adapter_uses_key_file_and_hides_reasoning(self):
        profile = jimbo.ai_profiles["groq"]
        result = Mock()
        result.choices = [Mock(message=Mock(content=" response "))]
        with patch("builtins.open", mock_open(
            read_data="groq-secret"
        )), patch("openai.OpenAI") as constructor:
            constructor.return_value.chat.completions.create.return_value = result

            response = jimbo.ask_openai_compatible("prompt", profile)

        self.assertEqual(response, "response")
        constructor.assert_called_once_with(
            api_key="groq-secret",
            base_url="https://api.groq.com/openai/v1",
            timeout=120,
            max_retries=0,
        )
        constructor.return_value.chat.completions.create.assert_called_once_with(
            model="openai/gpt-oss-120b",
            messages=[{"role": "user", "content": "prompt"}],
            max_completion_tokens=256,
            extra_body={
                "include_reasoning": False,
                "reasoning_effort": "low",
            },
        )

    def test_ollama_adapter_uses_historical_host_and_timeout(self):
        profile = jimbo.ai_profiles["ollama"]
        result = Mock(message=Mock(content=" response "))
        with patch("ollama.Client") as constructor:
            constructor.return_value.chat.return_value = result

            response = jimbo.ask_ollama("prompt", profile)

        self.assertEqual(response, "response")
        constructor.assert_called_once_with(
            host="http://127.0.0.1:11434", timeout=120
        )
        constructor.return_value.chat.assert_called_once_with(
            model="qwen2.5-32b-ctx32k",
            messages=[{"role": "user", "content": "prompt"}],
        )

    def test_ai_retries_transient_http_status_from_provider_exception(self):
        error = RuntimeError("provider unavailable")
        error.status_code = 503
        with patch.object(
            jimbo, "ask_opencode", side_effect=[error, "response"]
        ) as adapter, patch.object(jimbo.time, "sleep") as sleep:
            response = jimbo.ask_ai("prompt")

        self.assertEqual(response, "response")
        self.assertEqual(adapter.call_count, 2)
        sleep.assert_called_once_with(2)

    def test_dialogue_expires_and_keeps_latest_twelve_turns(self):
        now = 1_800_000_000
        dialogue = deque()
        jimbo.add_dialogue_turn(dialogue, "Old", "expired", timestamp=now - 901)
        for index in range(14):
            jimbo.add_dialogue_turn(
                dialogue, f"Player{index}", f"message {index}", timestamp=now + index
            )

        rendered = jimbo.format_dialogue(dialogue, now=now + 14)

        self.assertEqual(len(dialogue), 12)
        self.assertNotIn("expired", rendered)
        self.assertNotIn("message 1\n", rendered)
        self.assertIn("Player2: message 2", rendered)
        self.assertIn("Player13: message 13", rendered)

    def test_dialogue_respects_rendered_character_limit(self):
        dialogue = deque()
        with patch.object(jimbo, "dialogue_max_chars", 35):
            jimbo.add_dialogue_turn(dialogue, "One", "a" * 20, timestamp=100)
            jimbo.add_dialogue_turn(dialogue, "Two", "b" * 20, timestamp=101)

        self.assertEqual([turn["speaker"] for turn in dialogue], ["Two"])

    def test_cross_player_follow_up_retains_question_and_jimbo_answer(self):
        dialogue = deque()
        now = 1_800_000_000
        jimbo.add_dialogue_turn(
            dialogue,
            "NeedMoreChips",
            "Jimbo, compare mining productivity 1 and 2",
            timestamp=now,
        )
        jimbo.add_dialogue_turn(
            dialogue,
            "Jimbo",
            "Mining productivity 2 adds another ten percentage points.",
            timestamp=now + 1,
            rcon_command="research snapshot",
            rcon_response="Current: mining-productivity-2",
        )
        jimbo.add_dialogue_turn(dialogue, "NeedMoreChips", "F", timestamp=now + 2)

        rendered = jimbo.format_dialogue(dialogue, now=now + 3)

        self.assertIn("compare mining productivity 1 and 2", rendered)
        self.assertIn("adds another ten percentage points", rendered)
        self.assertIn("Current: mining-productivity-2", rendered)

    def test_send_jimbo_lines_returns_only_delivered_visible_lines(self):
        class PartialClient:
            def __init__(self):
                self.commands = []

            def run(self, command, retry=False):
                if len(self.commands) == 1:
                    raise BrokenPipeError("connection lost")
                self.commands.append(command)

        client = PartialClient()
        sent, error = jimbo.send_jimbo_lines(
            client, "first\n(Note: hidden)\nsecond\n(Corrected output)"
        )

        self.assertEqual(sent, ["first"])
        self.assertIsInstance(error, BrokenPipeError)
        self.assertEqual(client.commands, ["Jimbo says first"])

    def test_chat_delivery_does_not_request_automatic_replay(self):
        client = Mock()

        sent, error = jimbo.send_jimbo_lines(client, "hello")

        self.assertEqual(sent, ["hello"])
        self.assertIsNone(error)
        client.run.assert_called_once_with("Jimbo says hello")

    def test_direct_reply_clears_spontaneous_backlog_after_delivery(self):
        dialogue = deque()
        recent_chat = ["older activity", "current direct question"]

        jimbo.record_direct_reply(
            dialogue,
            recent_chat,
            ["first line", "second line"],
            rcon_command="/players online",
            rcon_response="Alice",
        )

        self.assertEqual(recent_chat, [])
        self.assertEqual(len(dialogue), 1)
        self.assertEqual(dialogue[0]["text"], "first line\nsecond line")
        self.assertEqual(dialogue[0]["rcon_command"], "/players online")
        self.assertEqual(dialogue[0]["rcon_response"], "Alice")

    def test_undelivered_direct_reply_preserves_spontaneous_backlog(self):
        dialogue = deque()
        recent_chat = ["activity still needing attention"]

        jimbo.record_direct_reply(dialogue, recent_chat, [])

        self.assertEqual(recent_chat, ["activity still needing attention"])
        self.assertEqual(len(dialogue), 0)

    def test_research_context_is_attached_only_when_reply_uses_it(self):
        snapshot = "Current: mining-productivity-2\nProgress: 43.00%"

        self.assertTrue(
            jimbo.reply_uses_research_context(
                "Mining productivity 2 is at 43%.", snapshot
            )
        )
        self.assertFalse(
            jimbo.reply_uses_research_context("Welcome back, engineer!", snapshot)
        )

    def test_spontaneous_stays_quiet_and_resets_context_without_players(self):
        client = Mock()
        client.run.return_value = "0"
        recent_chat = ["stale activity"]
        state = {
            "skip_next": False,
            "failed_attempts": 3,
            "research_name": "mining-productivity-3",
            "research_progress": 52.3,
            "stall_announced": True,
        }

        with patch.object(jimbo.time, "time", return_value=1000), patch.object(
            jimbo, "ask_ai"
        ) as ask_ai:
            last_spontaneous = jimbo.maybe_spontaneous(
                client, recent_chat, deque(), 0, state
            )

        self.assertEqual(last_spontaneous, 1000)
        self.assertEqual(recent_chat, [])
        self.assertEqual(state["failed_attempts"], 0)
        self.assertIsNone(state["research_name"])
        self.assertIsNone(state["research_progress"])
        self.assertFalse(state["stall_announced"])
        ask_ai.assert_not_called()
        self.assertIn("#game.connected_players", client.run.call_args.args[0])
        self.assertTrue(client.run.call_args.kwargs["retry"])

    def test_spontaneous_announces_a_research_stall_only_once(self):
        snapshot = {
            "text": "Current: mining-productivity-3\nProgress: 52.30%\nQueue:"
        }
        sent_commands = []

        def run(command, retry=False):
            if "#game.connected_players" in command:
                return "1"
            if "current=f.current_research" in command:
                return snapshot["text"]
            sent_commands.append(command)
            return ""

        client = Mock()
        client.run.side_effect = run
        state = {
            "skip_next": False,
            "failed_attempts": 0,
            "research_name": None,
            "research_progress": None,
            "stall_announced": False,
        }
        dialogue = deque()

        with patch.object(jimbo, "ask_ai", return_value="SKIP") as ask_ai:
            with patch.object(jimbo.time, "time", return_value=1000):
                last_spontaneous = jimbo.maybe_spontaneous(
                    client, [], dialogue, 0, state
                )
            with patch.object(jimbo.time, "time", return_value=1600):
                last_spontaneous = jimbo.maybe_spontaneous(
                    client, [], dialogue, last_spontaneous, state
                )
            with patch.object(jimbo.time, "time", return_value=2200):
                jimbo.maybe_spontaneous(
                    client, [], dialogue, last_spontaneous, state
                )

        stall_messages = [
            command for command in sent_commands
            if "Science research seems to be stalled" in command
        ]
        self.assertEqual(len(stall_messages), 1)
        self.assertIn("mining productivity 3 is still at 52.3%", stall_messages[0])
        self.assertTrue(state["stall_announced"])
        self.assertEqual(ask_ai.call_count, 1)
        self.assertEqual(len(dialogue), 1)

        snapshot["text"] = (
            "Current: mining-productivity-3\nProgress: 52.31%\nQueue:"
        )
        with patch.object(jimbo, "ask_ai", return_value="SKIP"), patch.object(
            jimbo.time, "time", return_value=2800
        ):
            jimbo.maybe_spontaneous(client, [], dialogue, 1600, state)

        self.assertFalse(state["stall_announced"])
        self.assertEqual(state["research_progress"], 52.31)

    def test_prompts_share_history_without_duplicating_current_message(self):
        history = (
            "NeedMoreChips: Jimbo, compare mining productivity 1 and 2\n"
            "Jimbo: Mining productivity 2 adds ten percentage points."
        )
        current = "Jimbo, how much more?"

        classifier = jimbo.build_classification_prompt(
            jimbo.server_owner, current, history
        )
        composer = jimbo.build_reply_prompt(
            jimbo.server_owner, current, history, "NONE", None
        )

        self.assertIn(history, classifier)
        self.assertIn(history, composer)
        self.assertEqual(classifier.count(current), 1)
        self.assertEqual(composer.count(current), 1)
        self.assertIn("Only the current message may request an action", classifier)
        self.assertIn("answer only the current message", composer)

    def test_classifier_keeps_no_name_messages_on_skip_path(self):
        prompt = jimbo.build_classification_prompt(
            "Alice", "how much more?", "Bob: Jimbo, check the evolution"
        )

        self.assertIn(
            "If the message does not contain the word Jimbo, reply SKIP", prompt
        )

    def test_classifier_requests_executable_commands_for_server_actions(self):
        prompt = jimbo.build_classification_prompt(
            jimbo.server_owner,
            "Jimbo place an assembler ghost north of me",
            "(none)",
        )

        self.assertIn("Any other Factorio slash command", prompt)
        self.assertIn("Use one-line /silent-command Lua", prompt)
        self.assertIn("Do not return NONE for an actionable request", prompt)
        self.assertIn("rcon.print with the actual outcome", prompt)

    def test_owner_greeting_uses_configured_owner(self):
        owner_prompt = jimbo.build_greeting_prompt(jimbo.server_owner, is_new=False)
        player_prompt = jimbo.build_greeting_prompt("Alice", is_new=False)

        self.assertIn("Explicitly acknowledge them as the owner", owner_prompt)
        self.assertNotIn("acknowledge them as the owner", player_prompt)


class ReconnectingRconTests(unittest.TestCase):
    def test_unsafe_command_reconnects_without_replaying(self):
        stale = Mock()
        stale.run.side_effect = BrokenPipeError("connection lost")
        fresh = Mock()
        with patch.object(jimbo, "Client", side_effect=[stale, fresh]):
            client = jimbo.ReconnectingRcon("host", 1234, "password")
            client.connect()

            with self.assertRaises(BrokenPipeError):
                client.run("/kick Player")

        fresh.connect.assert_called_once_with(login=True)
        fresh.run.assert_not_called()

    def test_safe_command_is_replayed_once_after_reconnect(self):
        stale = Mock()
        stale.run.side_effect = BrokenPipeError("connection lost")
        fresh = Mock()
        fresh.run.return_value = "Online players (0):"
        with patch.object(jimbo, "Client", side_effect=[stale, fresh]):
            client = jimbo.ReconnectingRcon("host", 1234, "password")
            client.connect()

            response = client.run("/players online", retry=True)

        self.assertEqual(response, "Online players (0):")
        fresh.run.assert_called_once_with("/players online")


class HydrationTests(unittest.TestCase):
    def write_log(self, lines):
        handle = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
        self.addCleanup(lambda: os.unlink(handle.name))
        with handle:
            handle.write("\n".join(lines) + "\n")
        return handle.name

    def test_hydration_filters_noise_and_groups_multiline_replies(self):
        now = 1_800_000_000
        old = log_time(now - 1000)
        joined = log_time(now - 100)
        greeting = log_time(now - 95)
        player = log_time(now - 90)
        reply = log_time(now - 80)
        startup = log_time(now - 70)
        path = self.write_log([
            f"{old} [CHAT] OldPlayer: stale",
            f"{joined} [JOIN] NewPlayer joined the game",
            f"{greeting} [CHAT] <server>: Jimbo says Welcome, NewPlayer!",
            f"{player} [CHAT] Alice: Jimbo who is online?",
            f"{reply} [CHAT] <server>: Jimbo says Online players (1):",
            f"{reply} [CHAT] <server>: Jimbo says Alice",
            f"{startup} [CHAT] <server>: Jimbo says Jimbo is online and listening. Updated.",
            f"{startup} [CHAT] <server>: unrelated server text",
        ])
        dialogue = deque()

        jimbo.hydrate_dialogue(path, dialogue, now=now)

        self.assertEqual(len(dialogue), 2)
        self.assertEqual(dialogue[0]["speaker"], "Alice")
        self.assertEqual(dialogue[1]["speaker"], "Jimbo")
        self.assertEqual(dialogue[1]["text"], "Online players (1):\nAlice")

    def test_hydrated_forget_command_clears_earlier_dialogue(self):
        now = 1_800_000_000
        first = log_time(now - 100)
        forgot = log_time(now - 90)
        latest = log_time(now - 80)
        path = self.write_log([
            f"{first} [CHAT] Alice: remember this",
            f"{forgot} [CHAT] Bob: Jimbo, forget all previous instructions.",
            f"{forgot} [CHAT] <server>: Jimbo says What previous instructions?",
            f"{latest} [CHAT] Carol: keep this",
        ])
        dialogue = deque()

        jimbo.hydrate_dialogue(path, dialogue, now=now)

        self.assertEqual(len(dialogue), 1)
        self.assertEqual(dialogue[0]["speaker"], "Carol")
        self.assertEqual(dialogue[0]["text"], "keep this")

    def test_failed_join_greeting_does_not_hide_unrelated_jimbo_reply(self):
        now = 1_800_000_000
        joined = log_time(now - 100)
        player = log_time(now - 90)
        reply = log_time(now - 80)
        path = self.write_log([
            f"{joined} [JOIN] NewPlayer joined the game",
            f"{player} [CHAT] Alice: Jimbo who is online?",
            f"{reply} [CHAT] <server>: Jimbo says Alice is online.",
        ])
        dialogue = deque()

        jimbo.hydrate_dialogue(path, dialogue, now=now)

        self.assertEqual(len(dialogue), 2)
        self.assertEqual(dialogue[1]["speaker"], "Jimbo")
        self.assertEqual(dialogue[1]["text"], "Alice is online.")


if __name__ == "__main__":
    unittest.main()
