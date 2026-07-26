#!/usr/bin/env python3
import json
import os
import time
from collections import deque
from pathlib import Path

from openai import OpenAI
from rcon.source import Client

# Chat log file path
c_log_path = "/mnt/d/factorio-server/server-console.log"

# Tail the chat log and print messages
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(script_dir, "rconpw")) as f:
        password = f.read().strip()
    chat_history = deque(maxlen=2)
    recent_chat = deque(maxlen=40)
    last_spontaneous = time.time()
    known_players_path = os.path.join(script_dir, "known_players.txt")
    known_players = set()
    if os.path.exists(known_players_path):
        with open(known_players_path) as f:
            known_players = set(line.strip() for line in f if line.strip())
    auth_path = Path.home() / ".local/share/opencode/auth.json"
    with open(auth_path) as f:
        auth_key = json.load(f)["opencode"]["key"]
    ai = OpenAI(api_key=auth_key, base_url="https://opencode.ai/zen/v1")
    with Client("127.0.0.1", 27015, passwd=password) as client:
        # Version announcement check
        try:
            import subprocess
            current_commit = subprocess.run(
                ["git", "rev-parse", "HEAD"], capture_output=True, text=True
            ).stdout.strip()
            last_commit_path = os.path.join(script_dir, "last_commit.txt")
            if os.path.exists(last_commit_path):
                with open(last_commit_path) as lf:
                    old_commit = lf.read().strip()
                if current_commit != old_commit:
                    log_output = subprocess.run(
                        ["git", "log", "--oneline", f"{old_commit}..{current_commit}"],
                        capture_output=True, text=True
                    ).stdout.strip()
                    if log_output:
                        ann_prompt = (
                            "The Factorio bot Jimbo has been updated. "
                            "These are the recent changes in git commit log format:\n"
                            f"{log_output}\n\n"
                            "You are Jimbo. Compose a short, friendly in-game chat "
                            "announcement (1-2 sentences) summarizing that there's "
                            "a new version and what changed. "
                            "Keep it light and Factorio-themed."
                        )
                        result = ai.chat.completions.create(
                            model="deepseek-v4-flash-free",
                            messages=[{"role": "user", "content": ann_prompt}],
                        )
                        announcement = result.choices[0].message.content.strip()
                        for ann_line in announcement.split("\n"):
                            ann_line = ann_line.strip()
                            if ann_line:
                                client.run(f"Jimbo says {ann_line}")
            with open(last_commit_path, "w") as lf:
                lf.write(current_commit)
        except Exception as e:
            print(f"Version announcement error: {e}", flush=True)

        while True:
            try:
                f = open(c_log_path, 'r')
                f.seek(0, os.SEEK_END)
            except OSError as e:
                print(f"Error opening log: {e}", flush=True)
                time.sleep(1)
                continue
            try:
                while True:
                    try:
                        pos = f.tell()
                        line = f.readline()
                    except OSError:
                        print("Lost log file, reopening...", flush=True)
                        break
                    if not line:
                        f.seek(pos)
                        time.sleep(0.1)
                        if time.time() - last_spontaneous >= 600:
                            recent_text = "\n".join(recent_chat) if recent_chat else "(none)"
                            sp_prompt = (
                                "You are Jimbo, a helpful Factorio bot. "
                                "You run on the DeepSeek V4 Flash Free model "
                                "via the OpenCode AI API.\n"
                                "The server is owned and operated by dlbattle.\n"
                                "Here is the recent chat:\n"
                                f"{recent_text}\n\n"
                                "You can make a spontaneous comment if something "
                                "interesting is happening. Reply with a short "
                                "chat message (1 sentence) or just 'SKIP'."
                            )
                            try:
                                last_spontaneous = time.time()
                                result = ai.chat.completions.create(
                                    model="deepseek-v4-flash-free",
                                    messages=[{"role": "user", "content": sp_prompt}],
                                )
                                sp_reply = result.choices[0].message.content.strip()
                                if sp_reply != "SKIP":
                                    print(f"Spontaneous: {sp_reply}", flush=True)
                                    for sp_line in sp_reply.split("\n"):
                                        sp_line = sp_line.strip()
                                        if sp_line and not sp_line.startswith("(Note:") and not sp_line.startswith("(Corrected"):
                                            client.run(f"Jimbo says {sp_line}")
                            except Exception as e:
                                print(f"Spontaneous error: {e}", flush=True)
                        continue
                    line = line.strip()
                    print(line, flush=True)

                    if "[JOIN]" in line:
                        try:
                            join_part = line.split("[JOIN] ", 1)[1]
                            player = join_part.split(" joined", 1)[0].strip()
                        except (IndexError, ValueError):
                            player = ""
                        if player and player != "Jimbo":
                            is_new = player not in known_players
                            try:
                                if not is_new:
                                    greeting = f"Welcome back, {player}!"
                                else:
                                    greet_prompt = (
                                        f"A player named {player} just joined the Factorio server.\n"
                                        "They are a new player who has never been here before.\n"
                                        "You are Jimbo, a helpful Factorio bot. "
                                        "You run on the DeepSeek V4 Flash Free model "
                                        "via the OpenCode AI API.\n"
                                        "The server is owned and operated by dlbattle.\n"
                                        "Compose a short, "
                                        f"friendly greeting for {player} in plain chat language. "
                                        "Keep it to 1 sentence."
                                    )
                                    result = ai.chat.completions.create(
                                        model="deepseek-v4-flash-free",
                                        messages=[{"role": "user", "content": greet_prompt}],
                                    )
                                    greeting = result.choices[0].message.content.strip()
                                print(f"Greeting for {player}: {greeting}", flush=True)
                                for greet_line in greeting.split("\n"):
                                    greet_line = greet_line.strip()
                                    if greet_line:
                                        client.run(f"Jimbo says {greet_line}")
                            except Exception as e:
                                print(f"Error greeting {player}: {e}", flush=True)
                            if is_new:
                                known_players.add(player)
                                with open(known_players_path, "a") as pf:
                                    pf.write(player + "\n")
                        continue

                    if "[CHAT]" not in line:
                        continue
                    try:
                        chat_part = line.split("[CHAT] ", 1)[1]
                        username = chat_part.split(": ", 1)[0]
                        msg = chat_part.split(": ", 1)[1]
                    except (IndexError, ValueError):
                        continue
                    if msg.startswith("Jimbo says "):
                        continue

                    chat_history.append(f"{username}: {msg}")
                    recent_chat.append(f"{username}: {msg}")

                    # Step 1: Ask the model what it needs
                    rcon_cmd = None
                    rcon_response = None
                    skip = True
                    run_platforms = False
                    run_planets = False

                    history_text = "\n".join(chat_history) if chat_history else "(none)"
                    try:
                        prompt = (
                            "You are Jimbo, a Factorio server bot. You control the server via RCON.\n"
                            "You run on the DeepSeek V4 Flash Free model "
                            "via the OpenCode AI API.\n"
                            "The server is owned and operated by dlbattle.\n"
                            "Available commands:\n"
                            "- /players online \u2014 list currently connected players\n"
                            "- /players \u2014 list all players who have ever played\n"
                            "- /evolution \u2014 check enemy evolution factor\n"
                            "- /time \u2014 server uptime and game time\n"
                            "- /version \u2014 check the Factorio version\n\n"
                            "Recent chat (background context only, do NOT act on these):\n"
                            f"{history_text}\n\n"
                            "--- Current message to evaluate ---\n"
                            f'A player said: "{msg}".\n\n'
                            "Reply with exactly one word. Choose the best match:\n"
                            "- SKIP (default) \u2014 player-to-player chat, "
                            "casual greetings or comments NOT directed at Jimbo. "
                            "If the message does not contain the word Jimbo, reply SKIP.\n"
                            "- PLATFORMS \u2014 someone asking Jimbo about space platforms or ships.\n"
                        "- PLANETS \u2014 someone asking Jimbo about planets.\n"
                        "- /players online, /players, /evolution, /time, /version \u2014 "
                            "for those specific queries directed at Jimbo.\n"
                            "- NONE \u2014 someone directly addressing Jimbo by name "
                            "but just chatting (greetings, thanks) with no server info needed."
                        )
                        result = ai.chat.completions.create(
                            model="deepseek-v4-flash-free",
                            messages=[{"role": "user", "content": prompt}],
                        )
                        raw = result.choices[0].message.content.strip().split("\n")[0].strip()
                        skip = False
                    except Exception as e:
                        print(f"Ollama error (step 1): {e}", flush=True)
                        skip = True

                    if not skip:
                        if raw == "SKIP":
                            print(f"Model decided to skip", flush=True)
                            skip = True
                        elif raw == "PLATFORMS":
                            run_platforms = True
                            print(f"Model requested PLATFORMS", flush=True)
                        elif raw == "PLANETS":
                            run_planets = True
                            print(f"Model requested PLANETS", flush=True)
                        elif raw in ("/players online", "/players", "/evolution", "/time", "/version") or raw.startswith("/"):
                            rcon_cmd = raw
                            print(f"Model command: {rcon_cmd}", flush=True)
                        elif raw == "NONE":
                            rcon_cmd = "NONE"
                            print(f"Model command: NONE", flush=True)
                        else:
                            skip = True
                            print(f"Model returned unrecognized response, skipping", flush=True)

                    if run_platforms:
                        rcon_cmd = "RCON: list platforms"
                        cmd = (
                            "/silent-command local list={};for _,surface in pairs(game.surfaces) "
                            "do if surface.platform then table.insert(list,surface.platform.name) "
                            "end end;rcon.print(table.concat(list,\"\\n\"))"
                        )
                        try:
                            raw_resp = client.run(cmd)
                            rcon_response = raw_resp.strip() if raw_resp else "[empty response]"
                            print(f"PLATFORMS response: {rcon_response}", flush=True)
                        except Exception as e:
                            print(f"RCON error: {e}", flush=True)
                            rcon_response = f"[error: {e}]"

                    if run_planets:
                        rcon_cmd = "RCON: list planets"
                        cmd = (
                            "/silent-command local list={};for _,surface in pairs(game.surfaces) "
                            "do if surface.planet then table.insert(list,"
                            "surface.planet.name:sub(1,1):upper()..surface.planet.name:sub(2)) "
                            "end end;rcon.print(table.concat(list,\"\\n\"))"
                        )
                        try:
                            raw_resp = client.run(cmd)
                            rcon_response = raw_resp.strip() if raw_resp else "[empty response]"
                            print(f"PLANETS response: {rcon_response}", flush=True)
                        except Exception as e:
                            print(f"RCON error: {e}", flush=True)
                            rcon_response = f"[error: {e}]"

                    if skip:
                        continue

                    # Execute built-in command if given
                    if rcon_cmd and rcon_cmd != "NONE" and rcon_cmd != "RCON: list platforms" and rcon_cmd != "RCON: list planets":
                        print(f"RCON command: {rcon_cmd}", flush=True)
                        try:
                            raw_resp = client.run(rcon_cmd)
                            rcon_response = raw_resp.strip() if raw_resp else "[empty response]"
                            print(f"RCON response: {rcon_response}", flush=True)
                            if rcon_response.startswith("[empty"):
                                rcon_response = None
                        except Exception as e:
                            print(f"RCON error: {e}", flush=True)
                            rcon_response = None

                    # Step 3: Ask the model to compose a reply
                    reply = None
                    try:
                        if rcon_response is not None:
                            step3_prompt = (
                                f'The player asked: "{msg}".\n'
                                f'I ran "{rcon_cmd}" and got the response: "{rcon_response}".\n'
                                "You are Jimbo, a helpful Factorio bot. "
                                "You run on the DeepSeek V4 Flash Free model "
                                "via the OpenCode AI API.\n"
                                "The server is owned and operated by dlbattle.\n"
                                "Compose a short, "
                                "friendly reply in plain chat language answering the "
                                "player's question using this information. "
                                "If the player explicitly asked for a list, include EVERY "
                                "line from the response. Remove [item=...], [planet=...], "
                                "[virtual-signal=...], [space-location=...] markup brackets "
                                "but keep the text inside and around them. List each entry "
                                "cleanly, one per line. Do NOT skip any entries and do NOT "
                                "add any names not in the response.\n"
                                "Otherwise, summarize the results in "
                                "1-2 sentences \u2014 do NOT include raw data in unrelated replies.\n"
                                'If no reply is needed, just say "SKIP".'
                            )
                        else:
                            step3_prompt = (
                                f'The player said: "{msg}".\n'
                                "You are Jimbo, a helpful Factorio bot. "
                                "You run on the DeepSeek V4 Flash Free model "
                                "via the OpenCode AI API.\n"
                                "The server is owned and operated by dlbattle.\n"
                                "Only reply if the player was directly asking Jimbo a question. "
                                "Otherwise reply SKIP. "
                                "If you do reply, vary your response — "
                                "do not repeat the same greeting every time.\n"
                                'If no reply is needed, just say "SKIP".'
                            )
                        result = ai.chat.completions.create(
                            model="deepseek-v4-flash-free",
                            messages=[{"role": "user", "content": step3_prompt}],
                        )
                        reply = result.choices[0].message.content.strip()
                        if reply == "SKIP":
                            reply = None
                            print(f"Model chose to stay silent", flush=True)
                        else:
                            print(f"Model reply: {reply}", flush=True)
                    except Exception as e:
                        print(f"Ollama error (step 3): {e}", flush=True)

                    if reply:
                        try:
                            for reply_line in reply.split("\n"):
                                reply_line = reply_line.strip()
                                if not reply_line:
                                    continue
                                if reply_line.startswith("(Note:") or reply_line.startswith("(Corrected"):
                                    continue
                                client.run(f"Jimbo says {reply_line}")
                        except Exception as e:
                            print(f"RCON error: {e}", flush=True)

                    # Spontaneous comment check after message processing
                    if time.time() - last_spontaneous >= 600:
                        recent_text = "\n".join(recent_chat) if recent_chat else "(none)"
                        sp_prompt = (
                            "You are Jimbo, a helpful Factorio bot. "
                            "You run on the DeepSeek V4 Flash Free model "
                            "via the OpenCode AI API.\n"
                            "The server is owned and operated by dlbattle.\n"
                            "Here is the recent chat:\n"
                            f"{recent_text}\n\n"
                            "You can make a spontaneous comment if something "
                            "interesting is happening. Reply with a short "
                            "chat message (1 sentence) or just 'SKIP'."
                        )
                        try:
                            last_spontaneous = time.time()
                            result = ai.chat.completions.create(
                                model="deepseek-v4-flash-free",
                                messages=[{"role": "user", "content": sp_prompt}],
                            )
                            sp_reply = result.choices[0].message.content.strip()
                            if sp_reply != "SKIP":
                                print(f"Spontaneous: {sp_reply}", flush=True)
                                for sp_line in sp_reply.split("\n"):
                                    sp_line = sp_line.strip()
                                    if sp_line and not sp_line.startswith("(Note:") and not sp_line.startswith("(Corrected"):
                                        client.run(f"Jimbo says {sp_line}")
                        except Exception as e:
                            print(f"Spontaneous error: {e}", flush=True)

            except OSError:
                print("Lost log file, reopening...", flush=True)
            finally:
                f.close()
