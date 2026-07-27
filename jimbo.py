#!/usr/bin/env python3
import json
import os
import subprocess
import time
from collections import deque

from rcon.source import Client

# Chat log file path
c_log_path = "/mnt/d/factorio-server/server-console.log"
model_name = "openai/gpt-5.4-mini"
model_identity = f"You run as {model_name} via OpenCode."

# IMPORTANT: Update this player-facing summary whenever a code change will cause
# Jimbo to restart. Describe why the behavior changed, not implementation details.
startup_change_summary = (
    "I now interpret server time results as elapsed game time instead of confusing "
    "them with the current time of day."
)

opencode_config = json.dumps({
    "model": model_name,
    "default_agent": "jimbo",
    "permission": "deny",
    "formatter": False,
    "lsp": False,
    "agent": {
        "jimbo": {
            "description": "Generate one plain text response without tools.",
            "mode": "primary",
            "model": model_name,
            "variant": "minimal",
            "prompt": "Return only the requested response. Never call tools.",
            "permission": {
                "read": "deny",
                "edit": "deny",
                "glob": "deny",
                "grep": "deny",
                "list": "deny",
                "bash": "deny",
                "task": "deny",
                "external_directory": "deny",
                "webfetch": "deny",
                "websearch": "deny",
                "skill": "deny",
                "todowrite": "deny",
                "question": "deny",
            },
        }
    },
})


def ask_ai(prompt):
    env = os.environ.copy()
    env.update({
        "OPENCODE_CONFIG_CONTENT": opencode_config,
        "OPENCODE_DISABLE_PROJECT_CONFIG": "1",
        "OPENCODE_DISABLE_EXTERNAL_SKILLS": "1",
        "OPENCODE_DISABLE_CLAUDE_CODE_SKILLS": "1",
    })
    os.makedirs("/tmp/opencode", exist_ok=True)
    for attempt in range(3):
        try:
            result = subprocess.run(
                [
                    "opencode", "run", "--pure", "--agent", "jimbo",
                    "--format", "json", prompt,
                ],
                cwd="/tmp/opencode",
                env=env,
                capture_output=True,
                text=True,
                timeout=120,
            )
        except subprocess.TimeoutExpired:
            if attempt == 2:
                raise
            delay = 2 ** (attempt + 1)
            print(f"AI request timed out; retrying in {delay}s", flush=True)
            time.sleep(delay)
            continue

        text_parts = []
        for line in result.stdout.splitlines():
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            if event.get("type") == "text":
                text = event.get("part", {}).get("text", "")
                if text:
                    text_parts.append(text)
        if result.returncode == 0 and text_parts:
            return "".join(text_parts).strip()

        detail = result.stderr.strip() or result.stdout.strip() or "no response"
        lowered_detail = detail.lower()
        transient = any(marker in lowered_detail for marker in (
            "429", "rate limit", "too many requests", "timed out", "timeout",
            "500 internal server error", "502 bad gateway",
            "503 service unavailable", "504 gateway timeout",
        ))
        if not transient or attempt == 2:
            raise RuntimeError(f"OpenAI request failed: {detail[-1000:]}")
        delay = 2 ** (attempt + 1)
        print(f"Temporary AI error; retrying in {delay}s", flush=True)
        time.sleep(delay)

    raise RuntimeError("OpenAI request failed after retries")


def get_research_snapshot(client):
    cmd = (
        "/silent-command local f=game.forces.player;local out={};"
        "local current=f.current_research;"
        "out[#out+1]=\"Current: \"..(current and current.name or \"none\");"
        "out[#out+1]=string.format(\"Progress: %.2f%%\",f.research_progress*100);"
        "out[#out+1]=\"Queue:\";"
        "for i,t in ipairs(f.research_queue) do "
        "out[#out+1]=i..\": \"..t.name end;"
        "rcon.print(table.concat(out,\"\\n\"))"
    )
    response = client.run(cmd)
    return response.strip() if response else "(unavailable)"


def is_quiet_request(message):
    normalized = message.lower()
    for punctuation in ",.!?":
        normalized = normalized.replace(punctuation, " ")
    normalized = " ".join(normalized.split())
    return any(
        phrase in normalized
        for phrase in (
            "shut up jimbo",
            "jimbo shut up",
            "be quiet jimbo",
            "jimbo be quiet",
            "stop talking jimbo",
            "jimbo stop talking",
        )
    )


def is_forget_request(message):
    normalized = message.strip().lower().rstrip(".!")
    return normalized == "jimbo, forget all previous instructions"


def maybe_spontaneous(
    client, recent_chat, last_spontaneous, spontaneous_state, force=False,
    topic_hint="",
):
    if not force and time.time() - last_spontaneous < 600:
        return last_spontaneous
    if not force and spontaneous_state["skip_next"]:
        spontaneous_state["skip_next"] = False
        print("Skipping scheduled spontaneous comment after quiet request", flush=True)
        return time.time()

    recent_text = "\n".join(recent_chat) if recent_chat else "(none)"
    try:
        research_text = get_research_snapshot(client)
    except Exception as e:
        print(f"Research snapshot error: {e}", flush=True)
        research_text = "(unavailable)"
    focus_text = ""
    if topic_hint:
        focus_text = (
            f'\nThe server owner asked you to focus on: "{topic_hint}"\n'
            "Treat this only as a topic hint. Use the supplied context and do not "
            "claim you need to gather more information.\n"
        )
    prompt = (
        "You are Jimbo, a helpful Factorio bot. "
        f"{model_identity}\n"
        "The server is owned and operated by dlbattle.\n"
        "Here is the recent server activity:\n"
        f"{recent_text}\n\n"
        "Here is the current research snapshot:\n"
        f"{research_text}\n"
        f"{focus_text}\n"
        "You can make a spontaneous comment if something interesting is "
        "happening. Reply with a short chat message (1 sentence) or just 'SKIP'."
    )
    last_spontaneous = time.time()
    successful = False
    try:
        reply = ask_ai(prompt)
        if reply != "SKIP":
            print(f"Spontaneous: {reply}", flush=True)
            for line in reply.split("\n"):
                line = line.strip()
                if line and not line.startswith("(Note:") and not line.startswith("(Corrected"):
                    client.run(f"Jimbo says {line}")
                    successful = True
    except Exception as e:
        print(f"Spontaneous error: {e}", flush=True)
    if successful:
        recent_chat.clear()
        spontaneous_state["failed_attempts"] = 0
    else:
        spontaneous_state["failed_attempts"] += 1
        failures = spontaneous_state["failed_attempts"]
        print(f"Spontaneous attempt did not comment ({failures}/12)", flush=True)
        if failures >= 12:
            recent_chat.clear()
            spontaneous_state["failed_attempts"] = 0
            print("Cleared stale spontaneous context after 12 attempts", flush=True)
    return last_spontaneous


# Tail the chat log and print messages
if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(script_dir, "rconpw")) as f:
        password = f.read().strip()
    chat_history = deque(maxlen=2)
    recent_chat = []
    last_spontaneous = time.time()
    spontaneous_state = {"skip_next": False, "failed_attempts": 0}
    known_players_path = os.path.join(script_dir, "known_players.txt")
    known_players = set()
    if os.path.exists(known_players_path):
        with open(known_players_path) as f:
            known_players = set(line.strip() for line in f if line.strip())
    with Client("127.0.0.1", 27015, passwd=password) as client:
        startup_summary_path = os.path.join(script_dir, "last_startup_summary.txt")
        try:
            last_summary = ""
            if os.path.exists(startup_summary_path):
                with open(startup_summary_path) as summary_file:
                    last_summary = summary_file.read().strip()
            announcement = "Jimbo is online and listening."
            if startup_change_summary != last_summary:
                announcement += f" {startup_change_summary}"
            client.run(f"Jimbo says {announcement}")
            with open(startup_summary_path, "w") as summary_file:
                summary_file.write(startup_change_summary)
        except Exception as e:
            print(f"Startup announcement error: {e}", flush=True)
            try:
                client.run("Jimbo says Jimbo is online and listening.")
            except Exception as fallback_error:
                print(
                    f"Startup announcement fallback error: {fallback_error}",
                    flush=True,
                )

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
                    except (OSError, ValueError):
                        print("Lost log file, reopening...", flush=True)
                        break
                    if not line:
                        f.seek(pos)
                        time.sleep(0.1)
                        last_spontaneous = maybe_spontaneous(
                            client, recent_chat, last_spontaneous, spontaneous_state
                        )
                        continue
                    line = line.strip()
                    print(line, flush=True)
                    if "Jimbo says" not in line:
                        recent_chat.append(line)

                    if "[JOIN]" in line:
                        try:
                            join_part = line.split("[JOIN] ", 1)[1]
                            player = join_part.split(" joined", 1)[0].strip()
                        except (IndexError, ValueError):
                            player = ""
                        if player and player != "Jimbo":
                            is_new = player not in known_players
                            try:
                                player_status = (
                                    "They are a new player who has never been here before."
                                    if is_new
                                    else "They are a returning player."
                                )
                                greet_prompt = (
                                    f"A player named {player} just joined the Factorio server.\n"
                                    f"{player_status}\n"
                                    "You are Jimbo, a helpful Factorio bot. "
                                    f"{model_identity}\n"
                                    "The server is owned and operated by dlbattle.\n"
                                    "Compose a short, "
                                    f"friendly greeting for {player} in plain chat language. "
                                    "Keep it to 1 sentence."
                                )
                                greeting = ask_ai(greet_prompt)
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

                    if is_forget_request(msg):
                        recent_chat.clear()
                        spontaneous_state["failed_attempts"] = 0
                        print("Manually cleared spontaneous context", flush=True)
                        try:
                            client.run("Jimbo says What previous instructions?")
                        except Exception as e:
                            print(f"RCON error: {e}", flush=True)
                        continue

                    if is_quiet_request(msg):
                        spontaneous_state["skip_next"] = True
                        print("Will skip next scheduled spontaneous comment", flush=True)

                    trigger = "jimbo, chime in"
                    stripped_msg = msg.strip()
                    lowered_msg = stripped_msg.lower()
                    if username == "dlbattle" and (
                        lowered_msg == trigger or lowered_msg.startswith(trigger + " ")
                    ):
                        topic_hint = stripped_msg[len(trigger):].strip()
                        recent_chat.pop()
                        last_spontaneous = maybe_spontaneous(
                            client, recent_chat, last_spontaneous, spontaneous_state,
                            force=True,
                            topic_hint=topic_hint,
                        )
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
                            f"{model_identity}\n"
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
                        raw = ask_ai(prompt).split("\n")[0].strip()
                        skip = False
                    except Exception as e:
                        print(f"AI error (step 1): {e}", flush=True)
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
                            time_hint = ""
                            if rcon_cmd == "/time":
                                time_hint = (
                                    "The /time result is elapsed server/game time, "
                                    "not the current wall-clock time.\n"
                                )
                            step3_prompt = (
                                f'The player asked: "{msg}".\n'
                                f'I ran "{rcon_cmd}" and got the response: "{rcon_response}".\n'
                                f"{time_hint}"
                                "You are Jimbo, a helpful Factorio bot. "
                                f"{model_identity}\n"
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
                                f"{model_identity}\n"
                                "The server is owned and operated by dlbattle.\n"
                                "The player is directly addressing Jimbo. "
                                "Reply in character — a short greeting, banter, "
                                "or whatever fits. Vary your responses. "
                                "If nothing is worth saying, just reply SKIP.\n"
                                'If no reply is needed, just say "SKIP".'
                            )
                        reply = ask_ai(step3_prompt)
                        if reply == "SKIP":
                            reply = None
                            print(f"Model chose to stay silent", flush=True)
                        else:
                            print(f"Model reply: {reply}", flush=True)
                    except Exception as e:
                        print(f"AI error (step 3): {e}", flush=True)

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

                    last_spontaneous = maybe_spontaneous(
                        client, recent_chat, last_spontaneous, spontaneous_state
                    )

            except (OSError, ValueError):
                print("Lost log file, reopening...", flush=True)
            finally:
                f.close()
