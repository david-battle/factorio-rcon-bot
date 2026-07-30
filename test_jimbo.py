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

    def test_opencode_uses_and_cleans_private_temp_directory(self):
        temp_paths = []

        def fake_run(*args, **kwargs):
            temp_path = kwargs["env"]["TMPDIR"]
            temp_paths.append(temp_path)
            self.assertTrue(os.path.isdir(temp_path))
            with open(os.path.join(temp_path, "native-library.so"), "wb") as artifact:
                artifact.write(b"temporary")
            return Mock(
                returncode=0,
                stdout='{"type":"text","part":{"text":" response "}}\n',
                stderr="",
            )

        with patch.object(jimbo.subprocess, "run", side_effect=fake_run) as run:
            response = jimbo.ask_opencode(
                "prompt", jimbo.ai_profiles["openai"]
            )

        self.assertEqual(response, "response")
        self.assertEqual(len(temp_paths), 1)
        self.assertFalse(os.path.exists(temp_paths[0]))
        call = run.call_args
        self.assertEqual(call.kwargs["cwd"], "/tmp/opencode")
        self.assertEqual(call.kwargs["timeout"], 120)
        self.assertEqual(
            call.kwargs["env"]["OPENCODE_DISABLE_PROJECT_CONFIG"], "1"
        )

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
        active_adapter_name = jimbo.ai_profile["provider"]
        adapter_names = {
            "opencode": "ask_opencode",
            "openai-compatible": "ask_openai_compatible",
            "ollama": "ask_ollama",
        }
        adapter_func = adapter_names[active_adapter_name]
        with patch.object(
            jimbo, adapter_func, side_effect=[error, "response"]
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

    def test_request_failure_is_sent_and_recorded(self):
        client = Mock()
        dialogue = deque()
        recent_chat = ["dlbattle: Jimbo check Fulgora logistics"]

        sent, error = jimbo.report_request_failure(client, dialogue, recent_chat)

        self.assertEqual(sent, ["I tried, but I couldn't complete that request."])
        self.assertIsNone(error)
        client.run.assert_called_once_with(
            "Jimbo says I tried, but I couldn't complete that request."
        )
        self.assertEqual(dialogue[-1]["text"], sent[0])
        self.assertEqual(recent_chat, [])

    def test_undelivered_request_failure_preserves_context(self):
        client = Mock()
        client.run.side_effect = BrokenPipeError("still disconnected")
        dialogue = deque()
        recent_chat = ["dlbattle: Jimbo check Fulgora logistics"]

        sent, error = jimbo.report_request_failure(client, dialogue, recent_chat)

        self.assertEqual(sent, [])
        self.assertIsInstance(error, BrokenPipeError)
        self.assertEqual(len(dialogue), 0)
        self.assertEqual(recent_chat, ["dlbattle: Jimbo check Fulgora logistics"])

    def test_logistics_decision_parses_and_validates_names(self):
        self.assertEqual(
            jimbo.parse_logistics_decision(
                "LOGISTICS|fulgora|holmium-plate,superconductor,supercapacitor"
            ),
            (
                "fulgora",
                ["holmium-plate", "superconductor", "supercapacitor"],
            ),
        )
        self.assertIsNone(
            jimbo.parse_logistics_decision("LOGISTICS|Fulgora|holmium-plate")
        )
        self.assertIsNone(
            jimbo.parse_logistics_decision(
                'LOGISTICS|fulgora|holmium-plate\"] ; game.reset_time_played()'
            )
        )

    def test_tag_decision_parses_and_validates(self):
        self.assertEqual(
            jimbo.parse_tag_decision("TAG|nauvis|artillery-turret"),
            ("nauvis", "artillery-turret", ""),
        )
        self.assertEqual(
            jimbo.parse_tag_decision("TAG|nauvis|artillery-turret|My Guns"),
            ("nauvis", "artillery-turret", "My Guns"),
        )
        self.assertEqual(
            jimbo.parse_tag_decision("TAG|fulgora|electric-pole|"),
            ("fulgora", "electric-pole", ""),
        )
        self.assertIsNone(jimbo.parse_tag_decision("TAG|Nauvis|artillery-turret"))
        self.assertIsNone(jimbo.parse_tag_decision("TAG|nauvis|ArtilleryTurret"))
        self.assertIsNone(jimbo.parse_tag_decision("MARK|nauvis|artillery-turret"))
        self.assertIsNone(
            jimbo.parse_tag_decision(
                'TAG|nauvis|artillery-turret\"] ; game.reset_time_played()'
            )
        )

    def test_tag_command_builds_correct_lua(self):
        client = Mock()
        client.run.return_value = "Tagged 12 artillery-turret on nauvis"
        result = jimbo.run_tag_command(client, "nauvis", "artillery-turret", "")
        command = client.run.call_args.args[0]
        self.assertIn('game.surfaces["nauvis"]', command)
        self.assertIn("add_chart_tag", command)
        self.assertIn("name=et", command)
        self.assertIn("type=et", command)
        self.assertIn("icon={type='entity',name=et}", command)
        self.assertTrue(client.run.call_args.kwargs["retry"])
        self.assertIn("Tagged", result)

    def test_tag_command_with_label(self):
        client = Mock()
        client.run.return_value = "Tagged 5 electric-pole on nauvis"
        result = jimbo.run_tag_command(client, "nauvis", "electric-pole", "Pole")
        command = client.run.call_args.args[0]
        self.assertIn('label_text="Pole"', command)
        self.assertIn("Tagged", result)

    def test_tag_command_reports_surface_not_found(self):
        client = Mock()
        client.run.return_value = "Surface not found"
        result = jimbo.run_tag_command(client, "invalid", "artillery-turret", "")
        self.assertIn("Surface not found", result)

    def test_tag_command_reports_no_entities_found(self):
        client = Mock()
        client.run.return_value = "No artillery-turret found on nauvis"
        result = jimbo.run_tag_command(client, "nauvis", "artillery-turret", "")
        self.assertIn("No artillery-turret found", result)

    def test_top_damage_decision_parses_and_validates(self):
        self.assertEqual(
            jimbo.parse_top_damage_decision("TOP_DAMAGE|nauvis|artillery-turret"),
            ("nauvis", "artillery-turret"),
        )
        self.assertEqual(
            jimbo.parse_top_damage_decision("TOP_DAMAGE|nauvis|any"),
            ("nauvis", "any"),
        )
        self.assertIsNone(jimbo.parse_top_damage_decision("TOP_DAMAGE|Nauvis|artillery-turret"))

    def test_top_damage_command_builds_correct_lua(self):
        client = Mock()
        client.run.return_value = "Tagged artillery-turret unit 12 at 0,0 with 100 damage"
        result = jimbo.run_top_damage_command(client, "nauvis", "artillery-turret")
        command = client.run.call_args.args[0]
        self.assertIn('game.surfaces["nauvis"]', command)
        self.assertIn("add_chart_tag", command)
        self.assertIn("damage_dealt", command)
        self.assertTrue(client.run.call_args.kwargs["retry"])
        self.assertIn("Tagged", result)

    def test_logistic_availability_deduplicates_and_marks_silo_networks(self):
        client = Mock()
        client.run.return_value = (
            "Surface fulgora, network 526 (rocket silo: yes): "
            "holmium-plate available=0, "
            "superconductor available=2527, supercapacitor available=284"
        )

        response = jimbo.get_logistic_availability(
            client,
            "fulgora",
            ["holmium-plate", "superconductor", "supercapacitor"],
        )

        command = client.run.call_args.args[0]
        self.assertIn('local scope="fulgora"', command)
        self.assertIn("game.surfaces[scope]", command)
        self.assertIn("n.network_id", command)
        self.assertIn('type="rocket-silo"', command)
        self.assertIn("n.get_contents()", command)
        self.assertIn("math.max(0,item.count)", command)
        self.assertTrue(client.run.call_args.kwargs["retry"])
        self.assertIn("superconductor available=2527", response)

    def test_logistic_availability_can_scan_all_planets(self):
        client = Mock()
        client.run.return_value = (
            "Surface nauvis, network 2: superconductor available=0\n"
            "Surface fulgora, network 526: superconductor available=2527"
        )

        response = jimbo.get_logistic_availability(
            client, "all", ["superconductor"]
        )

        command = client.run.call_args.args[0]
        self.assertIn('local scope="all"', command)
        self.assertIn("if candidate.planet", command)
        self.assertIn("Surface %s, network %s", command)
        self.assertIn("Surface fulgora", response)

    def test_logistic_reply_distinguishes_availability_from_shortfall(self):
        prompt = jimbo.build_reply_prompt(
            jimbo.server_owner,
            "Jimbo where can I get the rest?",
            "Jimbo: Mech Armor requires 200 holmium plates.",
            "RCON: logistic availability",
            "Network 526: holmium-plate available=0",
        )

        self.assertIn("available stock, never a recipe shortfall", prompt)
        self.assertIn("the full required quantity is still needed", prompt)

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

    def test_research_snapshot_requests_actual_levels(self):
        client = Mock()
        client.run.return_value = (
            "Current: scrap recycling productivity 3\n"
            "Progress: 87.37%\n"
            "Queue:\n"
            "1: mining productivity 7"
        )

        snapshot = jimbo.get_research_snapshot(client)

        command = client.run.call_args.args[0]
        self.assertIn("t.level", command)
        self.assertIn("t.prototype.max_level>1", command)
        self.assertIn("(base or t.name)", command)
        self.assertIn("display(current)", command)
        self.assertIn("gsub", command)
        self.assertIn("Current: scrap recycling productivity 3", snapshot)
        self.assertNotIn("(level 3)", snapshot)
        self.assertTrue(client.run.call_args.kwargs["retry"])

    def test_research_level_change_is_not_treated_as_a_stall(self):
        state = {"research_name": None, "research_progress": None}

        first = jimbo.update_research_stall_state(
            "Current: mining productivity 7\nProgress: 0.00%",
            state,
        )
        second = jimbo.update_research_stall_state(
            "Current: mining productivity 8\nProgress: 0.00%",
            state,
        )

        self.assertEqual(first[0], "changed")
        self.assertEqual(second[0], "changed")
        self.assertEqual(state["research_name"], "mining productivity 8")

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

        with patch.object(jimbo.time, "time", return_value=2000), patch.object(
            jimbo, "ask_ai"
        ) as ask_ai:
            last_spontaneous = jimbo.maybe_spontaneous(
                client, recent_chat, deque(), 0, state
            )

        self.assertEqual(last_spontaneous, 2000)
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
            with patch.object(jimbo.time, "time", return_value=1300):
                last_spontaneous = jimbo.maybe_spontaneous(
                    client, [], dialogue, 0, state
                )
            with patch.object(jimbo.time, "time", return_value=2600):
                last_spontaneous = jimbo.maybe_spontaneous(
                    client, [], dialogue, last_spontaneous, state
                )
            with patch.object(jimbo.time, "time", return_value=3900):
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
        self.assertIn("mining productivity 8", composer)
        self.assertIn("next level is mining productivity 9", composer)
        self.assertIn("scrap recycling productivity 3", composer)

    def test_classifier_keeps_no_name_messages_on_skip_path(self):
        prompt = jimbo.build_classification_prompt(
            "Alice", "how much more?", "Bob: Jimbo, check the evolution"
        )

        self.assertIn(
            "If the message does not contain the word Jimbo, reply SKIP", prompt
        )
        self.assertIn(
            "If the current message contains the word Jimbo, never reply SKIP",
            prompt,
        )

    def test_direct_jimbo_address_uses_word_boundary(self):
        self.assertTrue(
            jimbo.directly_addresses_jimbo(
                "Jimbo, please place a production cell."
            )
        )
        self.assertTrue(jimbo.directly_addresses_jimbo("hey JIMBO!"))
        self.assertFalse(jimbo.directly_addresses_jimbo("player-to-player chat"))
        self.assertFalse(jimbo.directly_addresses_jimbo("notjimbo"))

    def test_direct_jimbo_skip_retries_classification_once(self):
        with patch.object(
            jimbo,
            "ask_ai",
            side_effect=[
                "SKIP",
                "PRODUCE|current|iron-gear-wheel|standing:north",
            ],
        ) as ask_ai:
            result = jimbo.classify_current_message(
                "dlbattle",
                (
                    "Jimbo please place a production cell for iron gear wheels "
                    "north of my current location."
                ),
                "(none)",
            )

        self.assertEqual(
            result,
            "PRODUCE|current|iron-gear-wheel|standing:north",
        )
        self.assertEqual(ask_ai.call_count, 2)
        self.assertIn(
            "previous answer was SKIP",
            ask_ai.call_args_list[1].args[0],
        )
        self.assertIn(
            "must be classified as NONE",
            ask_ai.call_args_list[1].args[0],
        )

    def test_unaddressed_skip_is_not_retried(self):
        with patch.object(jimbo, "ask_ai", return_value="SKIP") as ask_ai:
            result = jimbo.classify_current_message(
                "Alice", "nice factory", "(none)"
            )

        self.assertEqual(result, "SKIP")
        ask_ai.assert_called_once()

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

    def test_classifier_uses_factorio_2_recipe_api(self):
        prompt = jimbo.build_classification_prompt(
            jimbo.server_owner,
            "Jimbo check the recipe for mech armor",
            "(none)",
        )

        self.assertIn('prototypes.recipe["internal-name"].ingredients', prompt)
        self.assertIn("does not have game.recipe_prototypes", prompt)

    def test_planet_list_does_not_imply_material_sources(self):
        classifier = jimbo.build_classification_prompt(
            jimbo.server_owner,
            "Jimbo where can I get holmium plates?",
            "(none)",
        )
        reply = jimbo.build_reply_prompt(
            jimbo.server_owner,
            "Jimbo where can I get those materials?",
            "Jimbo: You need holmium plates and superconductors.",
            "RCON: list planets",
            "Nauvis\nVulcanus\nFulgora\nGleba",
        )

        self.assertIn("a planet list does not establish material sources", classifier)
        self.assertIn("does not establish where an item comes from", reply)
        self.assertIn("Never claim that every listed planet supplies", reply)

    def test_classifier_requests_structured_logistic_inventory(self):
        prompt = jimbo.build_classification_prompt(
            jimbo.server_owner,
            "Jimbo are those materials in the silo logistic network on Fulgora?",
            "Jimbo: We need holmium plates and superconductors.",
        )

        self.assertIn("LOGISTICS|surface|item-name,item-name", prompt)
        self.assertIn(
            "LOGISTICS|fulgora|holmium-plate,superconductor,supercapacitor",
            prompt,
        )
        self.assertIn("resolve references such as 'those materials'", prompt)
        self.assertIn("available, on hand, or in stock", prompt)
        self.assertIn("even when the player does not explicitly say", prompt)
        self.assertIn("Use surface 'all' when asked about", prompt)
        self.assertIn("the whole solar system", prompt)
        self.assertIn("Never literally reply 'A Factorio slash command'", prompt)

    def test_classifier_requests_structured_production_cells(self):
        prompt = jimbo.build_classification_prompt(
            jimbo.server_owner,
            "Jimbo make electronic circuits at [gps=-622,51,nauvis]",
            "(none)",
        )

        self.assertIn(
            "PRODUCE|surface|item-name|optional-location", prompt
        )
        self.assertIn(
            "PRODUCE|nauvis|electronic-circuit|[gps=-622,51,nauvis]",
            prompt,
        )
        self.assertIn("Copy an explicit player-supplied GPS", prompt)
        self.assertIn("never invent or adjust coordinates", prompt)
        self.assertIn("normalized direction", prompt)
        self.assertIn("north-east", prompt)
        self.assertIn("empty fourth field", prompt)
        self.assertIn("'view' for 'here'", prompt)
        self.assertIn("'standing' only for the player's physical", prompt)
        self.assertIn("'standing:north'", prompt)
        self.assertIn("'view:north'", prompt)
        self.assertIn("'north of my current location'", prompt)
        self.assertIn("direction without an explicit origin", prompt)
        self.assertIn("surface 'current'", prompt)

    def test_production_reply_requires_grounded_success_or_failure(self):
        success_prompt = jimbo.build_reply_prompt(
            jimbo.server_owner,
            "Jimbo make electronic circuits here",
            "(none)",
            "RCON: production cell",
            (
                "SUCCESS: [gps=-622,51,nauvis] 3x3 electronic-circuit cell "
                "placed with assembling-machine-3, requester-chest, 2 inserters, "
                "passive-provider-chest, medium-electric-pole"
            ),
        )
        failure_prompt = jimbo.build_reply_prompt(
            jimbo.server_owner,
            "Jimbo make electronic circuits here",
            "(none)",
            "RCON: production cell",
            "ERROR: No logistic network coverage",
        )

        for prompt in (success_prompt, failure_prompt):
            self.assertIn("verified result of a production-cell", prompt)
            self.assertIn("report the anchor map ping", prompt)
            self.assertIn("every created entity named", prompt)
            self.assertIn("If SUCCESS includes a WARNING", prompt)
            self.assertIn("cell was placed but repeat every", prompt)
            self.assertIn("clearly say the cell was not placed", prompt)
            self.assertIn("Never claim that placement succeeded", prompt)

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


class ProduceCellTests(unittest.TestCase):
    def test_parse_produce_decision_valid(self):
        result = jimbo.parse_produce_decision(
            "PRODUCE|nauvis|processing-unit|"
        )
        self.assertEqual(result, ("nauvis", "processing-unit", ""))

    def test_parse_produce_decision_with_gps(self):
        result = jimbo.parse_produce_decision(
            "PRODUCE|fulgora|holmium-plate|[gps=10,20,fulgora]"
        )
        self.assertEqual(
            result, ("fulgora", "holmium-plate", "[gps=10,20,fulgora]")
        )

    def test_parse_produce_decision_with_normalized_direction(self):
        for direction in jimbo.production_cell_directions:
            with self.subTest(direction=direction):
                self.assertEqual(
                    jimbo.parse_produce_decision(
                        f"PRODUCE|nauvis|iron-plate|{direction}"
                    ),
                    ("nauvis", "iron-plate", direction),
                )

    def test_parse_produce_decision_distinguishes_view_and_standing(self):
        self.assertEqual(
            jimbo.parse_produce_decision(
                "PRODUCE|current|iron-plate|view"
            ),
            ("current", "iron-plate", "view"),
        )
        self.assertEqual(
            jimbo.parse_produce_decision(
                "PRODUCE|current|iron-plate|standing"
            ),
            ("current", "iron-plate", "standing"),
        )

    def test_parse_produce_decision_preserves_direction_origin(self):
        for origin in jimbo.production_cell_relative_locations:
            for direction in jimbo.production_cell_directions:
                hint = f"{origin}:{direction}"
                with self.subTest(hint=hint):
                    self.assertEqual(
                        jimbo.parse_produce_decision(
                            f"PRODUCE|current|iron-plate|{hint}"
                        ),
                        ("current", "iron-plate", hint),
                    )

    def test_parse_produce_decision_rejects_unstructured_location(self):
        for hint in (
            "somewhere-over-there",
            "standing:",
            "standing:up",
            "spawn:north",
            "view:north:west",
        ):
            with self.subTest(hint=hint):
                self.assertIsNone(
                    jimbo.parse_produce_decision(
                        f"PRODUCE|nauvis|iron-plate|{hint}"
                    )
                )

    def test_relative_hint_keeps_bare_directions_view_relative(self):
        self.assertEqual(
            jimbo.parse_production_cell_relative_hint("north"),
            ("view", "north"),
        )
        self.assertEqual(
            jimbo.parse_production_cell_relative_hint("standing:north"),
            ("standing", "north"),
        )
        self.assertIsNone(
            jimbo.parse_production_cell_relative_hint("standing:up")
        )

    def test_parse_produce_decision_invalid_prefix(self):
        self.assertIsNone(jimbo.parse_produce_decision("MAKE|nauvis|iron-plate"))

    def test_parse_produce_decision_invalid_item(self):
        self.assertIsNone(jimbo.parse_produce_decision("PRODUCE|nauvis|Iron Plate|"))

    def test_parse_produce_decision_invalid_surface(self):
        self.assertIsNone(jimbo.parse_produce_decision("PRODUCE|Nauvis|iron-plate|"))

    def test_dispatch_production_cell_passes_only_placement_fields_and_player(self):
        client = Mock()
        request = jimbo.parse_produce_decision(
            "PRODUCE|nauvis|electronic-circuit|[gps=-622,51,nauvis]"
        )
        with patch.object(
            jimbo, "place_production_cell", return_value="SUCCESS: placed"
        ) as place:
            result = jimbo.dispatch_production_cell(client, request, "Alice")

        self.assertEqual(result, "SUCCESS: placed")
        place.assert_called_once_with(
            client,
            "nauvis",
            "electronic-circuit",
            "[gps=-622,51,nauvis]",
            requesting_player="Alice",
        )

    def test_place_cell_full_success(self):
        client = Mock()
        client.run.side_effect = [
            "ANCHOR:10,20,3,3,assembling-machine-3",
            "SUCCESS: [gps=10,20,nauvis] 3x3 processing-unit cell placed",
        ]

        result = jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]", "dlbattle"
        )

        phase1 = client.run.call_args_list[0].args[0]
        self.assertIn("nauvis", phase1)
        self.assertIn("processing-unit", phase1)
        self.assertIn("ax=10", phase1)
        self.assertIn("ay=20", phase1)
        self.assertIn("SUCCESS", result)
        self.assertIn("[gps=10,20,nauvis]", result)

    def test_place_cell_looks_up_entity_dimensions(self):
        client = Mock()
        client.run.side_effect = [
            "ANCHOR:10,20,5,5,em-plasity-building",
            "SUCCESS: [gps=10,20,nauvis] 5x5 processing-unit cell placed",
        ]

        result = jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]", "dlbattle"
        )

        phase1 = client.run.call_args_list[0].args[0]
        self.assertIn("e.tile_width", phase1)
        self.assertIn("e.tile_height", phase1)
        self.assertIn("SUCCESS", result)

    def test_place_cell_reports_surface_error(self):
        client = Mock()
        client.run.return_value = "ERROR: Surface not found"

        result = jimbo.place_production_cell(
            client, "nonexistent", "iron-plate", "[gps=0,0,nonexistent]", "dlbattle"
        )

        self.assertIn("ERROR", result)
        self.assertIn("Surface not found", result)

    def test_place_cell_reports_entity_blocked(self):
        client = Mock()
        client.run.return_value = "ERROR: 3 entities in area"

        result = jimbo.place_production_cell(
            client, "nauvis", "iron-plate", "[gps=100,100,nauvis]", "dlbattle"
        )

        self.assertIn("ERROR", result)
        self.assertIn("entities in area", result.lower())

    def test_place_cell_reports_no_power(self):
        client = Mock()
        client.run.return_value = "ERROR: No power coverage at location"

        result = jimbo.place_production_cell(
            client, "nauvis", "iron-plate", "[gps=200,200,nauvis]", "dlbattle"
        )

        self.assertIn("ERROR", result)
        self.assertIn("power", result.lower())

    def test_place_cell_reports_no_logistics(self):
        client = Mock()
        client.run.return_value = "ERROR: No logistic network coverage"

        result = jimbo.place_production_cell(
            client, "nauvis", "iron-plate", "[gps=300,300,nauvis]", "dlbattle"
        )

        self.assertIn("ERROR", result)
        self.assertIn("logistic", result.lower())

    def test_place_cell_handles_empty_hint(self):
        client = Mock()
        client.run.return_value = (
            "ERROR: No suitable production-cell location within 128 tiles "
            "(last: No logistic network coverage)"
        )
        result = jimbo.place_production_cell(
            client, "nauvis", "iron-plate", "", "dlbattle"
        )

        phase1 = client.run.call_args.args[0]
        self.assertIn("request_player.position", phase1)
        self.assertIn("game.forces.player.get_spawn_position(s)", phase1)
        self.assertIn("No suitable production-cell location within", result)
        client.run.assert_called_once()
        self.assertTrue(client.run.call_args.kwargs["retry"])

    def test_place_cell_uses_bounded_footprint_aware_location_search(self):
        client = Mock()
        client.run.return_value = (
            "ERROR: No suitable production-cell location within 128 tiles"
        )

        jimbo.place_production_cell(
            client, "nauvis", "iron-plate", "", "dlbattle"
        )

        phase1 = client.run.call_args.args[0]
        self.assertEqual(jimbo.production_cell_search_max_radius, 128)
        self.assertEqual(jimbo.production_cell_search_max_candidates, 256)
        self.assertIn("local max_search_radius=128", phase1)
        self.assertIn("local max_search_candidates=256", phase1)
        self.assertIn("local step_x=w+4;local step_y=h+1", phase1)
        self.assertIn("for ring=0,max_ring", phase1)
        self.assertIn("#anchors>=max_search_candidates", phase1)
        self.assertIn("math.max(math.abs(dx),math.abs(dy))<=max_search_radius", phase1)

    def test_place_cell_prefers_full_support_then_uses_structural_fallback(self):
        client = Mock()
        client.run.return_value = "ERROR: captured"

        jimbo.place_production_cell(
            client, "aquilo", "iron-gear-wheel", "standing:north", "dlbattle"
        )

        phase1 = client.run.call_args.args[0]
        self.assertIn("local fallback_result=nil", phase1)
        self.assertIn("local function anchor_result", phase1)
        self.assertIn(
            "if compact_heated and compact_net and compact_construction "
            "and compact_power then",
            phase1,
        )
        self.assertIn("'aquilo-compact','strict'", phase1)
        self.assertIn("'aquilo-compact','fallback'", phase1)
        self.assertIn(
            "if heated and net and construction and supplies and connected then",
            phase1,
        )
        self.assertIn("'standard','strict'", phase1)
        self.assertIn("'standard','fallback'", phase1)
        self.assertIn("if fallback_result then rcon.print(fallback_result)", phase1)
        self.assertIn("local trace={anchors=0,structural=0", phase1)
        self.assertIn("local function trace_text", phase1)
        self.assertIn("trace.anchors=trace.anchors+1", phase1)
        self.assertIn("trace.occupied=trace.occupied+1", phase1)
        self.assertIn("trace.unplaceable=trace.unplaceable+1", phase1)
        self.assertIn("trace.heat=trace.heat+1", phase1)
        self.assertIn("trace.logistics=trace.logistics+1", phase1)
        self.assertIn("trace.construction=trace.construction+1", phase1)
        self.assertIn("trace.power=trace.power+1", phase1)
        self.assertIn("'|TRACE:'..trace_text", phase1)

    def test_place_cell_logs_trace_without_exposing_it_to_reply(self):
        client = Mock()
        client.run.side_effect = [
            (
                "ANCHOR:-34,-5,3,3,assembling-machine-3,,aquilo,"
                "aquilo-compact,fallback|TRACE:surface=aquilo "
                "origin=-29.1:0.0 direction=north machines=3 anchors=768 "
                "structural=4 occupied=500 unplaceable=264 heat=4 "
                "logistics=0 construction=0 power=1 "
                "selected=fallback:-34:-5:aquilo-compact"
            ),
            "SUCCESS: placed with warning",
        ]

        with patch("builtins.print") as output:
            result = jimbo.place_production_cell(
                client,
                "current",
                "iron-gear-wheel",
                "standing:north",
                "dlbattle",
            )

        self.assertEqual(result, "SUCCESS: placed with warning")
        output.assert_any_call(
            (
                "PRODUCE search trace: surface=aquilo origin=-29.1:0.0 "
                "direction=north machines=3 anchors=768 structural=4 "
                "occupied=500 unplaceable=264 heat=4 logistics=0 "
                "construction=0 power=1 "
                "selected=fallback:-34:-5:aquilo-compact"
            ),
            flush=True,
        )

    def test_place_cell_strips_trace_from_grounded_failure(self):
        client = Mock()
        client.run.return_value = (
            "ERROR: No structurally placeable candidate|TRACE:surface=aquilo "
            "origin=-29.1:0.0 direction=north machines=3 anchors=768 "
            "structural=0 occupied=700 unplaceable=68 heat=0 logistics=0 "
            "construction=0 power=0 selected=none:0:0:none"
        )

        with patch("builtins.print") as output:
            result = jimbo.place_production_cell(
                client,
                "current",
                "iron-gear-wheel",
                "standing:north",
                "dlbattle",
            )

        self.assertEqual(result, "ERROR: No structurally placeable candidate")
        self.assertNotIn("TRACE", result)
        self.assertTrue(
            any(
                call.args
                and call.args[0].startswith("PRODUCE search trace:")
                for call in output.call_args_list
            )
        )

    def test_place_cell_named_direction_requires_online_player_on_surface(self):
        client = Mock()
        client.run.return_value = (
            "ERROR: View-relative location requires the requesting player "
            "online on nauvis"
        )

        result = jimbo.place_production_cell(
            client, "nauvis", "iron-plate", "north-east", "dlbattle"
        )

        phase1 = client.run.call_args.args[0]
        self.assertIn('local direction="north-east"', phase1)
        self.assertIn('local relative_location="view"', phase1)
        self.assertIn("not request_player.connected", phase1)
        self.assertIn("request_player.surface~=s", phase1)
        self.assertIn("direction=='north-east'", phase1)
        self.assertIn("View-relative location requires", result)

    def test_place_cell_distinguishes_remote_view_and_physical_position(self):
        view_client = Mock()
        view_client.run.return_value = "ERROR: blocked"
        standing_client = Mock()
        standing_client.run.return_value = "ERROR: blocked"

        jimbo.place_production_cell(
            view_client, "current", "iron-plate", "view", "dlbattle"
        )
        jimbo.place_production_cell(
            standing_client, "current", "iron-plate", "standing", "dlbattle"
        )

        view_phase1 = view_client.run.call_args.args[0]
        standing_phase1 = standing_client.run.call_args.args[0]
        self.assertIn(
            "s=request_player.physical_surface else s=request_player.surface",
            view_phase1,
        )
        self.assertIn("origin=request_player.position", view_phase1)
        self.assertIn("origin=request_player.physical_position", standing_phase1)
        self.assertIn("request_player.physical_surface~=s", standing_phase1)

    def test_place_cell_direction_uses_selected_view_or_standing_origin(self):
        view_client = Mock()
        view_client.run.return_value = "ERROR: blocked"
        standing_client = Mock()
        standing_client.run.return_value = "ERROR: blocked"

        jimbo.place_production_cell(
            view_client, "current", "iron-plate", "view:north", "dlbattle"
        )
        jimbo.place_production_cell(
            standing_client, "current", "iron-plate", "standing:north", "dlbattle"
        )

        view_phase1 = view_client.run.call_args.args[0]
        standing_phase1 = standing_client.run.call_args.args[0]
        self.assertIn('local relative_location="view"', view_phase1)
        self.assertIn('local direction="north"', view_phase1)
        self.assertIn("s=request_player.surface", view_phase1)
        self.assertIn("origin=request_player.position", view_phase1)
        self.assertIn('local relative_location="standing"', standing_phase1)
        self.assertIn('local direction="north"', standing_phase1)
        self.assertIn(
            "s=request_player.physical_surface else s=request_player.surface",
            standing_phase1,
        )
        self.assertIn(
            "origin=request_player.physical_position", standing_phase1
        )

    def test_place_cell_carries_resolved_current_surface_into_mutation(self):
        client = Mock()
        client.run.side_effect = [
            "ANCHOR:10,20,3,3,assembling-machine-3,,fulgora",
            "SUCCESS: placed",
        ]

        result = jimbo.place_production_cell(
            client, "current", "iron-plate", "view", "dlbattle"
        )

        phase2 = client.run.call_args_list[1].args[0]
        self.assertIn('local s=game.surfaces["fulgora"]', phase2)
        self.assertEqual(result, "SUCCESS: placed")

    def test_place_cell_requires_requesting_player(self):
        client = Mock()

        result = jimbo.place_production_cell(
            client, "nauvis", "electronic-circuit", "[gps=10,20,nauvis]"
        )

        self.assertEqual(result, "ERROR: Requesting player is required")
        client.run.assert_not_called()

    def test_place_cell_rejects_invalid_or_mismatched_gps(self):
        client = Mock()

        invalid = jimbo.place_production_cell(
            client, "nauvis", "iron-plate", "[gps=oops,20,nauvis]", "dlbattle"
        )
        mismatched = jimbo.place_production_cell(
            client, "nauvis", "iron-plate", "[gps=10,20,fulgora]", "dlbattle"
        )

        self.assertEqual(invalid, "ERROR: Invalid GPS location hint")
        self.assertEqual(
            mismatched, "ERROR: GPS surface does not match requested surface"
        )
        client.run.assert_not_called()

    def test_place_cell_rejects_malformed_location_response(self):
        client = Mock()
        client.run.return_value = "ANCHOR:bad"

        result = jimbo.place_production_cell(
            client, "nauvis", "iron-plate", "[gps=10,20,nauvis]", "dlbattle"
        )

        self.assertEqual(result, "ERROR: Invalid location response")
        self.assertEqual(client.run.call_count, 1)

    def test_place_cell_rejects_fractional_anchor_response(self):
        client = Mock()
        client.run.return_value = "ANCHOR:10.5,20,3,3,assembling-machine-3"

        result = jimbo.place_production_cell(
            client, "nauvis", "electronic-circuit",
            "[gps=10,20,nauvis]", "dlbattle",
        )

        self.assertEqual(result, "ERROR: Invalid location response")
        self.assertEqual(client.run.call_count, 1)

    def test_place_cell_phase2_creates_all_ghosts(self):
        client = Mock()
        client.run.side_effect = [
            "ANCHOR:10,20,3,3,assembling-machine-3",
            "SUCCESS: placed",
        ]

        jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]", "dlbattle"
        )

        phase2 = client.run.call_args_list[1].args[0]
        self.assertIn("entity-ghost", phase2)
        self.assertIn("requester-chest", phase2)
        self.assertIn("passive-provider-chest", phase2)
        self.assertIn("inserter", phase2)
        self.assertIn("medium-electric-pole", phase2)
        self.assertEqual(phase2.count("direction=defines.direction.west"), 2)
        self.assertIn("direction=plans[4].direction", phase2)
        self.assertIn("direction=plans[5].direction", phase2)
        self.assertNotIn("defines.direction.right", phase2)
        self.assertNotIn("defines.direction.left", phase2)
        self.assertIn("pcall", phase2)
        self.assertIn("actual_recipe=b.get_recipe()", phase2)
        self.assertIn("cell placed with", phase2)
        self.assertNotIn("] ..w", phase2)

    def test_place_cell_phase2_requester_filters(self):
        client = Mock()
        client.run.side_effect = [
            "ANCHOR:10,20,3,3,assembling-machine-3",
            "SUCCESS: placed",
        ]

        jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]", "dlbattle"
        )

        phase2 = client.run.call_args_list[1].args[0]
        self.assertIn("get_logistic_sections", phase2)
        self.assertIn("copy_settings(b,player)", phase2)
        self.assertIn("filter.value.name==ing.name", phase2)
        self.assertIn("request filter missing for", phase2)

    def test_place_cell_phase2_rollback_on_failure(self):
        client = Mock()
        client.run.side_effect = [
            "ANCHOR:10,20,3,3,assembling-machine-3",
            "ERROR: building failed",
        ]

        result = jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]", "dlbattle"
        )

        self.assertIn("ERROR", result)
        self.assertIn("building", result)

    def test_place_cell_phase2_no_retry_on_mutation(self):
        client = Mock()
        client.run.side_effect = [
            "ANCHOR:10,20,3,3,assembling-machine-3",
            "SUCCESS: placed",
        ]

        jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]", "dlbattle"
        )

        phase2_call = client.run.call_args_list[1]
        self.assertFalse(phase2_call.kwargs.get("retry", False))

    def test_place_cell_resolves_compatible_machine_from_live_categories(self):
        client = Mock()
        client.run.side_effect = [
            "ANCHOR:10,20,3,3,assembling-machine-3",
            "SUCCESS: placed",
        ]

        jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]", "dlbattle"
        )

        phase1 = client.run.call_args_list[0].args[0]
        self.assertIn("ipairs(r.categories)", phase1)
        self.assertIn("prototypes.get_entity_filtered", phase1)
        self.assertIn("filter='crafting-category'", phase1)
        self.assertIn("crafting_category=category", phase1)
        self.assertIn("a.get_crafting_speed('normal')", phase1)
        self.assertNotIn("r.category", phase1)
        self.assertNotIn("r.products[1]", phase1)

    def test_place_cell_checks_power_supply_radius(self):
        client = Mock()
        client.run.side_effect = [
            "ANCHOR:10,20,3,3,assembling-machine-3",
            "SUCCESS: placed",
        ]

        jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]", "dlbattle"
        )

        phase1 = client.run.call_args_list[0].args[0]
        self.assertIn("get_supply_area_distance", phase1)
        self.assertIn("get_max_wire_distance", phase1)
        self.assertIn("pole.quality", phase1)
        self.assertIn("dx*dx+dy*dy<=reach*reach", phase1)

    def test_place_cell_searches_a_bounded_extension_pole_chain(self):
        client = Mock()
        client.run.return_value = (
            "ERROR: No live power connection within 2 extension poles"
        )

        result = jimbo.place_production_cell(
            client, "nauvis", "electronic-circuit",
            "[gps=10,20,nauvis]", "dlbattle",
        )

        phase1 = client.run.call_args.args[0]
        self.assertEqual(jimbo.production_cell_max_extension_poles, 2)
        self.assertIn("local max_extensions=2", phase1)
        self.assertIn("local search_radius=(max_extensions+1)*new_wire", phase1)
        self.assertIn("local function valid_extension(pos)", phase1)
        self.assertIn("s.count_entities_filtered{area=cell}", phase1)
        self.assertIn("find_logistic_networks_by_construction_area", phase1)
        self.assertIn("local frontier={{position=pole_pos,path={}}}", phase1)
        self.assertIn("distance<=new_wire*new_wire", phase1)
        self.assertIn("reaches_live(candidate.position)", phase1)
        self.assertIn("table.concat(encoded,';')", phase1)
        self.assertEqual(
            result, "ERROR: No live power connection within 2 extension poles"
        )
        self.assertEqual(client.run.call_count, 1)

    def test_place_cell_revalidates_and_creates_extension_poles(self):
        client = Mock()
        client.run.side_effect = [
            (
                "ANCHOR:10,20,3,3,assembling-machine-3,"
                "15.5:19.5;22.5:19.5"
            ),
            "SUCCESS: placed with 2 extension poles",
        ]

        result = jimbo.place_production_cell(
            client, "nauvis", "electronic-circuit",
            "[gps=10,20,nauvis]", "dlbattle",
        )

        phase2 = client.run.call_args_list[1].args[0]
        self.assertIn(
            "local extensions={{15.5,19.5},{22.5,19.5}}", phase2
        )
        self.assertIn("extension pole overlaps cell", phase2)
        self.assertIn("entity appeared at extension pole", phase2)
        self.assertIn("cannot place extension pole", phase2)
        self.assertIn(
            "no construction network coverage for extension pole", phase2
        )
        self.assertIn("extension pole chain exceeds wire reach", phase2)
        self.assertIn("previous=pos", phase2)
        self.assertIn(
            "inner_name='medium-electric-pole'", phase2
        )
        self.assertIn("cleanup[#cleanup+1]=extra", phase2)
        self.assertIn("#extensions..' extension medium-electric-pole'", phase2)
        self.assertEqual(result, "SUCCESS: placed with 2 extension poles")
        self.assertFalse(client.run.call_args_list[1].kwargs.get("retry", False))

    def test_place_cell_rejects_invalid_extension_plan_from_phase1(self):
        invalid_plans = (
            "15:19.5",
            "15.5:19.5;15.5:19.5",
            "15.5:19.5;22.5:19.5;29.5:19.5",
            "nan:19.5",
        )

        for plan in invalid_plans:
            with self.subTest(plan=plan):
                client = Mock()
                client.run.return_value = (
                    "ANCHOR:10,20,3,3,assembling-machine-3," + plan
                )

                result = jimbo.place_production_cell(
                    client, "nauvis", "electronic-circuit",
                    "[gps=10,20,nauvis]", "dlbattle",
                )

                self.assertEqual(result, "ERROR: Invalid location response")
                self.assertEqual(client.run.call_count, 1)

    def test_place_cell_preflights_every_entity_in_both_phases(self):
        client = Mock()
        client.run.side_effect = [
            "ANCHOR:10,20,3,3,assembling-machine-3",
            "SUCCESS: placed",
        ]

        jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]", "dlbattle"
        )

        phase1 = client.run.call_args_list[0].args[0]
        phase2 = client.run.call_args_list[1].args[0]
        for command in (phase1, phase2):
            self.assertIn("s.can_place_entity", command)
            self.assertIn("defines.build_check_type.script_ghost", command)
            self.assertIn("find_logistic_networks_by_construction_area", command)
            self.assertIn("requester-chest", command)
            self.assertIn("passive-provider-chest", command)
            self.assertIn("medium-electric-pole", command)

    def test_place_cell_uses_bottom_left_anchor_geometry(self):
        client = Mock()
        client.run.side_effect = [
            "ANCHOR:10,20,5,5,electromagnetic-plant",
            "SUCCESS: placed",
        ]

        jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]", "dlbattle"
        )

        phase1 = client.run.call_args_list[0].args[0]
        phase2 = client.run.call_args_list[1].args[0]
        self.assertIn("local cx=ax+w/2", phase1)
        self.assertIn("local cy=ay+h/2", phase1)
        self.assertIn("local row=ay+math.floor(h/2)+0.5", phase1)
        self.assertIn("position={cx,cy}", phase2)
        self.assertIn("position={x-1.5,row}", phase2)
        self.assertIn("position={x+w+1.5,row}", phase2)
        self.assertIn("position=plans[1].position", phase2)
        self.assertIn("position=plans[2].position", phase2)
        self.assertIn("position=plans[3].position", phase2)
        self.assertIn("pole_pos={x+math.floor(w/2)+0.5,y-0.5}", phase2)

    def test_place_cell_rejects_fluid_recipes_before_location_checks(self):
        client = Mock()
        client.run.return_value = "ERROR: Fluid recipes are not supported"

        result = jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]", "dlbattle"
        )

        phase1 = client.run.call_args.args[0]
        self.assertIn("ingredient.type=='fluid'", phase1)
        self.assertIn("product.type=='fluid'", phase1)
        self.assertEqual(result, "ERROR: Fluid recipes are not supported")
        self.assertEqual(client.run.call_count, 1)

    def test_place_cell_handles_one_sided_surface_conditions(self):
        client = Mock()
        client.run.return_value = "ERROR: Recipe is not supported on nauvis"

        jimbo.place_production_cell(
            client, "nauvis", "electronic-circuit",
            "[gps=10,20,nauvis]", "dlbattle",
        )

        phase1 = client.run.call_args.args[0]
        self.assertIn("condition.min and value<condition.min", phase1)
        self.assertIn("condition.max and value>condition.max", phase1)

    def test_place_cell_requires_live_heat_for_freezable_aquilo_components(self):
        client = Mock()
        client.run.return_value = (
            "ERROR: No suitable production-cell location within 128 tiles "
            "(last: No heat coverage for assembling-machine-3)"
        )

        result = jimbo.place_production_cell(
            client, "aquilo", "electronic-circuit", "[gps=10,20,aquilo]",
            "dlbattle",
        )

        phase1 = client.run.call_args.args[0]
        self.assertIn("local requires_heat=s.planet and s.planet.name=='aquilo'", phase1)
        self.assertIn("p.heating_energy<=0", phase1)
        self.assertIn("source.prototype.heating_radius", phase1)
        self.assertIn("source.temperature>=30", phase1)
        self.assertIn("local function plan_is_heated(plan)", phase1)
        self.assertIn("local function plan_overlaps_heat_source(plan)", phase1)
        self.assertIn("local function count_blockers(area)", phase1)
        self.assertIn("if not heat_source_type[existing.type]", phase1)
        self.assertIn("No heat coverage for", phase1)
        self.assertNotIn("Unheated cells are not supported on Aquilo", phase1)
        self.assertIn("No heat coverage", result)
        self.assertEqual(client.run.call_count, 1)

    def test_place_cell_rechecks_aquilo_heat_before_mutation(self):
        client = Mock()
        client.run.side_effect = [
            "ANCHOR:10,20,3,3,assembling-machine-3,,aquilo",
            "ERROR: no heat coverage for inserter",
        ]

        result = jimbo.place_production_cell(
            client, "aquilo", "electronic-circuit", "[gps=10,20,aquilo]",
            "dlbattle",
        )

        phase2 = client.run.call_args_list[1].args[0]
        self.assertIn("local requires_heat=s.planet and s.planet.name=='aquilo'", phase2)
        self.assertIn("p.heating_energy<=0", phase2)
        self.assertIn("source.prototype.heating_radius", phase2)
        self.assertIn("source.temperature>=30", phase2)
        self.assertIn("plan_overlaps_heat_source(plan)", phase2)
        self.assertIn("local count=count_blockers(area)", phase2)
        self.assertIn(
            "support_issue('no heat coverage for '..plan.name)", phase2
        )
        self.assertIn("local allow_support_warnings=false", phase2)
        self.assertEqual(result, "ERROR: no heat coverage for inserter")
        self.assertFalse(client.run.call_args_list[1].kwargs.get("retry", False))

    def test_place_cell_fallback_places_with_verified_support_warnings(self):
        client = Mock()
        client.run.side_effect = [
            (
                "ANCHOR:-34,-5,3,3,assembling-machine-3,,aquilo,"
                "aquilo-compact,fallback"
            ),
            (
                "SUCCESS: [gps=-34,-5,aquilo] 3x3 iron-gear-wheel cell placed "
                "with assembling-machine-3, requester-chest, 2 inserters, "
                "passive-provider-chest using existing power; WARNING: "
                "no heat coverage for inserter"
            ),
        ]

        result = jimbo.place_production_cell(
            client, "current", "iron-gear-wheel", "standing:north", "dlbattle"
        )

        phase2 = client.run.call_args_list[1].args[0]
        self.assertIn("local allow_support_warnings=true", phase2)
        self.assertIn("local warnings={};local warning_seen={}", phase2)
        self.assertIn("local function support_issue(text)", phase2)
        self.assertIn(
            "support_issue('no heat coverage for '..plan.name)", phase2
        )
        self.assertIn("support_issue('no logistic network coverage')", phase2)
        self.assertIn(
            "support_issue('no construction network coverage for full cell')",
            phase2,
        )
        self.assertIn(
            "support_issue('no existing power coverage for compact cell')",
            phase2,
        )
        self.assertIn("error(count..' entities appeared in area')", phase2)
        self.assertIn("error('cannot place '..plan.name)", phase2)
        self.assertIn("building recipe was not set", phase2)
        self.assertIn("request filter missing for", phase2)
        self.assertIn(
            "'; WARNING: '..table.concat(warnings,', ')", phase2
        )
        self.assertIn("SUCCESS", result)
        self.assertIn("WARNING", result)
        self.assertFalse(client.run.call_args_list[1].kwargs.get("retry", False))

    def test_place_cell_uses_compact_aquilo_ring_layout(self):
        client = Mock()
        client.run.side_effect = [
            "ANCHOR:-21,-8,3,3,assembling-machine-3,,aquilo,aquilo-compact",
            "SUCCESS: compact cell placed",
        ]

        result = jimbo.place_production_cell(
            client, "aquilo", "pumpjack", "[gps=-21,-8,aquilo]", "dlbattle"
        )

        phase1 = client.run.call_args_list[0].args[0]
        phase2 = client.run.call_args_list[1].args[0]
        self.assertIn("if requires_heat then step_x=1;step_y=1 end", phase1)
        self.assertIn("local compact_area={{ax,ay},{ax+w,ay+h+2}}", phase1)
        self.assertIn("position={ax+0.5,ay+h+1.5}", phase1)
        self.assertIn("position={ax+1.5,ay+h+1.5}", phase1)
        self.assertIn("position={ax+0.5,ay+h+0.5}", phase1)
        self.assertIn("position={ax+1.5,ay+h+0.5}", phase1)
        self.assertIn("direction=defines.direction.south", phase1)
        self.assertIn("direction=defines.direction.north", phase1)
        self.assertIn("plan_has_live_power(compact_plans[1])", phase1)
        self.assertIn("plan_has_live_power(compact_plans[4])", phase1)
        self.assertIn("plan_has_live_power(compact_plans[5])", phase1)
        self.assertIn("aquilo-compact", phase1)
        self.assertIn('local layout="aquilo-compact"', phase2)
        self.assertIn("area={{x,y},{x+w,y+h+2}}", phase2)
        self.assertIn("position={x+0.5,y+h+1.5}", phase2)
        self.assertIn("position={x+1.5,y+h+1.5}", phase2)
        self.assertIn("position={x+0.5,y+h+0.5}", phase2)
        self.assertIn("position={x+1.5,y+h+0.5}", phase2)
        self.assertIn("compact layout cannot use extension poles", phase2)
        self.assertIn("no existing power coverage for compact cell", phase2)
        self.assertIn("using existing power", phase2)
        self.assertEqual(result, "SUCCESS: compact cell placed")
        self.assertFalse(client.run.call_args_list[1].kwargs.get("retry", False))

    def test_place_cell_rejects_invalid_compact_layout_response(self):
        invalid_responses = (
            "ANCHOR:10,20,3,3,assembling-machine-3,,aquilo,unknown",
            "ANCHOR:10,20,3,3,assembling-machine-3,,nauvis,aquilo-compact",
            (
                "ANCHOR:10,20,3,3,assembling-machine-3,,aquilo,"
                "aquilo-compact,unknown"
            ),
            (
                "ANCHOR:10,20,3,3,assembling-machine-3,"
                "15.5:19.5,aquilo,aquilo-compact"
            ),
        )

        for response in invalid_responses:
            with self.subTest(response=response):
                client = Mock()
                client.run.return_value = response

                result = jimbo.place_production_cell(
                    client, "aquilo", "pumpjack", "[gps=10,20,aquilo]",
                    "dlbattle",
                )

                self.assertEqual(result, "ERROR: Invalid location response")
                self.assertEqual(client.run.call_count, 1)

    def test_place_cell_rechecks_occupancy_before_mutation(self):
        client = Mock()
        client.run.side_effect = [
            "ANCHOR:10,20,3,3,assembling-machine-3",
            "ERROR: 1 entities appeared in area",
        ]

        result = jimbo.place_production_cell(
            client, "nauvis", "electronic-circuit", "[gps=10,20,nauvis]",
            "dlbattle",
        )

        phase2 = client.run.call_args_list[1].args[0]
        self.assertIn("s.count_entities_filtered{area=area}", phase2)
        self.assertIn("entities appeared in area", phase2)
        self.assertIn("ERROR", result)

    def test_place_cell_floors_gps_to_bottom_left_tile(self):
        client = Mock()
        client.run.return_value = "ERROR: blocked"

        jimbo.place_production_cell(
            client, "nauvis", "electronic-circuit",
            "[gps=10.9,-20.1,nauvis]", "dlbattle",
        )

        phase1 = client.run.call_args.args[0]
        self.assertIn("local explicit_ax=10;local explicit_ay=-21", phase1)

    def test_place_cell_phase2_reports_incomplete_rollback(self):
        client = Mock()
        client.run.side_effect = [
            "ANCHOR:10,20,3,3,assembling-machine-3",
            "ERROR: request filter failed; rollback incomplete: 1",
        ]

        result = jimbo.place_production_cell(
            client, "nauvis", "electronic-circuit",
            "[gps=10,20,nauvis]", "dlbattle",
        )

        phase2 = client.run.call_args_list[1].args[0]
        self.assertIn("for i=#cleanup,1,-1", phase2)
        self.assertIn("rollback incomplete", phase2)
        self.assertEqual(
            result, "ERROR: request filter failed; rollback incomplete: 1"
        )


if __name__ == "__main__":
    unittest.main()
