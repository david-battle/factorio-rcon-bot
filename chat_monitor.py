#!/usr/bin/env python3
import os
import time

from rcon.source import Client
from ollama import Client as OllamaClient

# Chat log file path
c_log_path = "/mnt/d/factorio-server/server-console.log"

# Tail the chat log and print messages
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(script_dir, "rconpw")) as f:
        password = f.read().strip()
    with Client("127.0.0.1", 27015, passwd=password) as client:
        with open(c_log_path, 'r') as f:
            f.seek(0, os.SEEK_END)
            while True:
                pos = f.tell()
                line = f.readline()
                if not line:
                    f.seek(pos)
                    time.sleep(0.1)
                else:
                    line = line.strip()
                    print(line, flush=True)
                    if "[CHAT]" not in line:
                        continue
                    try:
                        chat_part = line.split("[CHAT] ", 1)[1]
                        msg = chat_part.split(": ", 1)[1]
                    except (IndexError, ValueError):
                        continue
                    if msg.startswith("Jimbo says "):
                        continue

                    ollama = OllamaClient(host="http://127.0.0.1:11434")

                    # Step 1: Ask the model what it needs
                    rcon_cmd = None
                    rcon_response = None
                    skip = True
                    run_platforms = False
                    run_planets = False
                    try:
                        prompt = (
                            "You are Jimbo, a Factorio server bot. You control the server via RCON.\n"
                            "Available commands:\n"
                            "- /players online — list currently connected players\n"
                            "- /players — list all players who have ever played\n"
                            "- /evolution — check enemy evolution factor\n"
                            "- /time — server uptime and game time\n\n"
                            f'A player said: "{msg}".\n'
                            "If Jimbo isn't mentioned in any way, reply SKIP.\n"
                            "If they are, reply with exactly one of:\n"
                            "- NONE (just chat, no info needed)\n"
                            "- PLATFORMS (need list of space platforms/ships)\n"
                            "- PLANETS (need list of planets)\n"
                            "- one of the commands above"
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
                        else:
                            lower = msg.lower()
                            platform_words = ("platform", "ship", "station", "space")
                            planet_words = ("planet", "base", "moon")
                            if any(w in lower for w in platform_words):
                                run_platforms = True
                                print(f"Keyword match -> PLATFORMS", flush=True)
                            elif any(w in lower for w in planet_words):
                                run_planets = True
                                print(f"Keyword match -> PLANETS", flush=True)
                            else:
                                rcon_cmd = "NONE"
                                print(f"Model command: NONE", flush=True)

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
                            data_hint = ""
                            if rcon_cmd in ("RCON: list platforms", "RCON: list planets"):
                                data_hint = " Each line in the response is a separate entry. List every single one without skipping, merging, or reinterpreting any of them."
                            step3_prompt = (
                                f'The player asked: "{msg}".\n'
                                f'I ran "{rcon_cmd}" and got the response: "{rcon_response}".\n'
                                "You are Jimbo, a helpful Factorio bot. Compose a short, "
                                "friendly reply in plain chat language answering the "
                                f"player's question using this information.{data_hint}"
                            )
                        else:
                            step3_prompt = (
                                f'The player said: "{msg}".\n'
                                "You are Jimbo, a helpful Factorio bot. Compose a short, "
                                "friendly reply in plain chat language."
                            )
                        result = ollama.chat(
                            model="qwen2.5-32b-ctx32k",
                            messages=[{"role": "user", "content": step3_prompt}],
                        )
                        reply = result.message.content.strip()
                        print(f"Model reply: {reply}", flush=True)
                    except Exception as e:
                        print(f"Ollama error (step 3): {e}", flush=True)

                    if reply:
                        try:
                            client.run(f"Jimbo says {reply}")
                        except Exception as e:
                            print(f"RCON error: {e}", flush=True)