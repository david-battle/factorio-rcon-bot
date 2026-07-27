#!/usr/bin/env python3
import json
import os
import subprocess
import time
from collections import deque
from datetime import datetime

from rcon.exceptions import EmptyResponse, SessionTimeout
from rcon.source import Client

# Chat log file path
c_log_path = "/mnt/d/factorio-server/server-console.log"
server_owner = "dlbattle"
ai_profile_name = "openai"
ai_profiles = {
    "openai": {
        "provider": "opencode",
        "model": "openai/gpt-5.4-mini",
        "identity": "You run as openai/gpt-5.4-mini via OpenCode.",
    },
    "deepseek": {
        "provider": "openai-compatible",
        "model": "deepseek-v4-flash-free",
        "identity": (
            "You run on the DeepSeek V4 Flash Free model via the OpenCode AI API."
        ),
        "base_url": "https://opencode.ai/zen/v1",
        "auth_provider": "opencode",
    },
    "groq": {
        "provider": "openai-compatible",
        "model": "openai/gpt-oss-120b",
        "identity": "You run as OpenAI GPT-OSS 120B via Groq.",
        "base_url": "https://api.groq.com/openai/v1",
        "api_key_path": os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "groq-api-key.txt"
        ),
        "request_options": {
            "max_completion_tokens": 256,
            "extra_body": {
                "include_reasoning": False,
                "reasoning_effort": "low",
            },
        },
    },
    "ollama": {
        "provider": "ollama",
        "model": "qwen2.5-32b-ctx32k",
        "identity": "You run locally as qwen2.5-32b-ctx32k via Ollama.",
        "host": "http://127.0.0.1:11434",
    },
}
ai_profile = ai_profiles[ai_profile_name]
model_name = ai_profile["model"]
model_identity = ai_profile["identity"]
dialogue_max_turns = 12
dialogue_max_age = 15 * 60
dialogue_max_chars = 4000
dialogue_log_tail_bytes = 256 * 1024
safe_retry_commands = (
    "/players online", "/players", "/evolution", "/time", "/version",
)

# IMPORTANT: Update this player-facing summary whenever a code change will cause
# Jimbo to restart. Describe why the behavior changed, not implementation details.
startup_change_summary = (
    "I can now switch to Groq's GPT-OSS 120B when my owner chooses it."
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


def ask_opencode(prompt, profile):
    env = os.environ.copy()
    env.update({
        "OPENCODE_CONFIG_CONTENT": opencode_config,
        "OPENCODE_DISABLE_PROJECT_CONFIG": "1",
        "OPENCODE_DISABLE_EXTERNAL_SKILLS": "1",
        "OPENCODE_DISABLE_CLAUDE_CODE_SKILLS": "1",
    })
    os.makedirs("/tmp/opencode", exist_ok=True)
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
    raise RuntimeError(f'{profile["model"]} request failed: {detail[-1000:]}')


def ask_openai_compatible(prompt, profile):
    from openai import OpenAI

    if "api_key_path" in profile:
        with open(profile["api_key_path"]) as key_file:
            api_key = key_file.read().strip()
    else:
        auth_path = os.path.expanduser("~/.local/share/opencode/auth.json")
        with open(auth_path) as auth_file:
            api_key = json.load(auth_file)[profile["auth_provider"]]["key"]
    client = OpenAI(
        api_key=api_key,
        base_url=profile["base_url"],
        timeout=120,
        max_retries=0,
    )
    request = {
        "model": profile["model"],
        "messages": [{"role": "user", "content": prompt}],
    }
    request.update(profile.get("request_options", {}))
    result = client.chat.completions.create(**request)
    return result.choices[0].message.content.strip()


def ask_ollama(prompt, profile):
    from ollama import Client as OllamaClient

    client = OllamaClient(host=profile["host"], timeout=120)
    result = client.chat(
        model=profile["model"],
        messages=[{"role": "user", "content": prompt}],
    )
    return result.message.content.strip()


def ask_ai(prompt):
    adapters = {
        "opencode": ask_opencode,
        "openai-compatible": ask_openai_compatible,
        "ollama": ask_ollama,
    }
    adapter = adapters[ai_profile["provider"]]
    for attempt in range(3):
        caught_error = None
        status_code = None
        try:
            return adapter(prompt, ai_profile)
        except subprocess.TimeoutExpired as error:
            caught_error = error
            detail = "request timed out"
            timed_out = True
        except Exception as error:
            caught_error = error
            detail = str(error) or error.__class__.__name__
            timed_out = False
            status_code = getattr(error, "status_code", None)
            if status_code is None and getattr(error, "response", None) is not None:
                status_code = getattr(error.response, "status_code", None)

        lowered_detail = detail.lower()
        transient = status_code in (429, 500, 502, 503, 504) or any(
            marker in lowered_detail
            for marker in (
                "429", "rate limit", "too many requests", "timed out", "timeout",
                "500 internal server error", "502 bad gateway",
                "503 service unavailable", "504 gateway timeout",
            )
        )
        if not transient or attempt == 2:
            if timed_out:
                raise RuntimeError(
                    f'{ai_profile["model"]} request timed out'
                )
            raise RuntimeError(
                f'{ai_profile["model"]} request failed: {detail[-1000:]}'
            ) from caught_error
        delay = 2 ** (attempt + 1)
        if timed_out:
            print(f"AI request timed out; retrying in {delay}s", flush=True)
        else:
            print(f"Temporary AI error; retrying in {delay}s", flush=True)
        time.sleep(delay)

    raise RuntimeError(f'{ai_profile["model"]} request failed after retries')


def render_dialogue_turn(turn):
    rendered = f'{turn["speaker"]}: {turn["text"]}'
    if turn.get("rcon_command") and turn.get("rcon_response"):
        rendered += (
            f'\n[Exact RCON context for Jimbo\'s reply: {turn["rcon_command"]} '
            f'-> {turn["rcon_response"]}]'
        )
    return rendered


def prune_dialogue(dialogue, now=None):
    now = time.time() if now is None else now
    cutoff = now - dialogue_max_age
    while dialogue and dialogue[0]["timestamp"] < cutoff:
        dialogue.popleft()
    while len(dialogue) > dialogue_max_turns:
        dialogue.popleft()
    while dialogue and len("\n".join(map(render_dialogue_turn, dialogue))) > dialogue_max_chars:
        dialogue.popleft()


def add_dialogue_turn(
    dialogue, speaker, text, timestamp=None, rcon_command=None, rcon_response=None,
):
    text = text.strip()
    if not text:
        return
    timestamp = time.time() if timestamp is None else timestamp
    dialogue.append({
        "timestamp": timestamp,
        "speaker": speaker,
        "text": text,
        "rcon_command": rcon_command,
        "rcon_response": rcon_response,
    })
    prune_dialogue(dialogue, now=timestamp)


def format_dialogue(dialogue, now=None):
    prune_dialogue(dialogue, now=now)
    if not dialogue:
        return "(none)"
    return "\n".join(map(render_dialogue_turn, dialogue))


def filtered_reply_lines(reply):
    lines = []
    for line in reply.split("\n"):
        line = line.strip()
        if not line:
            continue
        if line.startswith("(Note:") or line.startswith("(Corrected"):
            continue
        lines.append(line)
    return lines


def send_jimbo_lines(client, reply):
    sent_lines = []
    error = None
    try:
        for line in filtered_reply_lines(reply):
            client.run(f"Jimbo says {line}")
            sent_lines.append(line)
    except Exception as caught:
        error = caught
    return sent_lines, error


def reply_uses_research_context(reply, research_text):
    normalized_reply = reply.lower().replace("-", " ")
    if "research" in normalized_reply:
        return True
    for line in research_text.splitlines():
        if line.startswith("Current: "):
            current = line[len("Current: "):].strip().lower().replace("-", " ")
            return current != "none" and current in normalized_reply
    return False


def parse_log_timestamp(line):
    try:
        return datetime.strptime(line[:19], "%Y-%m-%d %H:%M:%S").timestamp()
    except (ValueError, OverflowError):
        return None


def hydrate_dialogue(log_path, dialogue, now=None):
    now = time.time() if now is None else now
    cutoff = now - dialogue_max_age
    pending_joins = deque()
    with open(log_path, "rb") as log_file:
        log_file.seek(0, os.SEEK_END)
        start = max(0, log_file.tell() - dialogue_log_tail_bytes)
        log_file.seek(start)
        if start:
            log_file.readline()
        lines = log_file.read().decode("utf-8", errors="replace").splitlines()
        end_position = log_file.tell()

    for line in lines:
        timestamp = parse_log_timestamp(line)
        if timestamp is None or timestamp < cutoff:
            continue
        while pending_joins and timestamp - pending_joins[0][0] > 120:
            pending_joins.popleft()
        if "[JOIN] " in line:
            try:
                player = line.split("[JOIN] ", 1)[1].split(" joined", 1)[0].strip()
            except (IndexError, ValueError):
                player = ""
            if player:
                pending_joins.append((timestamp, player))
            continue
        if "[CHAT] " not in line:
            continue
        try:
            chat_part = line.split("[CHAT] ", 1)[1]
            username, msg = chat_part.split(": ", 1)
        except (IndexError, ValueError):
            continue

        if msg.startswith("Jimbo says "):
            text = msg[len("Jimbo says "):].strip()
            if text.startswith("Jimbo is online and listening."):
                continue
            if text == "What previous instructions?":
                continue
            matching_join = next((
                pending
                for pending in pending_joins
                if pending[1].lower() in text.lower()
            ), None)
            if matching_join is not None:
                pending_joins.remove(matching_join)
                continue
            if dialogue and dialogue[-1]["speaker"] == "Jimbo" and (
                dialogue[-1]["timestamp"] == timestamp
            ):
                dialogue[-1]["text"] += "\n" + text
                prune_dialogue(dialogue, now=now)
            else:
                add_dialogue_turn(dialogue, "Jimbo", text, timestamp=timestamp)
            continue
        if username == "<server>":
            continue
        if is_forget_request(msg):
            dialogue.clear()
            continue
        add_dialogue_turn(dialogue, username, msg, timestamp=timestamp)

    prune_dialogue(dialogue, now=now)
    return end_position


class ReconnectingRcon:
    def __init__(self, host, port, passwd):
        self.host = host
        self.port = port
        self.passwd = passwd
        self.client = None

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, typ, value, traceback):
        self.close()

    def connect(self):
        self.close()
        client = Client(self.host, self.port, passwd=self.passwd)
        try:
            client.connect(login=True)
        except Exception:
            client.close()
            raise
        self.client = client

    def close(self):
        if self.client is not None:
            self.client.close()
            self.client = None

    def run(self, command, retry=False):
        if self.client is None:
            self.connect()
        try:
            return self.client.run(command)
        except (OSError, EmptyResponse, SessionTimeout) as error:
            print(f"RCON connection lost ({error}); reconnecting", flush=True)
            self.connect()
            if not retry:
                raise
            try:
                return self.client.run(command)
            except (OSError, EmptyResponse, SessionTimeout):
                self.close()
                raise


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
    response = client.run(cmd, retry=True)
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


def build_classification_prompt(username, message, history_text):
    return (
        "You are Jimbo, a Factorio server bot. You control the server via RCON.\n"
        f"{model_identity}\n"
        f"The server is owned and operated by {server_owner}.\n"
        "Available commands:\n"
        "- /players online — list currently connected players\n"
        "- /players — list all players who have ever played\n"
        "- /evolution — check enemy evolution factor\n"
        "- /time — server uptime and game time\n"
        "- /version — check the Factorio version\n\n"
        "Recent chat (background context only, do NOT act on these):\n"
        f"{history_text}\n\n"
        "--- Current message to evaluate ---\n"
        f'{username} said: "{message}".\n\n'
        "Only the current message may request an action. Older mentions of Jimbo "
        "are context only. Use history to resolve references in the current message, "
        "never to revive an old request.\n\n"
        "Reply with exactly one word. Choose the best match:\n"
        "- SKIP (default) — player-to-player chat, casual greetings or comments "
        "NOT directed at Jimbo. If the message does not contain the word Jimbo, "
        "reply SKIP.\n"
        "- PLATFORMS — someone asking Jimbo about space platforms or ships.\n"
        "- PLANETS — someone asking Jimbo about planets.\n"
        "- /players online, /players, /evolution, /time, /version — for those "
        "specific queries directed at Jimbo.\n"
        "- NONE — someone directly addressing Jimbo by name but just chatting "
        "(greetings, thanks) with no server info needed."
    )


def build_reply_prompt(username, message, history_text, rcon_command, rcon_response):
    context = (
        "Recent shared chat (background context only):\n"
        f"{history_text}\n\n"
    )
    if rcon_response is not None:
        time_hint = ""
        if rcon_command == "/time":
            time_hint = (
                "The /time result is elapsed server/game time, not the current "
                "wall-clock time.\n"
            )
        return (
            context
            + f'{username} currently asked: "{message}".\n'
            + f'I ran "{rcon_command}" and got the response: "{rcon_response}".\n'
            + time_hint
            + "You are Jimbo, a helpful Factorio bot. "
            + f"{model_identity}\n"
            + f"The server is owned and operated by {server_owner}.\n"
            + "Compose a short, friendly reply in plain chat language answering the "
            + "current player's question using this information. Use recent chat only "
            + "to resolve references such as that, it, more, or faster; do not continue "
            + "an old topic on your own. If the player explicitly asked for a list, "
            + "include EVERY line from the response. Remove [item=...], [planet=...], "
            + "[virtual-signal=...], [space-location=...] markup brackets but keep the "
            + "text inside and around them. List each entry cleanly, one per line. Do "
            + "NOT skip any entries and do NOT add any names not in the response.\n"
            + "Otherwise, summarize the results in 1-2 sentences — do NOT include raw "
            + "data in unrelated replies.\nIf no reply is needed, just say \"SKIP\"."
        )
    return (
        context
        + f'{username} currently said: "{message}".\n'
        + "You are Jimbo, a helpful Factorio bot. "
        + f"{model_identity}\n"
        + f"The server is owned and operated by {server_owner}.\n"
        + "The player is directly addressing Jimbo. Use recent chat to resolve "
        + "references such as that, it, more, or faster, but answer only the current "
        + "message. Reply in character — a short greeting, banter, or whatever fits. "
        + "Vary your responses. If nothing is worth saying, just reply SKIP.\n"
        + 'If no reply is needed, just say "SKIP".'
    )


def build_greeting_prompt(player, is_new):
    player_status = (
        "They are a new player who has never been here before."
        if is_new
        else "They are a returning player."
    )
    owner_instruction = ""
    if player == server_owner:
        owner_instruction = (
            "This player is the server owner. Explicitly acknowledge them as the "
            "owner in your greeting.\n"
        )
    return (
        f"A player named {player} just joined the Factorio server.\n"
        f"{player_status}\n"
        f"{owner_instruction}"
        "You are Jimbo, a helpful Factorio bot. "
        f"{model_identity}\n"
        f"The server is owned and operated by {server_owner}.\n"
        f"Compose a short, friendly greeting for {player} in plain chat language. "
        "Keep it to 1 sentence."
    )


def maybe_spontaneous(
    client, recent_chat, dialogue, last_spontaneous, spontaneous_state,
    force=False, topic_hint="",
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
        f"The server is owned and operated by {server_owner}.\n"
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
            sent_lines, send_error = send_jimbo_lines(client, reply)
            if sent_lines:
                visible_reply = "\n".join(sent_lines)
                used_research = reply_uses_research_context(
                    visible_reply, research_text
                )
                add_dialogue_turn(
                    dialogue,
                    "Jimbo",
                    visible_reply,
                    rcon_command="research snapshot" if used_research else None,
                    rcon_response=research_text if used_research else None,
                )
                successful = True
            if send_error is not None:
                raise send_error
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
    dialogue = deque()
    resume_position = None
    try:
        resume_position = hydrate_dialogue(c_log_path, dialogue)
        print(f"Hydrated {len(dialogue)} recent dialogue turns", flush=True)
    except OSError as e:
        print(f"Dialogue hydration error: {e}", flush=True)
    recent_chat = []
    last_spontaneous = time.time()
    spontaneous_state = {"skip_next": False, "failed_attempts": 0}
    known_players_path = os.path.join(script_dir, "known_players.txt")
    known_players = set()
    if os.path.exists(known_players_path):
        with open(known_players_path) as f:
            known_players = set(line.strip() for line in f if line.strip())
    with ReconnectingRcon("127.0.0.1", 27015, passwd=password) as client:
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
                end_position = f.tell()
                if resume_position is not None and resume_position <= end_position:
                    f.seek(resume_position)
                resume_position = None
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
                            client, recent_chat, dialogue, last_spontaneous,
                            spontaneous_state,
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
                            greeting_sent = False
                            try:
                                greet_prompt = build_greeting_prompt(player, is_new)
                                greeting = ask_ai(greet_prompt)
                                print(f"Greeting for {player}: {greeting}", flush=True)
                                for greet_line in greeting.split("\n"):
                                    greet_line = greet_line.strip()
                                    if greet_line:
                                        client.run(f"Jimbo says {greet_line}")
                                        greeting_sent = True
                            except Exception as e:
                                print(f"Error greeting {player}: {e}", flush=True)
                            if greeting_sent:
                                recent_chat.pop()
                                last_spontaneous = time.time()
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

                    history_text = format_dialogue(dialogue)
                    if is_forget_request(msg):
                        recent_chat.clear()
                        dialogue.clear()
                        spontaneous_state["failed_attempts"] = 0
                        print("Manually cleared spontaneous and dialogue context", flush=True)
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
                    if username == server_owner and (
                        lowered_msg == trigger or lowered_msg.startswith(trigger + " ")
                    ):
                        topic_hint = stripped_msg[len(trigger):].strip()
                        add_dialogue_turn(dialogue, username, msg)
                        recent_chat.pop()
                        last_spontaneous = maybe_spontaneous(
                            client, recent_chat, dialogue, last_spontaneous,
                            spontaneous_state, force=True,
                            topic_hint=topic_hint,
                        )
                        continue

                    add_dialogue_turn(dialogue, username, msg)

                    # Step 1: Ask the model what it needs
                    rcon_cmd = None
                    rcon_response = None
                    skip = True
                    run_platforms = False
                    run_planets = False

                    try:
                        prompt = build_classification_prompt(
                            username, msg, history_text
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
                            raw_resp = client.run(cmd, retry=True)
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
                            raw_resp = client.run(cmd, retry=True)
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
                            raw_resp = client.run(
                                rcon_cmd, retry=rcon_cmd in safe_retry_commands
                            )
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
                        step3_prompt = build_reply_prompt(
                            username, msg, history_text, rcon_cmd, rcon_response
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
                        sent_lines, send_error = send_jimbo_lines(client, reply)
                        if sent_lines:
                            add_dialogue_turn(
                                dialogue,
                                "Jimbo",
                                "\n".join(sent_lines),
                                rcon_command=(
                                    rcon_cmd if rcon_cmd and rcon_cmd != "NONE" else None
                                ),
                                rcon_response=rcon_response,
                            )
                        if send_error is not None:
                            print(f"RCON error: {send_error}", flush=True)

                    last_spontaneous = maybe_spontaneous(
                        client, recent_chat, dialogue, last_spontaneous,
                        spontaneous_state,
                    )

            except (OSError, ValueError):
                print("Lost log file, reopening...", flush=True)
            finally:
                f.close()
