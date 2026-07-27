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
