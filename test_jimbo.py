import json
import os
import tempfile
import unittest
from collections import deque
from datetime import datetime
from unittest.mock import Mock, mock_open, patch

import jimbo


def log_time(timestamp):
    return datetime.fromtimestamp(timestamp).strftime("%Y-%m-%d %H:%M:%S")


"""jimbo.py's send_jimbo_chat builds the print command; keep the sound path here in
sync with the jimbo_chat_sound_path constant."""


def jimbo_cmd(text):
    return (
        "/silent-command game.forces.player.print("
        + json.dumps(text, ensure_ascii=False)
        + ", {sound=defines.print_sound.use_player_settings, "
        + "sound_path=" + json.dumps(jimbo.jimbo_chat_sound_path, ensure_ascii=False) + "})"
    )


class DialogueTests(unittest.TestCase):
    def setUp(self):
        self._says = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
        self.addCleanup(lambda: os.unlink(self._says.name))
        self._says.close()
        self._says_patch = patch.object(jimbo, "jimbo_says_log_path", self._says.name)
        self._says_patch.start()
        self.addCleanup(self._says_patch.stop)

    def test_all_historical_ai_profiles_are_predefined(self):
        self.assertEqual(
            set(jimbo.ai_profiles),
            {"openai", "deepseek", "big-pickle", "free-models-router", "ollama", "nemotron"},
        )
        self.assertEqual(
            jimbo.ai_profiles["openai"]["model"], "openai/gpt-5.4-mini"
        )
        self.assertEqual(
            jimbo.ai_profiles["deepseek"]["model"], "deepseek-v4-flash"
        )
        self.assertEqual(jimbo.ai_profiles["big-pickle"]["model"], "big-pickle")
        self.assertEqual(jimbo.ai_profiles["big-pickle"]["provider"], "openai-compatible")
        self.assertEqual(
            jimbo.ai_profiles["big-pickle"]["base_url"],
            "https://opencode.ai/zen/v1",
        )
        self.assertEqual(
            jimbo.ai_profiles["big-pickle"]["auth_provider"], "opencode"
        )
        self.assertEqual(
            jimbo.ai_profiles["big-pickle"]["request_options"]["max_completion_tokens"],
            4096,
        )
        self.assertEqual(
            jimbo.ai_profiles["ollama"]["model"], "qwen2.5-32b-ctx32k"
        )
        self.assertEqual(
            jimbo.ai_profiles["free-models-router"]["model"], "openrouter/free"
        )
        self.assertEqual(
            jimbo.ai_profiles["deepseek"]["provider"], "openai-compatible"
        )
        self.assertEqual(
            jimbo.ai_profiles["deepseek"]["base_url"],
            "https://opencode.ai/zen/v1",
        )
        self.assertEqual(jimbo.ai_profiles["deepseek"]["auth_provider"], "opencode")
        self.assertEqual(
            jimbo.ai_profiles["free-models-router"]["provider"], "openai-compatible"
        )
        self.assertEqual(
            jimbo.ai_profiles["free-models-router"]["base_url"],
            "https://openrouter.ai/api/v1",
        )
        self.assertEqual(
            os.path.basename(jimbo.ai_profiles["free-models-router"]["api_key_path"]),
            "openrouter.key",
        )
        self.assertEqual(
            jimbo.ai_profiles["free-models-router"]["request_options"][
                "max_completion_tokens"
            ],
            256,
        )
        self.assertEqual(
            jimbo.ai_profiles["free-models-router"]["request_options"]["extra_body"],
            {"include_reasoning": False, "reasoning_effort": "low"},
        )
        self.assertEqual(jimbo.ai_profiles["ollama"]["provider"], "ollama")
        self.assertEqual(
            jimbo.ai_profiles["ollama"]["host"], "http://127.0.0.1:11434"
        )
        self.assertEqual(jimbo.ai_profiles["nemotron"]["provider"], "openai-compatible")
        self.assertEqual(
            jimbo.ai_profiles["nemotron"]["model"],
            "nvidia/nemotron-3-ultra-550b-a55b:free",
        )
        self.assertEqual(
            jimbo.ai_profiles["nemotron"]["base_url"],
            "https://openrouter.ai/api/v1",
        )
        self.assertEqual(
            os.path.basename(jimbo.ai_profiles["nemotron"]["api_key_path"]),
            "openrouter.key",
        )
        self.assertEqual(
            jimbo.ai_profiles["nemotron"]["request_options"]["max_completion_tokens"],
            1024,
        )
        self.assertEqual(
            jimbo.ai_profiles["nemotron"]["request_options"]["extra_body"],
            {"reasoning": {"exclude": True}},
        )
        self.assertIs(jimbo.ai_profile, jimbo.ai_profiles[jimbo.ai_profile_name])
        self.assertEqual(jimbo.model_name, jimbo.ai_profile["model"])
        self.assertEqual(jimbo.model_identity, jimbo.ai_profile["identity"])

    def test_ai_profile_selects_its_provider_adapter(self):
        cases = (
            ("openai", "ask_opencode"),
            ("deepseek", "ask_openai_compatible"),
            ("big-pickle", "ask_openai_compatible"),
            ("free-models-router", "ask_openai_compatible"),
            ("ollama", "ask_ollama"),
            ("nemotron", "ask_openai_compatible"),
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
            model="deepseek-v4-flash",
            messages=[{"role": "user", "content": "prompt"}],
        )

    def test_free_models_router_adapter_uses_key_file_and_hides_reasoning(self):
        profile = jimbo.ai_profiles["free-models-router"]
        result = Mock()
        result.choices = [Mock(message=Mock(content=" response "))]
        with patch("builtins.open", mock_open(
            read_data="router-secret"
        )), patch("openai.OpenAI") as constructor:
            constructor.return_value.chat.completions.create.return_value = result

            response = jimbo.ask_openai_compatible("prompt", profile)

        self.assertEqual(response, "response")
        constructor.assert_called_once_with(
            api_key="router-secret",
            base_url="https://openrouter.ai/api/v1",
            timeout=120,
            max_retries=0,
        )
        constructor.return_value.chat.completions.create.assert_called_once_with(
            model="openrouter/free",
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
        jimbo.add_dialogue_turn(dialogue, "Old", "expired", timestamp=now - 2401)
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
        with patch.object(jimbo, "record_jimbo_says"):
            sent, error = jimbo.send_jimbo_lines(
                client, "first\n(Note: hidden)\nsecond\n(Corrected output)"
            )

        self.assertEqual(sent, ["first"])
        self.assertIsInstance(error, BrokenPipeError)
        self.assertEqual(client.commands, [jimbo_cmd("Jimbo says first")])

    def test_chat_delivery_does_not_request_automatic_replay(self):
        client = Mock()

        with patch.object(jimbo, "record_jimbo_says"):
            sent, error = jimbo.send_jimbo_lines(client, "hello")

        self.assertEqual(sent, ["hello"])
        self.assertIsNone(error)
        client.run.assert_called_once_with(jimbo_cmd("Jimbo says hello"))

    def test_chat_delivery_passes_non_ascii_as_raw_utf8(self):
        client = Mock()

        with patch.object(jimbo, "record_jimbo_says"):
            sent, error = jimbo.send_jimbo_lines(client, "steady hum \U0001F604")

        self.assertEqual(sent, ["steady hum \U0001F604"])
        self.assertIsNone(error)
        command = client.run.call_args.args[0]
        self.assertIn("steady hum \U0001F604", command)
        self.assertNotIn("\\u", command)

    def test_console_prime_sends_identical_noop_twice(self):
        client = Mock()

        jimbo.prime_lua_console(client)

        self.assertEqual(client.run.call_count, 2)
        first, second = client.run.call_args_list
        self.assertEqual(first, second)
        self.assertEqual(first.args[0], jimbo.lua_console_prime_command)

    def test_ai_warmup_uses_throwaway_prompt(self):
        with patch.object(jimbo, "ask_ai", return_value="ok") as ask:
            jimbo.warm_up_ai()

        ask.assert_called_once_with(jimbo.ai_warmup_prompt)

    def test_ai_warmup_failure_does_not_raise(self):
        with patch.object(jimbo, "ask_ai", side_effect=RuntimeError("down")):
            jimbo.warm_up_ai()

    def test_record_jimbo_says_appends_formatted_chat_line(self):
        path = tempfile.NamedTemporaryFile("w", encoding="utf-8", delete=False)
        self.addCleanup(lambda: os.unlink(path.name))
        path.close()

        with patch.object(jimbo, "jimbo_says_log_path", path.name):
            jimbo.record_jimbo_says("Jimbo says hello")

        with open(path.name, encoding="utf-8") as f:
            line = f.read().strip()
        self.assertTrue(
            line.endswith("[CHAT] <server>: Jimbo says hello")
        )

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

        with patch.object(jimbo, "record_jimbo_says"):
            sent, error = jimbo.report_request_failure(client, dialogue, recent_chat)

        self.assertEqual(sent, ["I tried, but I couldn't complete that request."])
        self.assertIsNone(error)
        client.run.assert_called_once_with(
            jimbo_cmd("Jimbo says I tried, but I couldn't complete that request.")
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
        self.assertIn('local scope="nauvis"', command)
        self.assertIn("game.surfaces[scope]", command)
        self.assertIn("add_chart_tag", command)
        self.assertIn("name=et", command)
        self.assertIn("type=et", command)
        self.assertIn("icon={type='entity',name=et}", command)
        self.assertTrue(client.run.call_args.kwargs["retry"])
        self.assertIn("Tagged", result)

    def test_tag_command_scans_all_surfaces(self):
        client = Mock()
        client.run.return_value = "Tagged 4 character-corpse on nauvis:4"
        result = jimbo.run_tag_command(client, "all", "character-corpse", "")
        command = client.run.call_args.args[0]
        self.assertIn('local scope="all"', command)
        self.assertIn("scope=='all'", command)
        self.assertIn("pairs(game.surfaces)", command)
        self.assertIn("table.concat(res,',')", command)
        self.assertIn("add_chart_tag", command)
        self.assertIn("Tagged", result)

    def test_tag_command_tags_player_corpses(self):
        client = Mock()
        client.run.return_value = "Tagged 4 character-corpse on nauvis:4"
        result = jimbo.run_tag_command(client, "nauvis", "character-corpse", "")
        command = client.run.call_args.args[0]
        self.assertIn('local et="character-corpse"', command)
        self.assertIn("name=et", command)
        self.assertIn("type=et", command)
        self.assertIn("add_chart_tag", command)
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
        self.assertIn("[gps=", command)
        self.assertIn("icon_name..' '..tostring(best.unit_number)", command)
        self.assertTrue(client.run.call_args.kwargs["retry"])
        self.assertIn("Tagged", result)

    def test_top_damage_response_includes_exact_map_ping(self):
        client = Mock()
        client.run.return_value = (
            "Tagged tesla-turret unit 10093840 at 646,1020 with 211368 "
            "damage [gps=646,1020,nauvis]"
        )
        result = jimbo.run_top_damage_command(client, "nauvis", "tesla-turret")
        self.assertIn("[gps=646,1020,nauvis]", result)

    def test_top_damage_reply_hint_requires_exact_map_ping(self):
        prompt = jimbo.build_reply_prompt(
            jimbo.server_owner,
            "Jimbo ping the map and show the highest damage",
            "(none)",
            "RCON: top damage",
            "Tagged tesla-turret unit 10093840 at 646,1020 with 211368 "
            "damage [gps=646,1020,nauvis]",
        )
        self.assertIn("[gps=x,y,surface]", prompt)
        self.assertIn("include that markup verbatim", prompt)
        self.assertIn("never invent or change the coordinates", prompt)

    def test_ensure_gps_ping_appends_verified_ping_when_missing(self):
        reply = "Done! I pinged the tesla turret at 646,1020."
        response = "Tagged tesla-turret unit 12 at 646,1020 with 211368 "
        response += "damage [gps=646,1020,nauvis]"
        merged = jimbo.ensure_gps_ping(
            reply, "RCON: top damage", response
        )
        self.assertIn("[gps=646,1020,nauvis]", merged)
        self.assertTrue(merged.endswith("Requested location: [gps=646,1020,nauvis]"))

    def test_ensure_gps_ping_keeps_existing_ping(self):
        reply = "Done! [gps=646,1020,nauvis]"
        merged = jimbo.ensure_gps_ping(
            reply,
            "RCON: top damage",
            "Tagged tesla-turret unit 12 at 646,1020 with 211368 damage "
            "[gps=646,1020,nauvis]",
        )
        self.assertEqual(merged, reply)

    def test_ensure_gps_ping_skips_failure_or_other_commands(self):
        failure = jimbo.ensure_gps_ping(
            "No tesla-turret found.",
            "RCON: top damage",
            "No tesla-turret found on nauvis",
        )
        self.assertEqual(failure, "No tesla-turret found.")
        other = jimbo.ensure_gps_ping(
            "Hey, there are 134 turrets.",
            "RCON: list platforms",
            "some platform",
        )
        self.assertEqual(other, "Hey, there are 134 turrets.")

    def test_untag_decision_parses_and_validates(self):
        self.assertEqual(
            jimbo.parse_untag_decision("UNTAG|nauvis|artillery-turret"),
            ("nauvis", "artillery-turret", ""),
        )
        self.assertEqual(
            jimbo.parse_untag_decision("UNTAG|nauvis|foundry|foundry 771429"),
            ("nauvis", "foundry", "foundry 771429"),
        )
        self.assertIsNone(jimbo.parse_untag_decision("UNTAG|Nauvis|foundry"))

    def test_untag_command_matches_label_and_type_prefixes(self):
        client = Mock()
        client.run.return_value = "Removed 1 tags from nauvis"
        result = jimbo.run_untag_command(
            client, "nauvis", "foundry", "foundry 771429"
        )
        command = client.run.call_args.args[0]
        self.assertIn('local scope="nauvis"', command)
        self.assertIn("find_chart_tags", command)
        self.assertIn("tag.text:lower():match('^'..label_text", command)
        self.assertIn("tag.text:lower():match('^'..et", command)
        self.assertTrue(client.run.call_args.kwargs["retry"])
        self.assertIn("Removed", result)

    def test_untag_command_scans_all_surfaces(self):
        client = Mock()
        client.run.return_value = "Removed 4 tags on nauvis:4"
        result = jimbo.run_untag_command(client, "all", "character-corpse", "")
        command = client.run.call_args.args[0]
        self.assertIn('local scope="all"', command)
        self.assertIn("scope=='all'", command)
        self.assertIn("pairs(game.surfaces)", command)
        self.assertIn("find_chart_tags", command)
        self.assertIn("Removed", result)

    def test_classifier_guidance_for_corpse_tagging(self):
        prompt = jimbo.build_classification_prompt(
            jimbo.server_owner,
            "Jimbo please tag all player corpses",
            "(none)",
        )
        self.assertIn("character-corpse", prompt)
        self.assertIn("TAG|all|character-corpse|", prompt)
        self.assertIn("scan every surface", prompt)

    def test_classification_prompt_includes_lua_essentials(self):
        with patch.object(
            jimbo, "lua_essentials_text", "ESSENTIALS SENTINEL rcon.print"
        ):
            prompt = jimbo.build_classification_prompt(
                jimbo.server_owner,
                "Jimbo how many iron chests exist",
                "(none)",
            )
        self.assertIn("authoritative", prompt)
        self.assertIn("ESSENTIALS SENTINEL rcon.print", prompt)

    def test_reply_prompt_omits_lua_essentials(self):
        with patch.object(
            jimbo, "lua_essentials_text", "ESSENTIALS SENTINEL rcon.print"
        ):
            reply = jimbo.build_reply_prompt(
                jimbo.server_owner,
                "Jimbo how many iron chests exist",
                "(none)",
                "RCON: scripted query",
                "42",
            )
            none_reply = jimbo.build_reply_prompt(
                jimbo.server_owner,
                "Jimbo how's the weather",
                "(none)",
                "NONE",
                None,
            )
        self.assertNotIn("ESSENTIALS SENTINEL", reply)
        self.assertNotIn("ESSENTIALS SENTINEL", none_reply)

    def test_missing_lua_essentials_file_returns_empty(self):
        self.assertEqual(
            jimbo.load_lua_essentials("/nonexistent/lua_essentials.txt"), ""
        )

    def test_lua_essentials_generator_builds_compact_reference(self):
        import generate_lua_reference as gen

        doc = {
            "application_version": "9.9.9-test",
            "global_objects": [
                {"name": "game", "type": "LuaGameScript", "description": "Main entry."},
            ],
            "global_functions": [],
            "classes": [{"name": "LuaSurface"}, {"name": "LuaEntity"}],
        }
        text = gen.build_essentials(doc, "runtime-api.json")
        self.assertIn("9.9.9-test", text)
        self.assertIn("- game :: LuaGameScript — Main entry.", text)
        self.assertIn("LuaSurface, LuaEntity", text)
        self.assertIn("CORE RULES", text)

    def test_lua_essentials_generator_includes_ghost_idiom(self):
        import generate_lua_reference as gen

        text = gen.build_essentials(
            {"application_version": "9.9.9-test"}, "runtime-api.json"
        )
        self.assertIn('e.type == "entity-ghost"', text)
        self.assertIn("no e.ghost field exists", text)
        self.assertIn("e.ghost_type", text)
        self.assertIn("e.ghost_name", text)


    def test_untag_classifier_guidance_for_just_tagged_entity(self):
        prompt = jimbo.build_classification_prompt(
            jimbo.server_owner,
            "Jimbo remove all tags on that foundry",
            "(none)",
        )
        self.assertIn("UNTAG|nauvis|foundry|", prompt)
        self.assertIn("do not build a label from a unit number", prompt)
        self.assertIn("starts with that label", prompt)

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

        self.assertIn("available stock in player logistic networks", prompt)
        self.assertIn("never a recipe shortfall", prompt)
        self.assertIn("Report ONLY counts that literally appear", prompt)

    def test_logistic_reply_forbids_inventing_counts_when_none_found(self):
        prompt = jimbo.build_reply_prompt(
            jimbo.server_owner,
            "Jimbo how many iron plates exist on Nauvis?",
            "(none)",
            "RCON: logistic availability",
            "No player logistic networks found",
        )

        self.assertIn(
            "never reuse or extrapolate a number", prompt
        )
        self.assertIn(
            "say plainly that there are none to count", prompt
        )

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

    def test_alerts_snapshot_queries_grouped_alerts(self):
        client = Mock()
        client.run.return_value = (
            "nauvis|turret_enemy:1\n"
            "fulgora|not_enough_construction_robots:2"
        )

        snapshot = jimbo.get_alerts_snapshot(client)

        command = client.run.call_args.args[0]
        self.assertIn("f.alerts", command)
        self.assertIn("a.surface.name", command)
        self.assertIn("groups[key]", command)
        self.assertIn("nauvis|turret_enemy:1", snapshot)
        self.assertIn("fulgora|not_enough_construction_robots:2", snapshot)
        self.assertTrue(client.run.call_args.kwargs["retry"])

    def test_alerts_snapshot_reports_no_active_alerts(self):
        client = Mock()
        client.run.return_value = ""

        self.assertEqual(jimbo.get_alerts_snapshot(client), "(no active alerts)")

    def test_prepare_alerts_for_prompt_debounces_platform_storage(self):
        raw = "nauvis|no_platform_storage:1"

        first, keys = jimbo.prepare_alerts_for_prompt(raw, set())
        self.assertEqual(first, "(no active alerts)")
        self.assertIn("nauvis|no_platform_storage", keys)

        second, keys2 = jimbo.prepare_alerts_for_prompt(raw, keys)
        self.assertIn("nauvis|no_platform_storage:1", second)
        self.assertEqual(keys2, keys)

    def test_prepare_alerts_for_prompt_keeps_real_alerts_immediately(self):
        raw = "nauvis|turret_enemy:1\nfulgora|not_enough_construction_robots:2"

        text, keys = jimbo.prepare_alerts_for_prompt(raw, set())

        self.assertIn("nauvis|turret_enemy:1", text)
        self.assertIn("fulgora|not_enough_construction_robots:2", text)
        self.assertEqual(
            keys,
            {"nauvis|turret_enemy", "fulgora|not_enough_construction_robots"},
        )

    def test_spontaneous_prompt_includes_alerts_snapshot(self):
        def run(command, retry=False):
            if "#game.connected_players" in command:
                return "1"
            if "current=f.current_research" in command:
                return "Current: mining-productivity-3\nProgress: 52.30%\nQueue:"
            if "f.alerts" in command:
                return "nauvis|turret_enemy:1"
            return ""

        client = Mock()
        client.run.side_effect = run
        state = {
            "skip_next": False,
            "failed_attempts": 0,
            "research_name": None,
            "research_progress": None,
            "stall_announced": False,
            "alerts_prev_keys": set(),
        }

        with patch.object(jimbo, "ask_ai", return_value="SKIP") as ask_ai:
            with patch.object(jimbo.time, "time", return_value=1300):
                jimbo.maybe_spontaneous(client, [], deque(), 0, state)

        prompt = ask_ai.call_args.args[0]
        self.assertIn("current game alerts snapshot", prompt)
        self.assertIn("nauvis|turret_enemy:1", prompt)

    def test_spontaneous_records_alerts_context_when_used(self):
        def run(command, retry=False):
            if "#game.connected_players" in command:
                return "1"
            if "current=f.current_research" in command:
                return "Current: mining-productivity-3\nProgress: 52.30%\nQueue:"
            if "f.alerts" in command:
                return "nauvis|turret_enemy:1"
            return ""

        client = Mock()
        client.run.side_effect = run
        state = {
            "skip_next": False,
            "failed_attempts": 0,
            "research_name": None,
            "research_progress": None,
            "stall_announced": False,
            "alerts_prev_keys": set(),
        }
        dialogue = deque()

        with patch.object(
            jimbo, "ask_ai", return_value="There is a turret enemy alert near base."
        ):
            with patch.object(jimbo.time, "time", return_value=1300):
                jimbo.maybe_spontaneous(client, [], dialogue, 0, state)

        self.assertEqual(len(dialogue), 1)
        self.assertEqual(dialogue[0]["rcon_command"], "alerts snapshot")
        self.assertEqual(dialogue[0]["rcon_response"], "nauvis|turret_enemy:1")

    def test_active_alerts_break_stalled_research_silence(self):
        def run(command, retry=False):
            if "#game.connected_players" in command:
                return "1"
            if "current=f.current_research" in command:
                return "Current: mining-productivity-3\nProgress: 52.30%\nQueue:"
            if "f.alerts" in command:
                return "nauvis|turret_enemy:1"
            return ""

        client = Mock()
        client.run.side_effect = run
        state = {
            "skip_next": False,
            "failed_attempts": 0,
            "research_name": "mining-productivity-3",
            "research_progress": 52.3,
            "stall_announced": True,
            "alerts_prev_keys": set(),
        }

        with patch.object(jimbo, "ask_ai", return_value="SKIP") as ask_ai:
            with patch.object(jimbo.time, "time", return_value=1300):
                jimbo.maybe_spontaneous(client, [], deque(), 0, state)

        ask_ai.assert_called_once()
        prompt = ask_ai.call_args.args[0]
        self.assertIn("nauvis|turret_enemy:1", prompt)

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

    def test_unrecognized_prose_classification_is_retried(self):
        with patch.object(
            jimbo,
            "ask_ai",
            side_effect=[
                (
                    "The user is asking for small power poles. This is a direct "
                    "request to Jimbo. The appropriate command is LOGISTICS."
                ),
                "LOGISTICS|all|small-electric-pole,medium-electric-pole",
            ],
        ) as ask_ai:
            result = jimbo.classify_current_message(
                "Threevee", "Jimbo i need small power poles", "(none)"
            )

        self.assertEqual(
            result,
            "LOGISTICS|all|small-electric-pole,medium-electric-pole",
        )
        self.assertEqual(ask_ai.call_count, 2)
        self.assertIn(
            "reply with exactly one line",
            ask_ai.call_args_list[1].args[0].lower(),
        )

    def test_recognized_classification_is_not_retried(self):
        with patch.object(jimbo, "ask_ai", return_value="NONE") as ask_ai:
            result = jimbo.classify_current_message(
                "Alice", "Jimbo thanks", "(none)"
            )

        self.assertEqual(result, "NONE")
        ask_ai.assert_called_once()

    def test_lookup_classification_is_recognized_without_retry(self):
        decision = (
            "LOOKUP|LuaSurface,LuaEntity|how many iron-plate items exist on "
            "nauvis"
        )
        with patch.object(jimbo, "ask_ai", return_value=decision) as ask_ai:
            result = jimbo.classify_current_message(
                "dlbattle",
                "Jimbo how many iron plates are in chests on Nauvis?",
                "(none)",
            )

        self.assertEqual(result, decision)
        ask_ai.assert_called_once()

    def test_unrecognized_classification_logs_raw_response(self):
        prose = (
            "The user is asking for small power poles. This is a direct "
            "request to Jimbo. The appropriate command is LOGISTICS."
        )
        with patch.object(
            jimbo,
            "ask_ai",
            side_effect=[prose, "LOGISTICS|all|small-electric-pole"],
        ), patch("builtins.print") as output:
            result = jimbo.classify_current_message(
                "Threevee", "Jimbo i need small power poles", "(none)"
            )

        self.assertEqual(
            result, "LOGISTICS|all|small-electric-pole"
        )
        logged = "".join(str(call.args[0]) for call in output.call_args_list)
        self.assertIn(prose, logged)

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

    def test_classifier_knows_equipment_prototypes_and_enumeration(self):
        prompt = jimbo.build_classification_prompt(
            jimbo.server_owner,
            "Jimbo how much energy does a personal roboport need to charge?",
            "(none)",
        )

        self.assertIn('prototypes.equipment["personal-roboport-', prompt)
        self.assertIn("personal-roboport-mk2-equipment", prompt)
        self.assertIn("prototypes.equipment, not prototypes.entity", prompt)
        self.assertIn("attempt to index field", prompt)
        self.assertIn("pairs() and a substring :find()", prompt)

    def test_classifier_knows_equipment_buffer_reading_and_pcall(self):
        prompt = jimbo.build_classification_prompt(
            jimbo.server_owner,
            "Jimbo how many MJ is the exoskeleton internal buffer?",
            "(none)",
        )

        self.assertIn("p.energy_source.buffer_capacity", prompt)
        self.assertIn("has no internal buffer", prompt)
        self.assertIn("exoskeleton is 0", prompt)
        self.assertIn("doesn't contain key X", prompt)
        self.assertIn("wrap each field read in pcall", prompt)
        self.assertIn("Never invent a value", prompt)

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
        old = log_time(now - 2500)
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

    def test_hydration_merges_jimbo_says_log_by_timestamp(self):
        now = 1_800_000_000
        player = log_time(now - 90)
        reply = log_time(now - 80)
        server_path = self.write_log([
            f"{player} [CHAT] Alice: Jimbo who is online?",
        ])
        jimbo_path = self.write_log([
            f"{reply} [CHAT] <server>: Jimbo says Alice is online.",
        ])
        dialogue = deque()

        jimbo.hydrate_dialogue(server_path, dialogue, jimbo_path, now=now)

        self.assertEqual(len(dialogue), 2)
        self.assertEqual(dialogue[0]["speaker"], "Alice")
        self.assertEqual(dialogue[1]["speaker"], "Jimbo")
        self.assertEqual(dialogue[1]["text"], "Alice is online.")

    def test_hydration_without_jimbo_log_ignores_missing_file(self):
        now = 1_800_000_000
        player = log_time(now - 90)
        server_path = self.write_log([
            f"{player} [CHAT] Alice: Jimbo who is online?",
        ])
        dialogue = deque()

        jimbo.hydrate_dialogue(server_path, dialogue, "missing.log", now=now)

        self.assertEqual(len(dialogue), 1)
        self.assertEqual(dialogue[0]["speaker"], "Alice")


class ProduceCellTests(unittest.TestCase):
    def candidates_response(self, extra=""):
        return f"CANDIDATES:assembling-machine-3:3:3{extra}"

    def produce_client(self, phase1_response, phase2_response=None):
        client = Mock()
        effects = [self.candidates_response(), phase1_response]
        if phase2_response is not None:
            effects.append(phase2_response)
        client.run.side_effect = effects
        return client

    def test_parse_produce_decision_valid(self):
        result = jimbo.parse_produce_decision(
            "PRODUCE|nauvis|processing-unit|"
        )
        self.assertEqual(
            result,
            (
                "nauvis",
                "processing-unit",
                "",
                jimbo.default_production_cell_knobs(),
            ),
        )

    def test_parse_produce_decision_with_gps(self):
        result = jimbo.parse_produce_decision(
            "PRODUCE|fulgora|holmium-plate|[gps=10,20,fulgora]"
        )
        self.assertEqual(
            result,
            (
                "fulgora",
                "holmium-plate",
                "[gps=10,20,fulgora]",
                jimbo.default_production_cell_knobs(),
            ),
        )

    def test_parse_produce_decision_with_normalized_direction(self):
        for direction in jimbo.production_cell_directions:
            with self.subTest(direction=direction):
                self.assertEqual(
                    jimbo.parse_produce_decision(
                        f"PRODUCE|nauvis|iron-plate|{direction}"
                    ),
                    (
                        "nauvis",
                        "iron-plate",
                        direction,
                        jimbo.default_production_cell_knobs(),
                    ),
                )

    def test_parse_produce_decision_distinguishes_view_and_standing(self):
        self.assertEqual(
            jimbo.parse_produce_decision(
                "PRODUCE|current|iron-plate|view"
            ),
            (
                "current",
                "iron-plate",
                "view",
                jimbo.default_production_cell_knobs(),
            ),
        )
        self.assertEqual(
            jimbo.parse_produce_decision(
                "PRODUCE|current|iron-plate|standing"
            ),
            (
                "current",
                "iron-plate",
                "standing",
                jimbo.default_production_cell_knobs(),
            ),
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
                        (
                            "current",
                            "iron-plate",
                            hint,
                            jimbo.default_production_cell_knobs(),
                        ),
                    )

    def test_parse_produce_decision_knobs_field(self):
        surface, item, hint, knobs = jimbo.parse_produce_decision(
            "PRODUCE|current|iron-gear-wheel|standing:north|"
            "layout=belt-fed,rotation=west,lanes=2,tier=smallest"
        )
        self.assertEqual((surface, item, hint), ("current", "iron-gear-wheel", "standing:north"))
        self.assertEqual(
            knobs,
            {
                "layout": "belt-fed",
                "rotation": "west",
                "lanes": 2,
                "tier": "smallest",
            },
        )

    def test_parse_produce_decision_rejects_bad_knobs(self):
        for field in (
            "layout=mystery",
            "rotation=north-west",
            "lanes=3",
            "tier=cheapest",
            "color=red",
            "layout=belt-fed,layout=standard",
            "layout",
            "layout=",
        ):
            with self.subTest(field=field):
                self.assertIsNone(
                    jimbo.parse_produce_decision(
                        f"PRODUCE|nauvis|iron-plate||{field}"
                    )
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

    def test_remove_decision_valid_forms(self):
        self.assertEqual(
            jimbo.parse_remove_decision("REMOVE|nauvis|entity-ghost|[gps=6,-39]"),
            ("nauvis", "entity-ghost", "[gps=6,-39]"),
        )
        self.assertEqual(
            jimbo.parse_remove_decision("REMOVE|nauvis|entity-ghost|[gps=6,-39,nauvis]"),
            ("nauvis", "entity-ghost", "[gps=6,-39,nauvis]"),
        )
        self.assertEqual(
            jimbo.parse_remove_decision("REMOVE|nauvis|any"),
            ("nauvis", "any", ""),
        )
        self.assertEqual(
            jimbo.parse_remove_decision("REMOVE|all|character-corpse|"),
            ("all", "character-corpse", ""),
        )
        self.assertEqual(
            jimbo.parse_remove_decision("REMOVE|current|any|standing:north"),
            ("current", "any", "standing:north"),
        )

    def test_parse_remove_decision_invalid_forms(self):
        self.assertIsNone(jimbo.parse_remove_decision("DELETE|nauvis|any"))
        self.assertIsNone(jimbo.parse_remove_decision("REMOVE|nauvis|Iron-Chest"))
        self.assertIsNone(jimbo.parse_remove_decision("REMOVE|Nauvis|any"))
        self.assertIsNone(
            jimbo.parse_remove_decision("REMOVE|nauvis|any|[gps=1,2,vulcanus]")
        )
        self.assertIsNone(
            jimbo.parse_remove_decision("REMOVE|nauvis|any|[gps=nan,2]")
        )
        self.assertIsNone(
            jimbo.parse_remove_decision("REMOVE|nauvis|any|over-there")
        )

    def test_recognized_classification_accepts_remove_without_retry(self):
        decision = "REMOVE|nauvis|entity-ghost|[gps=6,-39,nauvis]"
        with patch.object(jimbo, "ask_ai", return_value=decision) as ask_ai:
            result = jimbo.classify_current_message(
                "Koopix",
                "Jimbo delete the ghosts you placed there",
                "(none)",
            )

        self.assertEqual(result, decision)
        ask_ai.assert_called_once()

    def test_recognized_classification_accepts_produce_knobs_without_retry(self):
        decision = (
            "PRODUCE|current|iron-gear-wheel|standing:north|layout=belt-fed"
        )
        with patch.object(jimbo, "ask_ai", return_value=decision) as ask_ai:
            result = jimbo.classify_current_message(
                "dlbattle",
                "Jimbo put a belt-fed iron gear cell north of me",
                "(none)",
            )

        self.assertEqual(result, decision)
        ask_ai.assert_called_once()

    def test_remove_entities_requires_requesting_player(self):
        client = Mock()
        self.assertEqual(
            jimbo.remove_entities(client, "nauvis", "any"),
            "ERROR: Requesting player is required",
        )
        client.run.assert_not_called()

    def test_remove_entities_rejects_unstructured_hint(self):
        client = Mock()
        result = jimbo.remove_entities(
            client, "nauvis", "any", "somewhere-over-there", "dlbattle"
        )
        self.assertEqual(result, "ERROR: Invalid location hint")
        client.run.assert_not_called()

    def test_remove_entities_runs_command_and_returns_response(self):
        client = Mock()
        client.run.return_value = (
            "Removed 6 ghosts, newly marked 0 for deconstruction, "
            "0 already marked on nauvis (removed 6, marked 0, "
            "already marked 0, skipped 0)"
        )
        result = jimbo.remove_entities(
            client,
            "nauvis",
            "entity-ghost",
            "[gps=6,-39]",
            requesting_player="dlbattle",
        )

        command = client.run.call_args.args[0]
        self.assertTrue(command.startswith("/silent-command "))
        self.assertIn('"nauvis"', command)
        self.assertIn('"entity-ghost"', command)
        self.assertIn(f"radius={jimbo.remove_area_radius}", command)
        self.assertIn('"dlbattle"', command)
        self.assertIn("{ox-radius,oy-radius},{ox+radius,oy+radius}", command)
        self.assertIn("order_deconstruction('player',request_player)", command)
        self.assertIn("to_be_deconstructed()", command)
        self.assertIn("'entity-ghost'", command)
        self.assertIn("'tile-ghost'", command)
        self.assertEqual(result, client.run.return_value.strip())

    def test_remove_entities_defaults_empty_location_to_view(self):
        client = Mock()
        client.run.return_value = "Removed 0 ghosts"
        jimbo.remove_entities(client, "nauvis", "any", "", "dlbattle")
        command = client.run.call_args.args[0]
        self.assertIn('relative_location=""', command)
        self.assertNotIn("explicit=true", command)

    def test_remove_entities_resolves_current_surface(self):
        client = Mock()
        client.run.return_value = "Removed 3 ghosts"
        result = jimbo.remove_entities(
            client,
            "current",
            "transport-belt",
            "standing:north",
            requesting_player="dlbattle",
        )

        command = client.run.call_args.args[0]
        self.assertIn("scope=='current'", command)
        self.assertIn("request_player.physical_surface", command)
        self.assertEqual(result, "Removed 3 ghosts")

    def test_remove_entities_any_type_searches_unfiltered(self):
        client = Mock()
        client.run.return_value = "Removed 0 ghosts"
        jimbo.remove_entities(
            client, "nauvis", "any", "[gps=0,0]", requesting_player="dlbattle"
        )
        command = client.run.call_args.args[0]
        self.assertIn("et~='any'", command)
        self.assertIn("find_entities_filtered{area=area}", command)

    def test_remove_entities_empty_response_becomes_error(self):
        client = Mock()
        client.run.return_value = ""
        result = jimbo.remove_entities(
            client, "nauvis", "any", "[gps=0,0]", requesting_player="dlbattle"
        )
        self.assertEqual(result, "ERROR: empty response")

    def test_dispatch_production_cell_passes_fields_knobs_and_player(self):
        client = Mock()
        request = jimbo.parse_produce_decision(
            "PRODUCE|nauvis|electronic-circuit|[gps=-622,51,nauvis]|"
            "layout=belt-fed,lanes=1"
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
            knobs={
                "layout": "belt-fed",
                "rotation": "east",
                "lanes": 1,
                "tier": "fastest",
            },
        )

    def test_place_cell_full_success(self):
        client = self.produce_client(
            "ANCHOR:10,20,3,3,assembling-machine-3",
            "SUCCESS: [gps=10,20,nauvis] 3x3 processing-unit cell placed",
        )

        result = jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]", "dlbattle"
        )

        phase1 = client.run.call_args_list[1].args[0]
        self.assertIn("nauvis", phase1)
        self.assertIn("processing-unit", phase1)
        self.assertIn("explicit_ax=10", phase1)
        self.assertIn("explicit_ay=20", phase1)
        probe = client.run.call_args_list[0].args[0]
        self.assertTrue(probe.startswith("/silent-command "))
        self.assertIn('"processing-unit"', probe)
        self.assertIn("tile_width..':'..e.tile_height", probe)
        self.assertIn("SUCCESS", result)
        self.assertIn("[gps=10,20,nauvis]", result)

    def test_place_cell_probe_error_short_circuits_before_search(self):
        client = Mock()
        client.run.return_value = "ERROR: Recipe not found"

        result = jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]", "dlbattle"
        )

        self.assertEqual(result, "ERROR: Recipe not found")
        self.assertEqual(client.run.call_count, 1)

    def test_place_cell_probe_reports_no_compatible_machine(self):
        client = Mock()
        client.run.return_value = "CANDIDATES:"

        result = jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "", "dlbattle"
        )

        self.assertEqual(result, "ERROR: No compatible crafting machine")
        self.assertEqual(client.run.call_count, 1)

    def test_place_cell_looks_up_entity_dimensions(self):
        client = Mock()
        client.run.side_effect = [
            "CANDIDATES:em-plasity-building:5:5",
            "ANCHOR:10,20,5,5,em-plasity-building",
            "SUCCESS: [gps=10,20,nauvis] 5x5 processing-unit cell placed",
        ]

        result = jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]", "dlbattle"
        )

        phase1 = client.run.call_args_list[1].args[0]
        self.assertIn("e.tile_width", phase1)
        self.assertIn("e.tile_height", phase1)
        self.assertIn("local w=e.tile_width;local h=e.tile_height", phase1)
        self.assertIn("local dims=w..'x'..h;", phase1)
        self.assertIn("local dim_variants=VARIANTS[dims];", phase1)
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
        client.run.side_effect = [
            self.candidates_response(),
            (
                "ERROR: No suitable production-cell location within 128 tiles "
                "(last: No logistic network coverage)|TRACE:surface=nauvis "
                "origin=0.0:0.0 direction=any machines=1 anchors=4 "
                "structural=0 occupied=0 unplaceable=0 heat=0 logistics=4 "
                "construction=0 power=0 selected=none:0:0:none"
            ),
        ]
        result = jimbo.place_production_cell(
            client, "nauvis", "iron-plate", "", "dlbattle"
        )

        phase1 = client.run.call_args_list[1].args[0]
        self.assertIn("request_player.position", phase1)
        self.assertIn("game.forces.player.get_spawn_position(s)", phase1)
        self.assertIn("No suitable production-cell location within", result)
        self.assertNotIn("TRACE", result)
        self.assertEqual(client.run.call_count, 2)
        self.assertTrue(client.run.call_args.kwargs["retry"])

    def test_place_cell_uses_bounded_footprint_aware_location_search(self):
        client = Mock()
        client.run.side_effect = [
            self.candidates_response(),
            "ERROR: No suitable production-cell location within 128 tiles",
        ]

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
        client.run.side_effect = [
            self.candidates_response(),
            "ERROR: captured",
        ]

        jimbo.place_production_cell(
            client, "aquilo", "iron-gear-wheel", "standing:north", "dlbattle"
        )

        phase1 = client.run.call_args.args[0]
        self.assertIn("local fallback_result=nil", phase1)
        self.assertIn("local function anchor_result", phase1)
        self.assertIn("v.layout~='aquilo-compact'", phase1)
        self.assertIn(
            "table.insert(ordered,1,dim_variants[#dim_variants])", phase1
        )
        self.assertIn(
            "if heated and net and construction and powered then", phase1
        )
        self.assertIn("'strict')) ", phase1)
        self.assertIn("'fallback') ", phase1)
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
            self.candidates_response(),
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
        client.run.side_effect = [
            self.candidates_response(),
            (
                "ERROR: No structurally placeable candidate|TRACE:surface=aquilo "
                "origin=-29.1:0.0 direction=north machines=3 anchors=768 "
                "structural=0 occupied=700 unplaceable=68 heat=0 logistics=0 "
                "construction=0 power=0 selected=none:0:0:none"
            ),
        ]

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
        client.run.side_effect = [
            self.candidates_response(),
            (
                "ERROR: View-relative location requires the requesting player "
                "online on nauvis"
            ),
        ]

        result = jimbo.place_production_cell(
            client, "nauvis", "iron-plate", "north-east", "dlbattle"
        )

        phase1 = client.run.call_args_list[1].args[0]
        self.assertIn('local direction="north-east"', phase1)
        self.assertIn('local relative_location="view"', phase1)
        self.assertIn("not request_player.connected", phase1)
        self.assertIn("request_player.surface~=s", phase1)
        self.assertIn("direction=='north-east'", phase1)
        self.assertIn("View-relative location requires", result)

    def test_place_cell_distinguishes_remote_view_and_physical_position(self):
        view_client = Mock()
        view_client.run.side_effect = [
            self.candidates_response(),
            "ERROR: blocked",
        ]
        standing_client = Mock()
        standing_client.run.side_effect = [
            self.candidates_response(),
            "ERROR: blocked",
        ]

        jimbo.place_production_cell(
            view_client, "current", "iron-plate", "view", "dlbattle"
        )
        jimbo.place_production_cell(
            standing_client, "current", "iron-plate", "standing", "dlbattle"
        )

        view_phase1 = view_client.run.call_args_list[1].args[0]
        standing_phase1 = standing_client.run.call_args_list[1].args[0]
        self.assertIn(
            "s=request_player.physical_surface else s=request_player.surface",
            view_phase1,
        )
        self.assertIn("origin=request_player.position", view_phase1)
        self.assertIn("origin=request_player.physical_position", standing_phase1)
        self.assertIn("request_player.physical_surface~=s", standing_phase1)

    def test_place_cell_direction_uses_selected_view_or_standing_origin(self):
        view_client = Mock()
        view_client.run.side_effect = [
            self.candidates_response(),
            "ERROR: blocked",
        ]
        standing_client = Mock()
        standing_client.run.side_effect = [
            self.candidates_response(),
            "ERROR: blocked",
        ]

        jimbo.place_production_cell(
            view_client, "current", "iron-plate", "view:north", "dlbattle"
        )
        jimbo.place_production_cell(
            standing_client, "current", "iron-plate", "standing:north", "dlbattle"
        )

        view_phase1 = view_client.run.call_args_list[1].args[0]
        standing_phase1 = standing_client.run.call_args_list[1].args[0]
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
            self.candidates_response(),
            "ANCHOR:10,20,3,3,assembling-machine-3,,fulgora",
            "SUCCESS: placed",
        ]

        result = jimbo.place_production_cell(
            client, "current", "iron-plate", "view", "dlbattle"
        )

        phase2 = client.run.call_args_list[2].args[0]
        self.assertIn('local s=game.surfaces["fulgora"]', phase2)
        self.assertEqual(result, "SUCCESS: placed")

    def test_place_cell_requires_requesting_player(self):
        client = Mock()

        result = jimbo.place_production_cell(
            client, "nauvis", "electronic-circuit", "[gps=10,20,nauvis]"
        )

        self.assertEqual(result, "ERROR: Requesting player is required")
        client.run.assert_not_called()

    def test_place_cell_rejects_unknown_knobs_dict(self):
        client = Mock()

        result = jimbo.place_production_cell(
            client, "nauvis", "iron-plate", "", "dlbattle",
            knobs={"layout": "standard"},
        )

        self.assertEqual(result, "ERROR: Invalid production-cell options")
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
        client.run.side_effect = [
            self.candidates_response(),
            "ANCHOR:bad",
        ]

        result = jimbo.place_production_cell(
            client, "nauvis", "iron-plate", "[gps=10,20,nauvis]", "dlbattle"
        )

        self.assertEqual(result, "ERROR: Invalid location response")
        self.assertEqual(client.run.call_count, 2)

    def test_place_cell_rejects_fractional_anchor_response(self):
        client = Mock()
        client.run.side_effect = [
            self.candidates_response(),
            "ANCHOR:10.5,20,3,3,assembling-machine-3",
        ]

        result = jimbo.place_production_cell(
            client, "nauvis", "electronic-circuit",
            "[gps=10,20,nauvis]", "dlbattle",
        )

        self.assertEqual(result, "ERROR: Invalid location response")
        self.assertEqual(client.run.call_count, 2)

    def test_place_cell_rejects_unknown_layout_in_response(self):
        client = Mock()
        client.run.side_effect = [
            self.candidates_response(),
            (
                "ANCHOR:10,20,3,3,assembling-machine-3,,nauvis,"
                "mystery,strict"
            ),
        ]

        result = jimbo.place_production_cell(
            client, "nauvis", "electronic-circuit",
            "[gps=10,20,nauvis]", "dlbattle",
        )

        self.assertEqual(result, "ERROR: Invalid location response")
        self.assertEqual(client.run.call_count, 2)

    def test_place_cell_phase2_creates_all_ghosts(self):
        client = Mock()
        client.run.side_effect = [
            self.candidates_response(),
            "ANCHOR:10,20,3,3,assembling-machine-3",
            "SUCCESS: placed",
        ]

        jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]", "dlbattle"
        )

        phase2 = client.run.call_args_list[2].args[0]
        self.assertIn("entity-ghost", phase2)
        self.assertIn('"requester-chest"', phase2)
        self.assertIn('"passive-provider-chest"', phase2)
        self.assertIn('"inserter"', phase2)
        self.assertIn('"medium-electric-pole"', phase2)
        self.assertEqual(phase2.count('["d"]="west"'), 2)
        self.assertIn("inner_name=plan.name", phase2)
        self.assertNotIn("defines.direction.right", phase2)
        self.assertNotIn("defines.direction.left", phase2)
        self.assertIn("pcall", phase2)
        self.assertIn("actual_recipe=b.get_recipe()", phase2)
        self.assertIn("cell placed with", phase2)
        self.assertNotIn("] ..w", phase2)

    def test_place_cell_phase2_requester_filters(self):
        client = Mock()
        client.run.side_effect = [
            self.candidates_response(),
            "ANCHOR:10,20,3,3,assembling-machine-3",
            "SUCCESS: placed",
        ]

        jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]", "dlbattle"
        )

        phase2 = client.run.call_args_list[2].args[0]
        self.assertIn("get_logistic_sections", phase2)
        self.assertIn("req.copy_settings(b,player)", phase2)
        self.assertIn("filter.value.name==ing.name", phase2)
        self.assertIn("request filter missing for", phase2)
        self.assertIn(
            "inherent_issue('furnace has no recipe; requester chest filters "
            "need setting by hand')",
            phase2,
        )

    def test_place_cell_phase2_rollback_on_failure(self):
        client = Mock()
        client.run.side_effect = [
            self.candidates_response(),
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
            self.candidates_response(),
            "ANCHOR:10,20,3,3,assembling-machine-3",
            "SUCCESS: placed",
        ]

        jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]", "dlbattle"
        )

        phase2_call = client.run.call_args_list[2]
        self.assertFalse(phase2_call.kwargs.get("retry", False))

    def test_place_cell_resolves_compatible_machine_from_live_categories(self):
        client = Mock()
        client.run.side_effect = [
            self.candidates_response(),
            "ANCHOR:10,20,3,3,assembling-machine-3",
            "SUCCESS: placed",
        ]

        jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]", "dlbattle"
        )

        phase1 = client.run.call_args_list[1].args[0]
        self.assertIn("ipairs(r.categories)", phase1)
        self.assertIn("prototypes.get_entity_filtered", phase1)
        self.assertIn("filter='crafting-category'", phase1)
        self.assertIn("crafting_category=category", phase1)
        self.assertIn("a.get_crafting_speed('normal')", phase1)
        self.assertNotIn("r.category", phase1)
        self.assertNotIn("r.products[1]", phase1)

    def test_place_cell_tier_knob_changes_candidate_sort(self):
        client = Mock()
        client.run.side_effect = [
            self.candidates_response(),
            "ANCHOR:10,20,3,3,assembling-machine-3",
            "SUCCESS: placed",
        ]

        jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]",
            "dlbattle",
            knobs={
                "layout": "standard",
                "rotation": "east",
                "lanes": 1,
                "tier": "smallest",
            },
        )

        phase1 = client.run.call_args_list[1].args[0]
        self.assertIn('if "smallest"==\'smallest\' then', phase1)
        self.assertIn("if aa~=ab then return aa<ab end;", phase1)

    def test_place_cell_checks_power_supply_radius(self):
        client = Mock()
        client.run.side_effect = [
            self.candidates_response(),
            "ANCHOR:10,20,3,3,assembling-machine-3",
            "SUCCESS: placed",
        ]

        jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]", "dlbattle"
        )

        phase1 = client.run.call_args_list[1].args[0]
        self.assertIn("get_supply_area_distance", phase1)
        self.assertIn("get_max_wire_distance", phase1)
        self.assertIn("pole.quality", phase1)
        self.assertIn("dx*dx+dy*dy<=reach*reach", phase1)

    def test_place_cell_searches_a_bounded_extension_pole_chain(self):
        client = Mock()
        client.run.side_effect = [
            self.candidates_response(),
            "ERROR: No live power connection within 2 extension poles",
        ]

        result = jimbo.place_production_cell(
            client, "nauvis", "electronic-circuit",
            "[gps=10,20,nauvis]", "dlbattle",
        )

        phase1 = client.run.call_args_list[1].args[0]
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
        self.assertEqual(client.run.call_count, 2)

    def test_place_cell_revalidates_and_creates_extension_poles(self):
        client = Mock()
        client.run.side_effect = [
            self.candidates_response(),
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

        phase2 = client.run.call_args_list[2].args[0]
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
        self.assertFalse(client.run.call_args_list[2].kwargs.get("retry", False))

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
                client.run.side_effect = [
                    self.candidates_response(),
                    (
                        "ANCHOR:10,20,3,3,assembling-machine-3,"
                        + plan
                    ),
                ]

                result = jimbo.place_production_cell(
                    client, "nauvis", "electronic-circuit",
                    "[gps=10,20,nauvis]", "dlbattle",
                )

                self.assertEqual(result, "ERROR: Invalid location response")
                self.assertEqual(client.run.call_count, 2)

    def test_place_cell_preflights_every_entity_in_both_phases(self):
        client = Mock()
        client.run.side_effect = [
            self.candidates_response(),
            "ANCHOR:10,20,3,3,assembling-machine-3",
            "SUCCESS: placed",
        ]

        jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]", "dlbattle"
        )

        phase1 = client.run.call_args_list[1].args[0]
        phase2 = client.run.call_args_list[2].args[0]
        for command in (phase1, phase2):
            self.assertIn("s.can_place_entity", command)
            self.assertIn("defines.build_check_type.script_ghost", command)
            self.assertIn("find_logistic_networks_by_construction_area", command)
            self.assertIn("requester-chest", command)
            self.assertIn("passive-provider-chest", command)
            self.assertIn("medium-electric-pole", command)

    def test_place_cell_builds_layouts_from_python_offset_tables(self):
        client = Mock()
        client.run.side_effect = [
            self.candidates_response(),
            "ANCHOR:10,20,3,3,assembling-machine-3",
            "SUCCESS: placed",
        ]

        jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]", "dlbattle"
        )

        phase1 = client.run.call_args_list[1].args[0]
        phase2 = client.run.call_args_list[2].args[0]
        self.assertIn('local VARIANTS={["3x3"]={', phase1)
        self.assertIn(
            "position={ax+off.x,ay+off.y}", phase1
        )
        self.assertIn("position={x+off.x,y+off.y}", phase2)
        self.assertIn("e.tile_width~=w or e.tile_height~=h", phase2)
        standard = jimbo._build_standard_variant(3, 3)
        self.assertEqual(standard["plans"][0], {
            "n": "building", "x": 1.5, "y": 1.5, "d": "", "r": "building",
        })
        self.assertEqual(
            standard["plans"][1],
            {"n": "requester-chest", "x": -1.5, "y": 1.5, "d": "", "r": "requester"},
        )

    def test_belt_fed_layout_geometry_east_single_lane(self):
        variant = jimbo._build_belt_fed_variant(3, 3, 1)

        self.assertEqual(variant["layout"], "belt-fed")
        self.assertTrue(variant["pole"])
        self.assertFalse(variant["req"])
        self.assertEqual(variant["area"], [-2, -2, 5, 6])

        by_name = {}
        for plan in variant["plans"]:
            by_name.setdefault(plan["n"], []).append(plan)

        self.assertEqual(by_name["building"][0]["x"], 1.5)
        self.assertEqual(by_name["building"][0]["y"], 1.5)

        output_inserter = by_name["inserter"][0]
        self.assertEqual(output_inserter["x"], 1.5)
        self.assertEqual(output_inserter["y"], -0.5)
        self.assertEqual(output_inserter["d"], "north")

        input_inserter = by_name["long-handed-inserter"][0]
        self.assertEqual(input_inserter["x"], 1.5)
        self.assertEqual(input_inserter["y"], 3.5)
        self.assertEqual(input_inserter["d"], "north")

        pole = by_name["medium-electric-pole"][0]
        self.assertEqual(pole["x"], 3.5)
        self.assertEqual(pole["y"], 4.5)

        output_belts = by_name["transport-belt"][:7]
        input_belts = by_name["transport-belt"][7:]
        self.assertEqual(
            [(belt["x"], belt["y"]) for belt in output_belts],
            [(x, -1.5) for x in (-1.5, -0.5, 0.5, 1.5, 2.5, 3.5, 4.5)],
        )
        self.assertEqual(
            {(belt["d"]) for belt in output_belts}, {"east"}
        )
        self.assertEqual(
            [(belt["x"], belt["y"]) for belt in input_belts],
            [(x, 5.5) for x in (-1.5, -0.5, 0.5, 1.5, 2.5, 3.5, 4.5)],
        )

    def test_belt_fed_layout_lane_count_knob_adds_outer_lanes(self):
        variant = jimbo._build_belt_fed_variant(3, 3, 2)

        belts = [plan for plan in variant["plans"] if plan["n"] == "transport-belt"]
        rows = sorted({belt["y"] for belt in belts})
        self.assertEqual(rows, [-2.5, -1.5, 5.5, 6.5])
        self.assertEqual(len(belts), 28)
        self.assertEqual(variant["area"], [-2, -3, 5, 7])

    def test_belt_fed_layout_aligns_even_width_machines(self):
        variant = jimbo._build_belt_fed_variant(2, 2, 1)

        belts = [plan for plan in variant["plans"] if plan["n"] == "transport-belt"]
        self.assertEqual(len(belts), 12)
        xs = sorted({belt["x"] for belt in belts})
        self.assertEqual(xs, [-1.5, -0.5, 0.5, 1.5, 2.5, 3.5])

        inserter = next(
            plan for plan in variant["plans"] if plan["n"] == "inserter"
        )
        long_handed = next(
            plan for plan in variant["plans"]
            if plan["n"] == "long-handed-inserter"
        )
        self.assertEqual(inserter["x"], 1.5)
        self.assertEqual(long_handed["x"], 1.5)
        self.assertEqual(
            {plan["x"] for plan in (inserter, long_handed)},
            {1.5},
        )

    def test_belt_fed_rotation_knob_rotates_offsets_and_directions(self):
        east = jimbo._build_belt_fed_variant(3, 3, 1)

        south = jimbo._rotate_variant(east, 1, 3, 3)
        south_plans = {id(plan): plan for plan in south["plans"]}
        building = next(
            plan for plan in south["plans"] if plan["r"] == "building"
        )
        self.assertEqual((building["x"], building["y"]), (1.5, 1.5))
        out_inserter = next(
            plan for plan in south["plans"]
            if plan["n"] == "inserter" and plan["y"] == 1.5
        )
        self.assertEqual(out_inserter["x"], 3.5)
        self.assertEqual(out_inserter["d"], "east")
        belts = [plan for plan in south["plans"] if plan["n"] == "transport-belt"]
        self.assertEqual({belt["d"] for belt in belts}, {"south"})
        self.assertEqual({belt["x"] for belt in belts}, {4.5, -2.5})
        self.assertEqual(south["area"], [-3, -2, 5, 5])

        west = jimbo._rotate_variant(east, 2, 3, 3)
        west_out = next(
            plan for plan in west["plans"]
            if plan["n"] == "inserter"
        )
        self.assertEqual((west_out["x"], west_out["y"]), (1.5, 3.5))
        self.assertEqual(west_out["d"], "south")
        west_lh = next(
            plan for plan in west["plans"]
            if plan["n"] == "long-handed-inserter"
        )
        self.assertEqual((west_lh["x"], west_lh["y"]), (1.5, -0.5))
        self.assertEqual(
            {belt["d"] for belt in west["plans"] if belt["n"] == "transport-belt"},
            {"west"},
        )

        north = jimbo.build_requested_cell_variants(
            {
                "layout": "belt-fed",
                "rotation": "north",
                "lanes": 1,
                "tier": "fastest",
            },
            3,
            3,
        )[0]
        north_lh = next(
            plan for plan in north["plans"]
            if plan["n"] == "long-handed-inserter"
        )
        self.assertEqual((north_lh["x"], north_lh["y"]), (3.5, 1.5))
        self.assertEqual(north_lh["d"], "west")

    def test_requested_variants_append_aquilo_compact_for_heat_fallback(self):
        variants = jimbo.build_requested_cell_variants(
            jimbo.default_production_cell_knobs(), 3, 3
        )

        self.assertEqual(
            [variant["layout"] for variant in variants],
            ["standard", "aquilo-compact"],
        )
        compact = variants[1]
        self.assertFalse(compact["pole"])
        self.assertTrue(compact["req"])
        self.assertEqual(compact["area"], [0, 0, 3, 5])
        directions = [plan["d"] for plan in compact["plans"]]
        self.assertEqual(directions.count("south"), 1)
        self.assertEqual(directions.count("north"), 1)

    def test_summarize_cell_plans_groups_repeated_names(self):
        belt_fed = jimbo._build_belt_fed_variant(3, 3, 1)
        self.assertEqual(
            jimbo.summarize_cell_plans(belt_fed, "assembling-machine-3"),
            (
                "assembling-machine-3, inserter, 7 transport-belt, "
                "long-handed-inserter, medium-electric-pole, 7 transport-belt"
            ),
        )
        standard = jimbo._build_standard_variant(3, 3)
        self.assertEqual(
            jimbo.summarize_cell_plans(standard, "assembling-machine-3"),
            (
                "assembling-machine-3, requester-chest, "
                "passive-provider-chest, 2 inserter, medium-electric-pole"
            ),
        )

    def test_place_cell_belt_fed_mutation_skips_requester_settings(self):
        client = Mock()
        client.run.side_effect = [
            self.candidates_response(),
            "ANCHOR:10,20,3,3,assembling-machine-3,,nauvis,belt-fed,strict",
            "SUCCESS: placed",
        ]

        result = jimbo.place_production_cell(
            client, "nauvis", "iron-gear-wheel", "[gps=10,20,nauvis]",
            "dlbattle",
            knobs={
                "layout": "belt-fed",
                "rotation": "east",
                "lanes": 1,
                "tier": "fastest",
            },
        )

        phase2 = client.run.call_args_list[2].args[0]
        self.assertIn('local layout="belt-fed"', phase2)
        self.assertIn('"transport-belt"', phase2)
        self.assertIn('"long-handed-inserter"', phase2)
        self.assertNotIn("copy_settings", phase2)
        self.assertNotIn("requester-chest", phase2)
        self.assertNotIn("furnace has no recipe", phase2)
        self.assertIn(
            "cell placed with assembling-machine-3, inserter, "
            "7 transport-belt, long-handed-inserter, medium-electric-pole, "
            "7 transport-belt",
            phase2,
        )
        self.assertEqual(result, "SUCCESS: placed")

    def test_place_cell_rejects_fluid_recipes_before_location_checks(self):
        client = Mock()
        client.run.return_value = "ERROR: Fluid recipes are not supported"

        result = jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]", "dlbattle"
        )

        probe = client.run.call_args.args[0]
        self.assertIn("ingredient.type=='fluid'", probe)
        self.assertIn("product.type=='fluid'", probe)
        self.assertEqual(result, "ERROR: Fluid recipes are not supported")
        self.assertEqual(client.run.call_count, 1)

    def test_place_cell_handles_one_sided_surface_conditions(self):
        client = Mock()
        client.run.return_value = "ERROR: Recipe is not supported on nauvis"

        jimbo.place_production_cell(
            client, "nauvis", "electronic-circuit",
            "[gps=10,20,nauvis]", "dlbattle",
        )

        probe = client.run.call_args.args[0]
        self.assertIn("condition.min and value<condition.min", probe)
        self.assertIn("condition.max and value>condition.max", probe)

    def test_place_cell_requires_live_heat_for_freezable_aquilo_components(self):
        client = Mock()
        client.run.side_effect = [
            self.candidates_response(),
            (
                "ERROR: No suitable production-cell location within 128 tiles "
                "(last: No heat coverage for assembling-machine-3)"
            ),
        ]

        result = jimbo.place_production_cell(
            client, "aquilo", "electronic-circuit", "[gps=10,20,aquilo]",
            "dlbattle",
        )

        phase1 = client.run.call_args_list[1].args[0]
        self.assertIn(
            "local requires_heat=s.planet and s.planet.name=='aquilo'", phase1
        )
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
        self.assertEqual(client.run.call_count, 2)

    def test_place_cell_rechecks_aquilo_heat_before_mutation(self):
        client = Mock()
        client.run.side_effect = [
            self.candidates_response(),
            "ANCHOR:10,20,3,3,assembling-machine-3,,aquilo",
            "ERROR: no heat coverage for inserter",
        ]

        result = jimbo.place_production_cell(
            client, "aquilo", "electronic-circuit", "[gps=10,20,aquilo]",
            "dlbattle",
        )

        phase2 = client.run.call_args_list[2].args[0]
        self.assertIn(
            "local requires_heat=s.planet and s.planet.name=='aquilo'", phase2
        )
        self.assertIn("p.heating_energy<=0", phase2)
        self.assertIn("source.prototype.heating_radius", phase2)
        self.assertIn("source.temperature>=30", phase2)
        self.assertIn("plan_overlaps_heat_source(plan)", phase2)
        self.assertIn("local count=count_blockers(area)", phase2)
        self.assertIn(
            "support_issue('no heat coverage for '..plan.key)", phase2
        )
        self.assertIn("local allow_support_warnings=false", phase2)
        self.assertEqual(result, "ERROR: no heat coverage for inserter")
        self.assertFalse(client.run.call_args_list[2].kwargs.get("retry", False))

    def test_place_cell_fallback_places_with_verified_support_warnings(self):
        client = Mock()
        client.run.side_effect = [
            self.candidates_response(),
            (
                "ANCHOR:-34,-5,3,3,assembling-machine-3,,aquilo,"
                "aquilo-compact,fallback"
            ),
            (
                "SUCCESS: [gps=-34,-5,aquilo] 3x3 iron-gear-wheel aquilo-compact "
                "cell placed with assembling-machine-3, requester-chest, "
                "passive-provider-chest, 2 inserter; WARNING: "
                "no heat coverage for inserter"
            ),
        ]

        result = jimbo.place_production_cell(
            client, "current", "iron-gear-wheel", "standing:north", "dlbattle"
        )

        phase2 = client.run.call_args_list[2].args[0]
        self.assertIn("local allow_support_warnings=true", phase2)
        self.assertIn("local warnings={};local warning_seen={}", phase2)
        self.assertIn("local function support_issue(text)", phase2)
        self.assertIn(
            "support_issue('no heat coverage for '..plan.key)", phase2
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
        self.assertIn("error('cannot place '..plan.key)", phase2)
        self.assertIn("building recipe was not set", phase2)
        self.assertIn("request filter missing for", phase2)
        self.assertIn(
            "'; WARNING: '..table.concat(warnings,', ')", phase2
        )
        self.assertIn("SUCCESS", result)
        self.assertIn("WARNING", result)
        self.assertFalse(client.run.call_args_list[2].kwargs.get("retry", False))

    def test_place_cell_uses_compact_aquilo_ring_layout(self):
        client = Mock()
        client.run.side_effect = [
            self.candidates_response(),
            "ANCHOR:-21,-8,3,3,assembling-machine-3,,aquilo,aquilo-compact",
            "SUCCESS: compact cell placed",
        ]

        result = jimbo.place_production_cell(
            client, "aquilo", "pumpjack", "[gps=-21,-8,aquilo]", "dlbattle"
        )

        phase1 = client.run.call_args_list[1].args[0]
        phase2 = client.run.call_args_list[2].args[0]
        self.assertIn("if requires_heat then step_x=1;step_y=1 end", phase1)
        self.assertIn('"aquilo-compact"', phase1)
        self.assertIn('["x"]=0.5', phase1)
        self.assertIn('["y"]=4.5', phase1)
        self.assertIn('["d"]="south"', phase1)
        self.assertIn('["d"]="north"', phase1)
        self.assertIn("powered=plan_has_live_power{position=building}", phase1)
        self.assertIn("if not plan_has_live_power{position=pos} then", phase1)
        self.assertIn('local layout="aquilo-compact"', phase2)
        self.assertIn("compact layout cannot use extension poles", phase2)
        self.assertIn("no existing power coverage for compact cell", phase2)
        self.assertIn("error('layout has no planned pole') end;", phase2)
        self.assertEqual(result, "SUCCESS: compact cell placed")
        self.assertFalse(client.run.call_args_list[2].kwargs.get("retry", False))

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
                client.run.side_effect = [
                    self.candidates_response(),
                    response,
                ]

                result = jimbo.place_production_cell(
                    client, "aquilo", "pumpjack", "[gps=10,20,aquilo]",
                    "dlbattle",
                )

                self.assertEqual(result, "ERROR: Invalid location response")
                self.assertEqual(client.run.call_count, 2)

    def test_place_cell_rechecks_occupancy_before_mutation(self):
        client = Mock()
        client.run.side_effect = [
            self.candidates_response(),
            "ANCHOR:10,20,3,3,assembling-machine-3",
            "ERROR: 1 entities appeared in area",
        ]

        result = jimbo.place_production_cell(
            client, "nauvis", "electronic-circuit", "[gps=10,20,nauvis]",
            "dlbattle",
        )

        phase2 = client.run.call_args_list[2].args[0]
        self.assertIn("s.count_entities_filtered{area=area}", phase2)
        self.assertIn("entities appeared in area", phase2)
        self.assertIn("ERROR", result)

    def test_place_cell_floors_gps_to_bottom_left_tile(self):
        client = Mock()
        client.run.side_effect = [
            self.candidates_response(),
            "ERROR: blocked",
        ]

        jimbo.place_production_cell(
            client, "nauvis", "electronic-circuit",
            "[gps=10.9,-20.1,nauvis]", "dlbattle",
        )

        phase1 = client.run.call_args.args[0]
        self.assertIn("local explicit_ax=10;local explicit_ay=-21", phase1)

    def test_place_cell_phase2_reports_incomplete_rollback(self):
        client = Mock()
        client.run.side_effect = [
            self.candidates_response(),
            "ANCHOR:10,20,3,3,assembling-machine-3",
            "ERROR: request filter failed; rollback incomplete: 1",
        ]

        result = jimbo.place_production_cell(
            client, "nauvis", "electronic-circuit",
            "[gps=10,20,nauvis]", "dlbattle",
        )

        phase2 = client.run.call_args_list[2].args[0]
        self.assertIn("for i=#cleanup,1,-1", phase2)
        self.assertIn("rollback incomplete", phase2)
        self.assertEqual(
            result, "ERROR: request filter failed; rollback incomplete: 1"
        )

class LookupTests(unittest.TestCase):
    def test_lookup_decision_parses_classes_and_question(self):
        decision = jimbo.parse_lookup_decision(
            "LOOKUP|LuaSpacePlatform, LuaLogisticSection|which platforms "
            "request gleba science"
        )
        self.assertEqual(
            decision,
            (
                ["LuaSpacePlatform", "LuaLogisticSection"],
                "which platforms request gleba science",
            ),
        )

    def test_lookup_decision_rejects_malformed_input(self):
        self.assertIsNone(jimbo.parse_lookup_decision("NONE"))
        self.assertIsNone(jimbo.parse_lookup_decision("LOOKUP|LuaSurface|"))
        self.assertIsNone(jimbo.parse_lookup_decision("LOOKUP||question"))
        self.assertIsNone(jimbo.parse_lookup_decision("LOOKUP|bad name!|q"))
        self.assertIsNone(jimbo.parse_lookup_decision("LOOKUP|a,b,c,d,e|q"))
        long_question = "x" * (jimbo.lookup_question_max_chars + 1)
        self.assertIsNone(
            jimbo.parse_lookup_decision(f"LOOKUP|LuaSurface|{long_question}")
        )

    def test_extract_api_slices_formats_members_and_skips_unknowns(self):
        doc = {
            "classes": [
                {
                    "name": "LuaThing",
                    "description": "A test thing.",
                    "attributes": [
                        {
                            "name": "valid",
                            "type": ["boolean"],
                            "description": "Is valid.",
                        }
                    ],
                    "methods": [
                        {
                            "name": "do_thing",
                            "parameters": [{"name": "target", "optional": True}],
                            "return_values": [{"type": ["string"]}],
                            "description": "Does a thing.",
                        }
                    ],
                }
            ],
            "concepts": [],
        }
        text = jimbo.extract_api_slices(doc, ["LuaThing", "LuaMissing"])
        self.assertIn("## LuaThing", text)
        self.assertIn("- valid :: boolean — Is valid.", text)
        self.assertIn("- do_thing(target?) -> string — Does a thing.", text)
        self.assertNotIn("LuaMissing", text)

    def test_extract_api_slices_respects_budget_with_truncation_marker(self):
        doc = {
            "classes": [
                {
                    "name": f"LuaBig{i}",
                    "methods": [
                        {"name": f"m{j}", "description": "x" * 60}
                        for j in range(50)
                    ],
                }
                for i in range(4)
            ]
        }
        with patch.object(jimbo, "lookup_slice_max_chars", 800):
            text = jimbo.extract_api_slices(
                doc, [f"LuaBig{i}" for i in range(4)]
            )
        self.assertLessEqual(len(text), 830)
        self.assertIn("[truncated]", text)

    def test_forbidden_lua_reason_blocks_bypasses_and_destruction(self):
        self.assertEqual(
            jimbo.forbidden_lua_reason("/silent-command game.player.insert{}"),
            "item grants",
        )
        self.assertEqual(
            jimbo.forbidden_lua_reason("/silent-command p.teleport{x=1}"),
            "teleporting players",
        )
        self.assertEqual(
            jimbo.forbidden_lua_reason("/silent-command e.destroy()"),
            "destructive changes",
        )
        self.assertEqual(
            jimbo.forbidden_lua_reason(
                '/silent-command s.create_entity{name="iron-chest"}'
            ),
            "spawning entities",
        )

    def test_forbidden_lua_reason_allows_ghosts_and_table_insert(self):
        self.assertIsNone(
            jimbo.forbidden_lua_reason(
                '/silent-command s.create_entity{name="entity-ghost", '
                'inner_name="iron-chest"}'
            )
        )
        self.assertIsNone(
            jimbo.forbidden_lua_reason(
                "/silent-command table.insert(out, e.name)"
            )
        )
        self.assertIsNone(
            jimbo.forbidden_lua_reason(
                "/silent-command rcon.print(#s.find_entities_filtered{})"
            )
        )

    def test_compose_lookup_command_strips_fences_takes_first_line(self):
        with patch.object(
            jimbo,
            "ask_ai",
            return_value="```lua\n/silent-command rcon.print(1)\n```",
        ) as ask:
            command = jimbo.compose_lookup_command("count chests", "SLICES")
        ask.assert_called_once()
        prompt = ask.call_args.args[0]
        self.assertIn('"count chests"', prompt)
        self.assertIn("SLICES", prompt)
        self.assertIn("Read-only inspection", prompt)
        self.assertIn("scope line", prompt)
        self.assertIn("EXCLUDED", prompt)
        self.assertEqual(command, "/silent-command rcon.print(1)")

    def test_compose_lookup_command_wraps_bare_lua_with_slash_prefix(self):
        bare = 'local c=0;rcon.print("scanned "..c)'
        with patch.object(jimbo, "ask_ai", return_value=bare):
            command = jimbo.compose_lookup_command("count chests", "SLICES")
        self.assertEqual(command, f"/silent-command {bare}")

    def test_compose_lookup_command_leaves_prefixed_command_untouched(self):
        prefixed = "/silent-command local c=0;rcon.print(c)"
        with patch.object(jimbo, "ask_ai", return_value=prefixed):
            command = jimbo.compose_lookup_command("count chests", "SLICES")
        self.assertEqual(command, prefixed)

    def test_compose_lookup_command_logs_raw_when_nothing_usable(self):
        with patch.object(jimbo, "ask_ai", return_value=""), patch(
            "builtins.print"
        ) as output:
            command = jimbo.compose_lookup_command("count chests", "SLICES")
        self.assertEqual(command, "")
        logged = "".join(str(call.args[0]) for call in output.call_args_list)
        self.assertIn("no command line", logged)

    def test_build_lookup_prompt_includes_essentials_when_present(self):
        with patch.object(jimbo, "lua_essentials_text", "SENTINEL SHEET"):
            prompt = jimbo.build_lookup_prompt("q", "SLICE TEXT")
        self.assertIn("SENTINEL SHEET", prompt)
        self.assertIn("SLICE TEXT", prompt)

    def test_reply_prompt_adds_scripted_lookup_hint(self):
        prompt = jimbo.build_reply_prompt(
            jimbo.server_owner,
            "Jimbo where are the iron plates going",
            "(none)",
            "RCON: scripted lookup",
            "42 plates in flight",
        )
        self.assertIn("scripted live query", prompt)
        self.assertIn("never add 'exactly' or 'all'", prompt)

    def test_classifier_prompt_guides_lookup_and_ghost_placement(self):
        prompt = jimbo.build_classification_prompt(
            jimbo.server_owner,
            "Jimbo where are my iron plates going",
            "(none)",
        )
        self.assertIn("LOOKUP|class-a,class-b|question", prompt)
        self.assertIn("ordinary convenience", prompt)
        self.assertIn("never as cheating", prompt)

    def test_classifier_routes_container_item_counts_to_lookup(self):
        prompt = jimbo.build_classification_prompt(
            jimbo.server_owner,
            "Jimbo how many iron plates exist on Nauvis?",
            "(none)",
        )

        self.assertIn(
            "asks to COUNT an item's quantity stored physically", prompt
        )
        self.assertIn(
            "grand total of an item that exists, use LOOKUP", prompt
        )
        self.assertIn(
            "how many iron-plate items are stored in chests on nauvis", prompt
        )
        self.assertIn(
            "what is available, on hand, or in stock in the player's "
            "LOGISTIC NETWORK",
            prompt,
        )


class CustomCellWorkerTests(unittest.TestCase):
    def facts(self):
        return {
            "surface": "nauvis",
            "origin": [100.0, 200.0],
            "machines": {"assembling-machine-3": {"w": 3, "h": 3}},
            "pole_supply": 7.0,
            "pole_wire": 9.0,
            "ingredients": ["1 copper-cable", "1 iron-gear-wheel"],
            "cliffs": [],
            "cliff_count": 0,
            "water_samples": [],
            "entities": [],
            "entity_count": 0,
        }

    def valid_proposal(self):
        return {
            "layout": "custom",
            "plans": [
                {"n": "assembling-machine-3", "x": 1.5, "y": 1.5,
                 "d": "", "r": "building"},
                {"n": "inserter", "x": 1.5, "y": -0.5, "d": "north",
                 "r": "inserter"},
                {"n": "transport-belt", "x": 0.5, "y": -1.5, "d": "east",
                 "r": "belt"},
                {"n": "transport-belt", "x": 1.5, "y": -1.5, "d": "east",
                 "r": "belt"},
                {"n": "medium-electric-pole", "x": 3.5, "y": 0.5, "d": "",
                 "r": "pole"},
            ],
            "area": [-1, -2, 4, 3],
            "pole": True,
            "req": False,
        }

    def test_validator_accepts_working_cell(self):
        errors = jimbo.validate_custom_cell_plan(
            self.valid_proposal(), self.facts()
        )
        self.assertEqual(errors, [])

    def test_validator_rejects_non_custom_layout(self):
        proposal = self.valid_proposal()
        proposal["layout"] = "standard"
        errors = jimbo.validate_custom_cell_plan(proposal, self.facts())
        self.assertTrue(
            any("layout" in e and "custom" in e for e in errors)
        )

    def test_validator_rejects_missing_building(self):
        proposal = self.valid_proposal()
        proposal["plans"] = proposal["plans"][1:]
        errors = jimbo.validate_custom_cell_plan(proposal, self.facts())
        self.assertTrue(
            any("exactly one" in e and "building" in e for e in errors)
        )

    def test_validator_rejects_unknown_machine(self):
        proposal = self.valid_proposal()
        proposal["plans"][0]["n"] = "assembling-machine-99"
        errors = jimbo.validate_custom_cell_plan(proposal, self.facts())
        self.assertTrue(
            any("not among the compatible machines" in e for e in errors)
        )

    def test_validator_rejects_isolated_belt(self):
        proposal = self.valid_proposal()
        proposal["plans"] = proposal["plans"][:3]
        errors = jimbo.validate_custom_cell_plan(proposal, self.facts())
        self.assertTrue(any("isolated" in e for e in errors))

    def test_validator_rejects_inserter_without_source(self):
        proposal = self.valid_proposal()
        for plan in proposal["plans"]:
            if plan["r"] == "inserter":
                plan["x"] = 4.5
                plan["y"] = 1.5
        errors = jimbo.validate_custom_cell_plan(proposal, self.facts())
        self.assertTrue(
            any("picks up" in e and "nothing stands" in e for e in errors)
        )

    def test_validator_rejects_pole_too_far(self):
        proposal = self.valid_proposal()
        for plan in proposal["plans"]:
            if plan["r"] == "pole":
                plan["x"] = 30.0
        errors = jimbo.validate_custom_cell_plan(proposal, self.facts())
        self.assertTrue(
            any("cannot power the machine" in e for e in errors)
        )

    def test_validator_rejects_overlapping_entities(self):
        proposal = self.valid_proposal()
        proposal["plans"][1]["x"] = 1.5
        proposal["plans"][1]["y"] = 1.5
        errors = jimbo.validate_custom_cell_plan(proposal, self.facts())
        self.assertTrue(any("overlaps" in e for e in errors))

    def test_validator_rejects_unknown_role(self):
        proposal = self.valid_proposal()
        proposal["plans"][1]["r"] = "rocket"
        errors = jimbo.validate_custom_cell_plan(proposal, self.facts())
        self.assertTrue(any("r must be one of" in e for e in errors))

    def test_validator_rejects_non_half_tile_centers(self):
        proposal = self.valid_proposal()
        proposal["plans"][1]["x"] = 1.3
        errors = jimbo.validate_custom_cell_plan(proposal, self.facts())
        self.assertTrue(any("half-tile centers" in e for e in errors))

    def test_parse_proposal_extracts_json_from_fences(self):
        proposal = self.valid_proposal()
        text = "Here you go:\n```json\n" + json.dumps(proposal) + "\n```"
        self.assertEqual(
            jimbo.parse_custom_plan_proposal(text), proposal
        )

    def test_parse_proposal_returns_none_on_garbage(self):
        self.assertIsNone(jimbo.parse_custom_plan_proposal("not json at all"))

    def test_produce_job_key_chunk_dedupe(self):
        key1 = jimbo.produce_job_key("nauvis", "iron-plate", "[gps=13.1,7.9]")
        key2 = jimbo.produce_job_key("nauvis", "iron-plate", "[gps=13.8,7.1]")
        self.assertEqual(key1, key2)
        self.assertIn("chunk:", key1)

    def test_produce_job_store_dedupe_reap(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(jimbo, "produce_jobs_dir", lambda: directory):
                job_id = jimbo.create_cell_job(
                    "nauvis", "iron-plate", "[gps=13,7]", {},
                    "dlbattle", self.facts(),
                )
                self.assertIsNotNone(job_id)
                self.assertEqual(
                    jimbo.find_active_cell_job(
                        jimbo.produce_job_key(
                            "nauvis", "iron-plate", "[gps=13,7]"
                        )
                    ),
                    job_id,
                )
                jimbo.update_job_status(job_id, pid=999999999)
                reaped = jimbo.reap_stale_cell_jobs()
                self.assertIn(job_id, reaped)
                status = jimbo._read_json(jimbo._job_paths(job_id)["status"])
                self.assertEqual(status["status"], "designed_failed")
                self.assertIn("interrupted", status["failure"])

    def test_run_worker_accepts_valid_proposal(self):
        proposal = self.valid_proposal()
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(jimbo, "produce_jobs_dir", lambda: directory):
                job_id = jimbo.create_cell_job(
                    "nauvis", "iron-plate", "[gps=13,7]", {},
                    "dlbattle", self.facts(),
                )
                job_path = jimbo._job_paths(job_id)["job"]
                with patch.object(jimbo, "ask_ai", return_value=json.dumps(proposal)):
                    rc = jimbo.run_produce_worker(job_path)
                self.assertEqual(rc, 0)
                result = jimbo._read_json(jimbo._job_paths(job_id)["result"])
                self.assertTrue(result["ok"])
                self.assertEqual(result["variant"]["layout"], "custom")
                status = jimbo._read_json(jimbo._job_paths(job_id)["status"])
                self.assertEqual(status["status"], "designed_ok")

    def test_run_worker_fails_after_iterations(self):
        def bad_ai(prompt):
            return json.dumps({"layout": "custom", "plans": [
                {"n": "assembling-machine-3", "x": 1.5, "y": 1.5,
                 "d": "", "r": "building"},
            ], "area": [0, 0, 3, 3], "pole": False, "req": False})

        with tempfile.TemporaryDirectory() as directory:
            with patch.object(jimbo, "produce_jobs_dir", lambda: directory):
                job_id = jimbo.create_cell_job(
                    "nauvis", "iron-plate", "[gps=13,7]", {},
                    "dlbattle", self.facts(),
                )
                job_path = jimbo._job_paths(job_id)["job"]
                with patch.object(
                    jimbo, "ask_ai", side_effect=bad_ai
                ):
                    rc = jimbo.run_produce_worker(job_path)
                self.assertEqual(rc, 1)
                result = jimbo._read_json(jimbo._job_paths(job_id)["result"])
                self.assertFalse(result["ok"])
                status = jimbo._read_json(jimbo._job_paths(job_id)["status"])
                self.assertEqual(status["status"], "designed_failed")
                self.assertIn("iterations", status["failure"])

    def test_run_worker_handles_non_json_response(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(jimbo, "produce_jobs_dir", lambda: directory):
                job_id = jimbo.create_cell_job(
                    "nauvis", "iron-plate", "[gps=13,7]", {},
                    "dlbattle", self.facts(),
                )
                job_path = jimbo._job_paths(job_id)["job"]
                with patch.object(
                    jimbo, "ask_ai", side_effect=lambda p: "I think you should..."
                ):
                    rc = jimbo.run_produce_worker(job_path)
                self.assertEqual(rc, 1)

    def test_normalize_custom_variant_recenters_building(self):
        variant = self.valid_proposal()
        normalized = jimbo._normalize_custom_variant(variant, 3, 3)
        building = next(p for p in normalized["plans"] if p["r"] == "building")
        self.assertEqual(building["x"], 1.5)
        self.assertEqual(building["y"], 1.5)
        self.assertEqual(normalized["layout"], "custom")

    def test_place_cell_with_custom_variant_stamps(self):
        client = Mock()
        client.run.side_effect = [
            "CANDIDATES:assembling-machine-3:3:3",
            "ANCHOR:10,20,3,3,assembling-machine-3,,nauvis,custom",
            "SUCCESS: [gps=10,20,nauvis] custom cell placed",
        ]
        knobs = jimbo.default_production_cell_knobs()
        knobs["layout"] = "custom"
        knobs["custom_variant"] = self.valid_proposal()
        result = jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]",
            "dlbattle", knobs=knobs,
        )
        self.assertTrue(result.startswith("SUCCESS"))
        phase2 = client.run.call_args_list[2].args[0]
        self.assertIn("cell placed with", phase2)

    def test_place_cell_custom_requires_known_machine(self):
        client = Mock()
        client.run.side_effect = [
            "CANDIDATES:assembling-machine-2:3:3",
        ]
        knobs = jimbo.default_production_cell_knobs()
        knobs["layout"] = "custom"
        knobs["custom_variant"] = self.valid_proposal()
        result = jimbo.place_production_cell(
            client, "nauvis", "processing-unit", "[gps=10,20,nauvis]",
            "dlbattle", knobs=knobs,
        )
        self.assertIn("not available", result)

    def test_report_finished_job_stamps_and_reports(self):
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(jimbo, "produce_jobs_dir", lambda: directory):
                job_id = jimbo.create_cell_job(
                    "nauvis", "iron-plate", "[gps=13,7]",
                    jimbo.default_production_cell_knobs(),
                    "dlbattle", self.facts(),
                )
                jimbo._write_json(
                    jimbo._job_paths(job_id)["result"],
                    {"ok": True, "variant": self.valid_proposal()},
                )
                jimbo.update_job_status(
                    job_id, status="designed_ok", reported=False
                )
                client = Mock()
                client.run.side_effect = [
                    "CANDIDATES:assembling-machine-3:3:3",
                    "ANCHOR:13,7,3,3,assembling-machine-3,,nauvis,custom",
                    "SUCCESS: [gps=13,7,nauvis] custom cell placed",
                ]
                with patch.object(
                    jimbo, "ask_ai",
                    return_value="Placed your custom iron-plate cell.",
                ):
                    with patch.object(
                        jimbo, "send_jimbo_lines",
                        return_value=(["Placed your custom iron-plate cell."], None),
                    ):
                        with patch.object(jimbo, "record_direct_reply"):
                            result = jimbo.report_finished_cell_job(
                                client, deque(), [], job_id
                            )
                self.assertTrue(result)
                status = jimbo._read_json(
                    jimbo._job_paths(job_id)["status"]
                )
                self.assertEqual(status["status"], "done_placed")
                self.assertTrue(status["reported"])

    def test_dispatch_custom_layout_spawns_job(self):
        knobs = jimbo.default_production_cell_knobs()
        knobs["layout"] = "custom"
        produce_request = ("nauvis", "iron-plate", "[gps=13,7]", knobs)
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(jimbo, "produce_jobs_dir", lambda: directory):
                with patch.object(
                    jimbo, "collect_custom_site_facts",
                    return_value=(self.facts(), None),
                ):
                    with patch.object(jimbo, "spawn_cell_worker") as spawn:
                        client = Mock()
                        result = jimbo.dispatch_production_cell(
                            client, produce_request, "dlbattle"
                        )
                spawn.assert_called_once()
        self.assertTrue(result.startswith("PENDING:"))

    def test_dispatch_exhausted_fallback_spawns_job(self):
        knobs = jimbo.default_production_cell_knobs()
        produce_request = ("nauvis", "iron-plate", "[gps=13,7]", knobs)
        with tempfile.TemporaryDirectory() as directory:
            with patch.object(jimbo, "produce_jobs_dir", lambda: directory):
                with patch.object(
                    jimbo, "collect_custom_site_facts",
                    return_value=(self.facts(), None),
                ):
                    with patch.object(jimbo, "spawn_cell_worker") as spawn:
                        with patch.object(
                            jimbo, "place_production_cell",
                            return_value=(
                                "ERROR: No suitable production-cell location "
                                "within search radius"
                            ),
                        ):
                            client = Mock()
                            result = jimbo.dispatch_production_cell(
                                client, produce_request, "dlbattle"
                            )
                spawn.assert_called_once()
        self.assertTrue(result.startswith("PENDING:"))

    def test_parse_job_status_decision(self):
        self.assertEqual(jimbo.parse_job_status_decision("JOBSTATUS"), ())
        self.assertIsNone(jimbo.parse_job_status_decision("NONE"))
        self.assertTrue(
            jimbo._is_recognized_classification("JOBSTATUS")
        )

    def test_classifier_prompt_mentions_custom_and_jobstatus(self):
        prompt = jimbo.build_classification_prompt(
            jimbo.server_owner, "Jimbo what are you building?", "(none)"
        )
        self.assertIn("layout=custom", prompt)
        self.assertIn("JOBSTATUS", prompt)

    def test_reply_prompt_pending_hint(self):
        prompt = jimbo.build_reply_prompt(
            jimbo.server_owner, "build me something", "(none)",
            "RCON: production cell", "PENDING: designing in the background",
        )
        self.assertIn("background", prompt)
        self.assertIn("do NOT claim the cell was placed", prompt)

    def test_reply_prompt_job_status_hint(self):
        prompt = jimbo.build_reply_prompt(
            jimbo.server_owner, "status?", "(none)",
            "RCON: produce job status", "(no custom cell designs in progress)",
        )
        self.assertIn("no custom designs running", prompt)

    def test_build_custom_plan_prompt_contains_facts(self):
        job = {
            "surface": "nauvis",
            "item": "iron-plate",
            "hint": "",
            "requesting_player": "dlbattle",
            "facts": self.facts(),
        }
        prompt = jimbo.build_custom_plan_prompt(job, [], 1)
        self.assertIn("assembling-machine-3 (3x3)", prompt)
        self.assertIn("copper-cable", prompt)
        self.assertIn("Medium pole supply radius: 7.0", prompt)


if __name__ == "__main__":
    unittest.main()
