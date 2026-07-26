#!/usr/bin/env python3
import os
import time
from collections import deque

from rcon.source import Client
from ollama import Client as OllamaClient

# Chat log file path
c_log_path = "/mnt/d/factorio-server/server-console.log"

# Tail the chat log and print messages
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(script_dir, "rconpw")) as f:
        password = f.read().strip()
    chat_history = deque(maxlen=2)
    known_players_path = os.path.join(script_dir, "known_players.txt")
    known_players = set()
    if os.path.exists(known_players_path):
        with open(known_players_path) as f:
            known_players = set(line.strip() for line in f if line.strip())
    with Client("127.0.0.1", 27015, passwd=password) as client:
        ollama = OllamaClient(host="http://127.0.0.1:11434")
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
                                greet_prompt = (
                                    f"A player named {player} just joined the Factorio server.\n"
                                    f"They are {'a new player who has never been here before' if is_new else 'a returning player'}.\n"
                                    "You are Jimbo, a helpful Factorio bot. Compose a short, "
                                    f"friendly greeting for {player} in plain chat language. "
                                    "Keep it to 1-2 sentences."
                                )
                                result = ollama.chat(
                                    model="qwen2.5-32b-ctx32k",
                                    messages=[{"role": "user", "content": greet_prompt}],
                                )
                                greeting = result.message.content.strip()
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
                            "Available commands:\n"
                            "- /players online \u2014 list currently connected players\n"
                            "- /players \u2014 list all players who have ever played\n"
                            "- /evolution \u2014 check enemy evolution factor\n"
                            "- /time \u2014 server uptime and game time\n\n"
                            "Recent chat (background context only, do NOT act on these):\n"
                            f"{history_text}\n\n"
                            "--- Current message to evaluate ---\n"
                            f'A player said: "{msg}".\n\n'
                            "Reply with exactly one word. Choose the best match:\n"
                            "- PLATFORMS \u2014 if someone is asking about space platforms or ships.\n"
                            "- PLANETS \u2014 if someone is asking about planets.\n"
                            "- /players online, /players, /evolution, /time \u2014 for those specific queries.\n"
                            "- NONE \u2014 if directly addressing Jimbo but just chatting "
                            "(greetings, thanks, casual talk) with no server info needed.\n"
                            "- SKIP \u2014 if this is general conversation between other players, "
                            "or someone mentions Jimbo in passing without directly asking him "
                            "a question, giving an instruction, or requesting info."
                        )
                        result = ollama.chat(
                            model="qwen2.5-32b-ctx32k",
                            messages=[{"role": "user", "content": prompt}],
                        )
                        raw = result.message.content.strip().split("\n")[0].strip()
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
                        elif raw in ("/players online", "/players", "/evolution", "/time") or raw.startswith("/"):
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
                                "You are Jimbo, a helpful Factorio bot. Compose a short, "
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
                                "You are Jimbo, a helpful Factorio bot. Compose a short, "
                                "friendly reply in plain chat language.\n"
                                'If no reply is needed, just say "SKIP".'
                            )
                        result = ollama.chat(
                            model="qwen2.5-32b-ctx32k",
                            messages=[{"role": "user", "content": step3_prompt}],
                        )
                        reply = result.message.content.strip()
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
                                if reply_line:
                                    client.run(f"Jimbo says {reply_line}")
                        except Exception as e:
                            print(f"RCON error: {e}", flush=True)

            except OSError:
                print("Lost log file, reopening...", flush=True)
            finally:
                f.close()
