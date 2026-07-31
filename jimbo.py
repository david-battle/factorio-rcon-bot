#!/usr/bin/env python3
import json
import math
import os
import re
import subprocess
import tempfile
import time
from collections import deque
from datetime import datetime

from rcon.exceptions import EmptyResponse, SessionTimeout
from rcon.source import Client

# Chat log file path
c_log_path = "/mnt/d/factorio-server/server-console.log"
server_owner = "dlbattle"
ai_profile_name = "deepseek"
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
    "nemotron": {
        "provider": "openai-compatible",
        "model": "nvidia/nemotron-3-ultra-550b-a55b:free",
        "identity": "You run as Nemotron 3 Ultra (free) via OpenRouter.",
        "base_url": "https://openrouter.ai/api/v1",
        "api_key_path": os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "openrouter.key"
        ),
        "request_options": {
            "max_completion_tokens": 256,
        },
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
production_cell_max_extension_poles = 2
production_cell_directions = (
    "north", "north-east", "east", "south-east",
    "south", "south-west", "west", "north-west",
)
production_cell_relative_locations = ("view", "standing")
production_cell_search_max_radius = 128
production_cell_search_max_candidates = 256

# IMPORTANT: Update this player-facing summary whenever a code change will cause
# Jimbo to restart. Describe why the behavior changed, not implementation details.
startup_change_summary = (
    "When I find the entity with the highest damage or products finished, "
    "my reply now includes an exact clickable map ping at its location."
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
    os.makedirs("/tmp/opencode", exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="jimbo-opencode-") as temp_dir:
        env.update({
            "TMPDIR": temp_dir,
            "OPENCODE_CONFIG_CONTENT": opencode_config,
            "OPENCODE_DISABLE_PROJECT_CONFIG": "1",
            "OPENCODE_DISABLE_EXTERNAL_SKILLS": "1",
            "OPENCODE_DISABLE_CLAUDE_CODE_SKILLS": "1",
        })
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


def ensure_gps_ping(reply, rcon_command, rcon_response):
    if rcon_command != "RCON: top damage":
        return reply
    if not reply or "[gps=" in reply:
        return reply
    match = re.search(r"\[gps=[^\]\n]+\]", rcon_response or "")
    if not match:
        return reply
    return reply + f"\nRequested location: {match.group(0)}"


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


def record_direct_reply(
    dialogue, recent_chat, sent_lines, rcon_command=None, rcon_response=None,
):
    if not sent_lines:
        return
    add_dialogue_turn(
        dialogue,
        "Jimbo",
        "\n".join(sent_lines),
        rcon_command=rcon_command,
        rcon_response=rcon_response,
    )
    recent_chat.clear()


def report_request_failure(client, dialogue, recent_chat):
    reply = "I tried, but I couldn't complete that request."
    print(f"Request failure reply: {reply}", flush=True)
    sent_lines, error = send_jimbo_lines(client, reply)
    record_direct_reply(dialogue, recent_chat, sent_lines)
    if error is not None:
        print(f"RCON error sending request failure reply: {error}", flush=True)
    return sent_lines, error


def directly_addresses_jimbo(message):
    return re.search(r"\bjimbo\b", message, flags=re.IGNORECASE) is not None


def loosely_refers_to_jimbo(message):
    lowered = message.lower()
    target = "jimbo"
    n = len(target)
    for i in range(len(lowered) - n + 1):
        chunk = lowered[i:i + n]
        if sum(c1 != c2 for c1, c2 in zip(chunk, target)) <= 1:
            return True
    return False


def classify_current_message(username, message, history_text):
    prompt = build_classification_prompt(username, message, history_text)
    raw = ask_ai(prompt).split("\n")[0].strip()
    if raw == "SKIP" and directly_addresses_jimbo(message):
        print(
            "Classifier incorrectly skipped a direct Jimbo message; retrying",
            flush=True,
        )
        retry_prompt = (
            prompt
            + "\n\nYour previous answer was SKIP, but the current message directly "
            "addresses Jimbo. Under the rules above it must be classified as NONE, "
            "a structured request, or an executable slash command. Classify the "
            "current message again with exactly one line."
        )
        raw = ask_ai(retry_prompt).split("\n")[0].strip()
    return raw


def parse_logistics_decision(raw):
    if not raw.startswith("LOGISTICS|"):
        return None
    parts = raw.split("|")
    if len(parts) != 3:
        return None
    surface = parts[1].strip()
    items = list(dict.fromkeys(
        item.strip() for item in parts[2].split(",") if item.strip()
    ))

    def valid_name(name):
        return bool(name) and all(
            char.islower() or char.isdigit() or char in "-_" for char in name
        )

    if not valid_name(surface) or not items or len(items) > 20:
        return None
    if not all(valid_name(item) for item in items):
        return None
    return surface, items


def parse_tag_decision(raw):
    if not raw.startswith("TAG|"):
        return None
    parts = raw.split("|")
    if len(parts) not in (3, 4):
        return None
    surface = parts[1].strip()
    entity_type = parts[2].strip()

    def valid_name(name):
        return bool(name) and all(
            char.islower() or char.isdigit() or char in "-_" for char in name
        )

    label = parts[3].strip() if len(parts) == 4 and parts[3].strip() else ""
    if not valid_name(surface) or not valid_name(entity_type):
        return None
    return surface, entity_type, label


def run_tag_command(client, surface, entity_type, label):
    surface_lua = json.dumps(surface)
    entity_lua = json.dumps(entity_type)
    label_lua = json.dumps(label)
    cmd = (
        f"/silent-command local s=game.surfaces[{surface_lua}];"
        f"if not s then rcon.print('Surface not found') return end;"
        f"local et={entity_lua};"
        f"local label_text={label_lua};"
        f"local icon={{type='entity',name=et}};"
        f"local count=0;"
        f"local list=s.find_entities_filtered{{name=et}};"
        f"if #list==0 then list=s.find_entities_filtered{{type=et}} end;"
        f"for _,e in ipairs(list) do "
        f"if e.valid then "
        f"local tag_label=label_text~='' and label_text or e.name;"
        f"game.forces.player.add_chart_tag(s,{{position=e.position,"
        f"icon=icon,text=tag_label}});"
        f"count=count+1 end end;"
        f"if count==0 then rcon.print('No '..et..' found on '..s.name) "
        f"else rcon.print('Tagged '..count..' '..et..' on '..s.name) end"
    )
    response = client.run(cmd, retry=True)
    return response.strip() if response else "ERROR: empty response"


def parse_untag_decision(raw):
    if not raw.startswith("UNTAG|"):
        return None
    parts = raw.split("|")
    if len(parts) not in (3, 4):
        return None
    surface = parts[1].strip()
    entity_type = parts[2].strip()

    def valid_name(name):
        return bool(name) and all(
            char.islower() or char.isdigit() or char in "-_" for char in name
        )

    label = parts[3].strip() if len(parts) == 4 and parts[3].strip() else ""
    if not valid_name(surface) or not valid_name(entity_type):
        return None
    return surface, entity_type, label


def run_untag_command(client, surface, entity_type, label):
    surface_lua = json.dumps(surface)
    entity_lua = json.dumps(entity_type)
    label_lua = json.dumps(label)
    cmd = (
        f"/silent-command local s=game.surfaces[{surface_lua}];"
        f"if not s then rcon.print('Surface not found') return end;"
        f"local et={entity_lua};"
        f"local label_text={label_lua};"
        f"local pt=prototypes.entity[et];"
        f"local type_name=pt and pt.type or nil;"
        f"local tags=game.forces.player.find_chart_tags(s);"
        f"local count=0;"
        f"for _,tag in ipairs(tags) do "
        f"if (label_text~='' and tag.text==label_text) or "
        f"(label_text=='' and "
        f"(tag.text:lower():match('^'..et:lower():gsub('%-','%%-')) or "
        f"(type_name and "
        f"tag.text:lower():match('^'..type_name:lower():gsub('%-','%%-'))))) then "
        f"tag.destroy();"
        f"count=count+1 end end;"
        f"if count==0 then rcon.print('No matching tags found on '..s.name) "
        f"else rcon.print('Removed '..count..' tags from '..s.name) end"
    )
    response = client.run(cmd, retry=True)
    return response.strip() if response else "ERROR: empty response"


def parse_top_damage_decision(raw):
    if not raw.startswith("TOP_DAMAGE|"):
        return None
    parts = raw.split("|")
    if len(parts) < 3 or len(parts) > 3:
        return None
    surface = parts[1].strip()
    entity_type = parts[2].strip()

    def valid_name(name):
        return bool(name) and all(
            char.islower() or char.isdigit() or char in "-_" for char in name
        )

    if not valid_name(surface):
        return None
    if entity_type != "any" and not valid_name(entity_type):
        return None
    return surface, entity_type


def run_top_damage_command(client, surface, entity_type):
    surface_lua = json.dumps(surface)
    entity_lua = json.dumps(entity_type)
    cmd = (
        f"/silent-command local s=game.surfaces[{surface_lua}];"
        f"if not s then rcon.print('Surface not found') return end;"
        f"local et={entity_lua};"
        f"local best=nil;local bd=0;local stat_name='damage';local best_name='';"
        f"if et=='any' then "
        f"local types={{'rocket-silo','assembling-machine','furnace','mining-drill',"
        f"'chemical-plant','oil-refinery','centrifuge'}};"
        f"for _,t in ipairs(types) do "
        f"local list=s.find_entities_filtered{{type=t}};"
        f"for _,e in ipairs(list) do "
        f"local ok,v=pcall(function() return e.products_finished end);"
        f"local sn=t=='rocket-silo' and 'launches' or 'products';"
        f"if ok and v and v>bd then bd=v;best=e;stat_name=sn;best_name=e.name end end end;"
        f"else "
        f"local list=s.find_entities_filtered{{name=et}};"
        f"if #list==0 then list=s.find_entities_filtered{{type=et}} end;"
        f"for _,e in ipairs(list) do "
        f"local ok,v=pcall(function() return e.products_finished end);"
        f"if ok and v then "
        f"local sn=(e.type=='rocket-silo' or e.name=='rocket-silo') and 'launches' or 'products';"
        f"if v>bd then bd=v;best=e;stat_name=sn end "
        f"else "
        f"local ok2,v2=pcall(function() return e.damage_dealt end);"
        f"if ok2 and v2 and v2>bd then bd=v2;best=e;stat_name='damage' end "
        f"end end end;"
        f"if not best then rcon.print('No '..et..' found on '..s.name) return end;"
        f"local icon_name=best_name~='' and best_name or et;"
        f"game.forces.player.add_chart_tag(s,{{position=best.position,"
        f"icon={{type='entity',name=icon_name}},"
        f"text='Highest '..stat_name..': '..tostring(math.floor(bd))}});"
        f"rcon.print('Tagged '..et..' unit '..best.unit_number..' at '.."
        f"tostring(best.position.x)..','..tostring(best.position.y)"
        f"..' with '..tostring(math.floor(bd))..' '..stat_name"
        f"..' [gps='..tostring(best.position.x)..','..tostring(best.position.y)"
        f"..','..s.name..']')"
    )
    response = client.run(cmd, retry=True)
    return response.strip() if response else "ERROR: empty response"


def get_logistic_availability(client, surface, items):
    surface_lua = json.dumps(surface)
    items_lua = "{" + ",".join(json.dumps(item) for item in items) + "}"
    cmd = (
        f"/silent-command local scope={surface_lua};local surfaces={{}};"
        "if scope==\"all\" then for _,candidate in pairs(game.surfaces) do "
        "if candidate.planet then surfaces[#surfaces+1]=candidate end end else "
        "local s=game.surfaces[scope];if not s then rcon.print(\"Surface not "
        "found\") return end;surfaces[1]=s end;table.sort(surfaces,function(a,b) "
        "return a.name<b.name end);"
        f"local wanted={items_lua};local out={{}};for _,s in ipairs(surfaces) do "
        "local networks,ids,silos={},{},{};for _,e in pairs("
        "s.find_entities_filtered{type=\"roboport\",force=\"player\"}) do "
        "local n=e.logistic_network;if n and not networks[n.network_id] then "
        "networks[n.network_id]=n;ids[#ids+1]=n.network_id end end;"
        "for _,e in pairs(s.find_entities_filtered{type=\"rocket-silo\","
        "force=\"player\"}) do local n=s.find_logistic_network_by_position("
        "e.position,e.force);if n then silos[n.network_id]=true end end;"
        "table.sort(ids);for _,id in ipairs(ids) do local n=networks[id];local "
        "totals={};for _,name in ipairs(wanted) do totals[name]=0 end;for _,item "
        "in ipairs(n.get_contents()) do if totals[item.name]~=nil then "
        "totals[item.name]=totals[item.name]+math.max(0,item.count) end end;"
        "local counts={};for _,name in ipairs(wanted) do counts[#counts+1]="
        "name..\" available=\"..totals[name] end;out[#out+1]=string.format("
        "\"Surface %s, network %s (rocket silo: %s): %s\",s.name,id,"
        "silos[id] and \"yes\" or \"no\",table.concat(counts,\", \")) end end;"
        "rcon.print(#out>0 and table.concat(out,\"\\n\") or "
        "\"No player logistic networks found\")"
    )
    response = client.run(cmd, retry=True)
    return response.strip() if response else "(unavailable)"


def parse_production_cell_relative_hint(hint):
    if hint in production_cell_directions:
        return "view", hint
    if hint in production_cell_relative_locations:
        return hint, ""
    origin, separator, direction = hint.partition(":")
    if (
        separator
        and origin in production_cell_relative_locations
        and direction in production_cell_directions
    ):
        return origin, direction
    return None


def parse_produce_decision(raw):
    if not raw.startswith("PRODUCE|"):
        return None
    parts = raw.split("|")
    if len(parts) not in (3, 4):
        return None
    surface = parts[1].strip()
    item = parts[2].strip()
    hint = parts[3].strip() if len(parts) == 4 else ""

    def valid_name(name):
        return bool(name) and all(
            char.islower() or char.isdigit() or char in "-_" for char in name
        )

    if not valid_name(surface) or not valid_name(item):
        return None
    if hint:
        if parse_production_cell_relative_hint(hint) is not None:
            return surface, item, hint
        try:
            if not (hint.startswith("[gps=") and hint.endswith("]")):
                return None
            coords = [part.strip() for part in hint[5:-1].split(",")]
            if len(coords) not in (2, 3):
                return None
            x = float(coords[0])
            y = float(coords[1])
            if not math.isfinite(x) or not math.isfinite(y):
                return None
        except ValueError:
            return None
    return surface, item, hint


def place_production_cell(client, surface, item, hint="", requesting_player=""):
    if not requesting_player:
        return "ERROR: Requesting player is required"

    explicit = False
    ax = 0
    ay = 0
    direction = ""
    relative_location = ""
    relative_hint = parse_production_cell_relative_hint(hint)
    if relative_hint is not None:
        relative_location, direction = relative_hint
    elif hint:
        inner = hint[1:-1] if hint.startswith("[") and hint.endswith("]") else ""
        if not inner.startswith("gps="):
            return "ERROR: Invalid location hint"
        coords = [part.strip() for part in inner[4:].split(",")]
        if len(coords) not in (2, 3):
            return "ERROR: Invalid GPS location hint"
        try:
            ax_value = float(coords[0])
            ay_value = float(coords[1])
        except ValueError:
            return "ERROR: Invalid GPS location hint"
        if not math.isfinite(ax_value) or not math.isfinite(ay_value):
            return "ERROR: Invalid GPS location hint"
        if len(coords) == 3 and coords[2] != surface:
            return "ERROR: GPS surface does not match requested surface"
        explicit = True
        ax = math.floor(ax_value)
        ay = math.floor(ay_value)

    surface_lua = json.dumps(surface)
    item_lua = json.dumps(item)
    player_lua = json.dumps(requesting_player)
    direction_lua = json.dumps(direction)
    relative_location_lua = json.dumps(relative_location)
    explicit_lua = "true" if explicit else "false"

    phase1 = (
        f"/silent-command "
        f"local requested_surface={surface_lua};"
        f"local request_player=game.get_player({player_lua});"
        f"local relative_location={relative_location_lua};"
        f"local s=nil;"
        f"if requested_surface=='current' then "
        f"if not request_player or not request_player.connected then "
        f"rcon.print('ERROR: Current location requires the requesting player "
        f"online') return end;"
        f"if relative_location=='standing' then "
        f"s=request_player.physical_surface else s=request_player.surface end "
        f"else s=game.surfaces[requested_surface] end;"
        f"if not s then rcon.print('ERROR: Surface not found') return end;"
        f"local explicit={explicit_lua};"
        f"local explicit_ax={ax};local explicit_ay={ay};"
        f"local direction={direction_lua};"
        f"local origin=nil;"
        f"if not explicit then "
        f"if relative_location=='standing' then "
        f"if not request_player or not request_player.connected "
        f"or request_player.physical_surface~=s then "
        f"rcon.print('ERROR: Standing location requires the requesting player "
        f"online on '..s.name) return end;"
        f"origin=request_player.physical_position "
        f"elseif relative_location=='view' or direction~='' then "
        f"if not request_player or not request_player.connected "
        f"or request_player.surface~=s then "
        f"rcon.print('ERROR: View-relative location requires the requesting player "
        f"online on '..s.name) return end;"
        f"origin=request_player.position "
        f"elseif request_player and request_player.connected "
        f"and request_player.surface==s then "
        f"origin=request_player.position "
        f"else origin=game.forces.player.get_spawn_position(s) end end;"
        f"local origin_x=explicit and explicit_ax or origin.x;"
        f"local origin_y=explicit and explicit_ay or origin.y;"
        f"local r=prototypes.recipe[{item_lua}];"
        f"if not r then rcon.print('ERROR: Recipe not found') return end;"
        f"for _,ingredient in ipairs(r.ingredients) do "
        f"if ingredient.type=='fluid' then "
        f"rcon.print('ERROR: Fluid recipes are not supported') return end end;"
        f"for _,product in ipairs(r.products) do "
        f"if product.type=='fluid' then "
        f"rcon.print('ERROR: Fluid recipes are not supported') return end end;"
        f"if not s.ignore_surface_conditions then "
        f"for _,condition in ipairs(r.surface_conditions or {{}}) do "
        f"local value=s.get_property(condition.property);"
        f"if (condition.min and value<condition.min) "
        f"or (condition.max and value>condition.max) then "
        f"rcon.print('ERROR: Recipe is not supported on '..s.name) return end end end;"
        f"local force_recipe=game.forces.player.recipes[{item_lua}];"
        f"if not force_recipe or not force_recipe.enabled then "
        f"rcon.print('ERROR: Recipe is not unlocked') return end;"
        f"local by_name={{}};"
        f"for _,category in ipairs(r.categories) do "
        f"for name,e in pairs(prototypes.get_entity_filtered{{"
        f"{{filter='crafting-category',crafting_category=category}}"
        f"}}) do "
        f"if (e.type=='assembling-machine' or e.type=='furnace') "
        f"and e.items_to_place_this and #e.items_to_place_this>0 "
        f"and (not e.fixed_recipe or e.fixed_recipe.name==r.name) then "
        f"by_name[name]=e end end end;"
        f"local candidates={{}};"
        f"for _,e in pairs(by_name) do candidates[#candidates+1]=e end;"
        f"table.sort(candidates,function(a,b) "
        f"local sa=a.get_crafting_speed('normal');"
        f"local sb=b.get_crafting_speed('normal');"
        f"if sa~=sb then return sa>sb end;"
        f"local aa=a.tile_width*a.tile_height;"
        f"local ab=b.tile_width*b.tile_height;"
        f"if aa~=ab then return aa<ab end;"
        f"return a.name<b.name end);"
        f"if #candidates==0 then "
        f"rcon.print('ERROR: No compatible crafting machine') return end;"
        f"local max_search_radius={production_cell_search_max_radius};"
        f"local max_search_candidates={production_cell_search_max_candidates};"
        f"local function direction_ok(dx,dy) "
        f"if direction=='' then return true end;"
        f"if direction=='north' then return dy<0 and math.abs(dx)<=math.abs(dy) end;"
        f"if direction=='north-east' then return dx>0 and dy<0 end;"
        f"if direction=='east' then return dx>0 and math.abs(dy)<=math.abs(dx) end;"
        f"if direction=='south-east' then return dx>0 and dy>0 end;"
        f"if direction=='south' then return dy>0 and math.abs(dx)<=math.abs(dy) end;"
        f"if direction=='south-west' then return dx<0 and dy>0 end;"
        f"if direction=='west' then return dx<0 and math.abs(dy)<=math.abs(dx) end;"
        f"return dx<0 and dy<0 end;"
        f"local requires_heat=s.planet and s.planet.name=='aquilo';"
        f"local heat_source_types={{'heat-pipe','reactor','heat-interface'}};"
        f"local heat_source_type={{['heat-pipe']=true,['reactor']=true,"
        f"['heat-interface']=true}};"
        f"local max_heat_reach=0;"
        f"if requires_heat then "
        f"for _,source_type in ipairs(heat_source_types) do "
        f"for _,p in pairs(prototypes.get_entity_filtered{{"
        f"{{filter='type',type=source_type}}}}) do "
        f"local radius=p.heating_radius or 0;local box=p.collision_box;"
        f"local extent=math.max(math.abs(box.left_top.x),"
        f"math.abs(box.left_top.y),math.abs(box.right_bottom.x),"
        f"math.abs(box.right_bottom.y));"
        f"max_heat_reach=math.max(max_heat_reach,radius+extent) end end end;"
        f"local function plan_is_heated(plan) "
        f"if not requires_heat then return true end;"
        f"local p=prototypes.entity[plan.name];"
        f"if not p or p.heating_energy<=0 then return true end;"
        f"local box=p.collision_box;"
        f"local left=plan.position[1]+box.left_top.x;"
        f"local top=plan.position[2]+box.left_top.y;"
        f"local right=plan.position[1]+box.right_bottom.x;"
        f"local bottom=plan.position[2]+box.right_bottom.y;"
        f"local sources=s.find_entities_filtered{{"
        f"area={{{{left-max_heat_reach,top-max_heat_reach}},"
        f"{{right+max_heat_reach,bottom+max_heat_reach}}}},"
        f"type=heat_source_types}};"
        f"for _,source in ipairs(sources) do "
        f"local radius=source.prototype.heating_radius or 0;"
        f"local heat_box=source.bounding_box;"
        f"if radius>0 and source.temperature and source.temperature>=30 "
        f"and right>heat_box.left_top.x-radius "
        f"and left<heat_box.right_bottom.x+radius "
        f"and bottom>heat_box.left_top.y-radius "
        f"and top<heat_box.right_bottom.y+radius then return true end end;"
        f"return false end;"
        f"local function plan_overlaps_heat_source(plan) "
        f"if not requires_heat then return false end;"
        f"local p=prototypes.entity[plan.name];local box=p.collision_box;"
        f"local left=plan.position[1]+box.left_top.x;"
        f"local top=plan.position[2]+box.left_top.y;"
        f"local right=plan.position[1]+box.right_bottom.x;"
        f"local bottom=plan.position[2]+box.right_bottom.y;"
        f"for _,source in ipairs(s.find_entities_filtered{{"
        f"area={{{{left,top}},{{right,bottom}}}},type=heat_source_types}}) do "
        f"local heat_box=source.bounding_box;"
        f"if right>heat_box.left_top.x and left<heat_box.right_bottom.x "
        f"and bottom>heat_box.left_top.y and top<heat_box.right_bottom.y then "
        f"return true end end;return false end;"
        f"local function count_blockers(area) "
        f"if not requires_heat then "
        f"return s.count_entities_filtered{{area=area}} end;"
        f"local count=0;for _,existing in ipairs("
        f"s.find_entities_filtered{{area=area}}) do "
        f"if not heat_source_type[existing.type] then count=count+1 end end;"
        f"return count end;"
        f"local function plan_has_live_power(plan) "
        f"for _,pole in ipairs(s.find_entities_filtered{{type='electric-pole',"
        f"area={{{{plan.position[1]-64,plan.position[2]-64}},"
        f"{{plan.position[1]+64,plan.position[2]+64}}}},force='player'}}) do "
        f"if pole.electric_network then "
        f"local supply=pole.prototype.get_supply_area_distance(pole.quality);"
        f"if math.abs(pole.position.x-plan.position[1])<=supply "
        f"and math.abs(pole.position.y-plan.position[2])<=supply then "
        f"return true end end end;return false end;"
        f"local pole_proto=prototypes.entity['medium-electric-pole'];"
        f"if not pole_proto then "
        f"rcon.print('ERROR: medium-electric-pole not found') return end;"
        f"local trace={{anchors=0,structural=0,occupied=0,unplaceable=0,"
        f"heat=0,logistics=0,construction=0,power=0}};"
        f"local function trace_text(selection,ax,ay,layout) "
        f"return string.format('surface=%s origin=%.1f:%.1f direction=%s "
        f"machines=%d anchors=%d structural=%d occupied=%d unplaceable=%d "
        f"heat=%d logistics=%d construction=%d power=%d "
        f"selected=%s:%.0f:%.0f:%s',s.name,origin_x,origin_y,"
        f"direction=='' and 'any' or direction,#candidates,trace.anchors,"
        f"trace.structural,trace.occupied,trace.unplaceable,trace.heat,"
        f"trace.logistics,trace.construction,trace.power,selection,ax,ay,"
        f"layout) end;"
        f"local function anchor_result(ax,ay,w,h,en,chain,layout,mode) "
        f"local encoded={{}};for _,pos in ipairs(chain) do "
        f"encoded[#encoded+1]=string.format('%.1f:%.1f',pos[1],pos[2]) end;"
        f"return 'ANCHOR:'..ax..','..ay..','..w..','..h..','..en.."
        f"','..table.concat(encoded,';')..','..s.name..','..layout..','..mode.."
        f"'|TRACE:'..trace_text(mode,ax,ay,layout) end;"
        f"local fallback_result=nil;"
        f"local last_error='No suitable compatible crafting machine';"
        f"for _,e in ipairs(candidates) do "
        f"local en=e.name;local w=e.tile_width;local h=e.tile_height;"
        f"local anchors={{}};"
        f"if explicit then anchors[1]={{explicit_ax,explicit_ay}} else "
        f"local step_x=w+4;local step_y=h+1;"
        f"if requires_heat then step_x=1;step_y=1 end;"
        f"local base_x=math.floor(origin.x-w/2);"
        f"local base_y=math.floor(origin.y-h/2);"
        f"local max_ring=math.ceil(max_search_radius/math.min(step_x,step_y));"
        f"for ring=0,max_ring do "
        f"if #anchors>=max_search_candidates then break end;"
        f"for gy=-ring,ring do "
        f"if #anchors>=max_search_candidates then break end;"
        f"for gx=-ring,ring do "
        f"if #anchors>=max_search_candidates then break end;"
        f"if math.max(math.abs(gx),math.abs(gy))==ring then "
        f"local dx=gx*step_x;local dy=gy*step_y;"
        f"if math.max(math.abs(dx),math.abs(dy))<=max_search_radius "
        f"and direction_ok(dx,dy) then "
        f"anchors[#anchors+1]={{base_x+dx,base_y+dy}} end end end end end end;"
        f"for _,anchor in ipairs(anchors) do "
        f"trace.anchors=trace.anchors+1;"
        f"local ax=anchor[1];local ay=anchor[2];"
        f"local cx=ax+w/2;local cy=ay+h/2;"
        f"if requires_heat and w>=2 then "
        f"local compact_area={{{{ax,ay}},{{ax+w,ay+h+2}}}};"
        f"local compact_plans={{"
        f"{{name=en,position={{cx,cy}}}},"
        f"{{name='requester-chest',position={{ax+0.5,ay+h+1.5}}}},"
        f"{{name='passive-provider-chest',position={{ax+1.5,ay+h+1.5}}}},"
        f"{{name='inserter',position={{ax+0.5,ay+h+0.5}},"
        f"direction=defines.direction.south}},"
        f"{{name='inserter',position={{ax+1.5,ay+h+0.5}},"
        f"direction=defines.direction.north}}"
        f"}};"
        f"local compact_count=count_blockers(compact_area);"
        f"if compact_count>0 then "
        f"trace.occupied=trace.occupied+1;"
        f"last_error=compact_count..' entities in compact area' "
        f"else "
        f"local compact_placeable=true;local compact_blocked='';"
        f"for _,plan in ipairs(compact_plans) do "
        f"if plan_overlaps_heat_source(plan) or not "
        f"s.can_place_entity{{name=plan.name,position=plan.position,"
        f"direction=plan.direction,force='player',"
        f"build_check_type=defines.build_check_type.script_ghost}} then "
        f"compact_placeable=false;compact_blocked=plan.name;break end end;"
        f"local compact_heated=true;local compact_cold='';"
        f"if compact_placeable then for _,plan in ipairs(compact_plans) do "
        f"if not plan_is_heated(plan) then "
        f"compact_heated=false;compact_cold=plan.name;break end end end;"
        f"if not compact_placeable then "
        f"trace.unplaceable=trace.unplaceable+1;"
        f"last_error='Cannot place compact '..compact_blocked "
        f"else "
        f"trace.structural=trace.structural+1;"
        f"local compact_net=s.find_logistic_network_by_position("
        f"compact_plans[2].position,'player');"
        f"local compact_construction=true;"
        f"for _,plan in ipairs(compact_plans) do "
        f"if #s.find_logistic_networks_by_construction_area("
        f"plan.position,'player')==0 then "
        f"compact_construction=false break end end;"
        f"local compact_power=plan_has_live_power(compact_plans[1]) "
        f"and plan_has_live_power(compact_plans[4]) "
        f"and plan_has_live_power(compact_plans[5]);"
        f"if not compact_heated then trace.heat=trace.heat+1 end;"
        f"if not compact_net then trace.logistics=trace.logistics+1 end;"
        f"if not compact_construction then "
        f"trace.construction=trace.construction+1 end;"
        f"if not compact_power then trace.power=trace.power+1 end;"
        f"if compact_heated and compact_net and compact_construction "
        f"and compact_power then "
        f"rcon.print(anchor_result(ax,ay,w,h,en,{{}},"
        f"'aquilo-compact','strict')) return "
        f"else "
        f"if not compact_heated then "
        f"last_error='No heat coverage for compact '..compact_cold "
        f"elseif not compact_net then "
        f"last_error='No logistic network coverage for compact cell' "
        f"elseif not compact_construction then "
        f"last_error='No construction network coverage for compact cell' "
        f"else last_error='No existing power coverage for compact cell' end;"
        f"if not fallback_result then fallback_result=anchor_result("
        f"ax,ay,w,h,en,{{}},'aquilo-compact','fallback') end end end end end;"
        f"local row=ay+math.floor(h/2)+0.5;"
        f"local pole_pos={{ax+math.floor(w/2)+0.5,ay-0.5}};"
        f"local area={{{{ax-2,ay-1}},{{ax+w+2,ay+h}}}};"
        f"local count=count_blockers(area);"
        f"if count>0 then "
        f"trace.occupied=trace.occupied+1;"
        f"last_error=count..' entities in area' "
        f"else "
        f"local plans={{"
        f"{{name=en,position={{cx,cy}}}},"
        f"{{name='requester-chest',position={{ax-1.5,row}}}},"
        f"{{name='passive-provider-chest',position={{ax+w+1.5,row}}}},"
        f"{{name='inserter',position={{ax-0.5,row}},"
        f"direction=defines.direction.west}},"
        f"{{name='inserter',position={{ax+w+0.5,row}},"
        f"direction=defines.direction.west}},"
        f"{{name='medium-electric-pole',position=pole_pos}}"
        f"}};"
        f"local placeable=true;local blocked='';"
        f"for _,plan in ipairs(plans) do "
        f"if plan_overlaps_heat_source(plan) or not "
        f"s.can_place_entity{{name=plan.name,position=plan.position,"
        f"direction=plan.direction,force='player',"
        f"build_check_type=defines.build_check_type.script_ghost}} then "
        f"placeable=false;blocked=plan.name;break end end;"
        f"local heated=true;local cold='';"
        f"if placeable then for _,plan in ipairs(plans) do "
        f"if not plan_is_heated(plan) then "
        f"heated=false;cold=plan.name;break end end end;"
        f"if not placeable then "
        f"trace.unplaceable=trace.unplaceable+1;"
        f"last_error='Cannot place '..blocked "
        f"else "
        f"trace.structural=trace.structural+1;"
        f"local requester=plans[2].position;"
        f"local net=s.find_logistic_network_by_position(requester,'player');"
        f"local construction=true;"
        f"for _,plan in ipairs(plans) do "
        f"if #s.find_logistic_networks_by_construction_area("
        f"plan.position,'player')==0 then construction=false break end end;"
        f"local supply=pole_proto.get_supply_area_distance('normal');"
        f"local supplies=math.abs(cx-pole_pos[1])<=supply "
        f"and math.abs(cy-pole_pos[2])<=supply;"
        f"local new_wire=pole_proto.get_max_wire_distance('normal');"
        f"local max_extensions={production_cell_max_extension_poles};"
        f"local search_radius=(max_extensions+1)*new_wire;"
        f"local live={{}};"
        f"for _,pole in ipairs(s.find_entities_filtered{{type='electric-pole',"
        f"area={{{{pole_pos[1]-search_radius,pole_pos[2]-search_radius}},"
        f"{{pole_pos[1]+search_radius,pole_pos[2]+search_radius}}}},"
        f"force='player'}}) do "
        f"if pole.electric_network then live[#live+1]=pole end end;"
        f"table.sort(live,function(a,b) "
        f"local adx=a.position.x-pole_pos[1];"
        f"local ady=a.position.y-pole_pos[2];"
        f"local bdx=b.position.x-pole_pos[1];"
        f"local bdy=b.position.y-pole_pos[2];"
        f"local da=adx*adx+ady*ady;local db=bdx*bdx+bdy*bdy;"
        f"if da~=db then return da<db end;"
        f"if a.position.x~=b.position.x then "
        f"return a.position.x<b.position.x end;"
        f"return a.position.y<b.position.y end);"
        f"local function reaches_live(pos) "
        f"for _,pole in ipairs(live) do "
        f"local reach=math.min(new_wire,"
        f"pole.prototype.get_max_wire_distance(pole.quality));"
        f"local dx=pole.position.x-pos[1];"
        f"local dy=pole.position.y-pos[2];"
        f"if dx*dx+dy*dy<=reach*reach then return true end end;"
        f"return false end;"
        f"local function overlaps_cell(pos) "
        f"local left=pos[1]-0.5;local right=pos[1]+0.5;"
        f"local top=pos[2]-0.5;local bottom=pos[2]+0.5;"
        f"return not (right<=area[1][1] or left>=area[2][1] "
        f"or bottom<=area[1][2] or top>=area[2][2]) end;"
        f"local function valid_extension(pos) "
        f"if overlaps_cell(pos) then return false end;"
        f"local cell={{{{pos[1]-0.5,pos[2]-0.5}},"
        f"{{pos[1]+0.5,pos[2]+0.5}}}};"
        f"if s.count_entities_filtered{{area=cell}}>0 then return false end;"
        f"if not s.can_place_entity{{name='medium-electric-pole',position=pos,"
        f"force='player',"
        f"build_check_type=defines.build_check_type.script_ghost}} then "
        f"return false end;"
        f"return #s.find_logistic_networks_by_construction_area("
        f"pos,'player')>0 end;"
        f"local function key(pos) "
        f"return string.format('%.1f,%.1f',pos[1],pos[2]) end;"
        f"local function target_distance(pos) "
        f"local best=math.huge;for _,pole in ipairs(live) do "
        f"local dx=pole.position.x-pos[1];"
        f"local dy=pole.position.y-pos[2];"
        f"best=math.min(best,dx*dx+dy*dy) end;return best end;"
        f"local chain={{}};local connected=reaches_live(pole_pos);"
        f"if not connected and construction and supplies and #live>0 then "
        f"local frontier={{{{position=pole_pos,path={{}}}}}};"
        f"local seen={{[key(pole_pos)]=true}};"
        f"for depth=1,max_extensions do "
        f"local next_frontier={{}};"
        f"for _,state in ipairs(frontier) do "
        f"local candidates={{}};"
        f"local min_x=math.ceil(state.position[1]-new_wire-0.5);"
        f"local max_x=math.floor(state.position[1]+new_wire-0.5);"
        f"local min_y=math.ceil(state.position[2]-new_wire-0.5);"
        f"local max_y=math.floor(state.position[2]+new_wire-0.5);"
        f"for tile_x=min_x,max_x do for tile_y=min_y,max_y do "
        f"local pos={{tile_x+0.5,tile_y+0.5}};"
        f"local dx=pos[1]-state.position[1];"
        f"local dy=pos[2]-state.position[2];"
        f"local distance=dx*dx+dy*dy;local pos_key=key(pos);"
        f"if distance>0 and distance<=new_wire*new_wire "
        f"and not seen[pos_key] then "
        f"candidates[#candidates+1]={{position=pos,key=pos_key,"
        f"target=target_distance(pos)}} end end end;"
        f"table.sort(candidates,function(a,b) "
        f"if a.target~=b.target then return a.target<b.target end;"
        f"if a.position[1]~=b.position[1] then "
        f"return a.position[1]<b.position[1] end;"
        f"return a.position[2]<b.position[2] end);"
        f"for _,candidate in ipairs(candidates) do "
        f"seen[candidate.key]=true;"
        f"if valid_extension(candidate.position) then "
        f"local path={{}};for _,p in ipairs(state.path) do "
        f"path[#path+1]=p end;path[#path+1]=candidate.position;"
        f"if reaches_live(candidate.position) then "
        f"chain=path;connected=true;break end;"
        f"next_frontier[#next_frontier+1]="
        f"{{position=candidate.position,path=path}} end end;"
        f"if connected then break end end;"
        f"if connected then break end;frontier=next_frontier end end;"
        f"if not heated then trace.heat=trace.heat+1 end;"
        f"if not net then trace.logistics=trace.logistics+1 end;"
        f"if not construction then trace.construction=trace.construction+1 end;"
        f"if not supplies or not connected then trace.power=trace.power+1 end;"
        f"if heated and net and construction and supplies and connected then "
        f"rcon.print(anchor_result(ax,ay,w,h,en,chain,'standard','strict')) "
        f"return "
        f"else "
        f"if not heated then last_error='No heat coverage for '..cold "
        f"elseif not net then last_error='No logistic network coverage' "
        f"elseif not construction then "
        f"last_error='No construction network coverage for full cell' "
        f"elseif not supplies then last_error='Planned pole cannot power building' "
        f"else last_error='No live power connection within '..max_extensions.."
        f"' extension poles' end;"
        f"if not fallback_result then fallback_result=anchor_result("
        f"ax,ay,w,h,en,chain,'standard','fallback') end end end end end end;"
        f"if fallback_result then rcon.print(fallback_result) "
        f"else local failure=nil;"
        f"if explicit then failure='ERROR: '..last_error "
        f"else failure='ERROR: No suitable production-cell location within "
        f"'..max_search_radius..' tiles (last: '..last_error..')' end;"
        f"rcon.print(failure..'|TRACE:'..trace_text('none',0,0,'none')) end"
    )

    response = client.run(phase1, retry=True)
    phase1_result = response.strip() if response else "ERROR: empty response"
    phase1_result, trace_marker, search_trace = phase1_result.partition("|TRACE:")
    if trace_marker:
        print(f"PRODUCE search trace: {search_trace}", flush=True)
    if not phase1_result.startswith("ANCHOR:"):
        return phase1_result

    parts = phase1_result[len("ANCHOR:"):].split(",")
    try:
        anchor_ax_value = float(parts[0])
        anchor_ay_value = float(parts[1])
        anchor_w = int(parts[2])
        anchor_h = int(parts[3])
        en = parts[4]
    except (IndexError, ValueError):
        return "ERROR: Invalid location response"
    if (
        len(parts) not in (5, 6, 7, 8, 9)
        or not math.isfinite(anchor_ax_value)
        or not math.isfinite(anchor_ay_value)
        or not anchor_ax_value.is_integer()
        or not anchor_ay_value.is_integer()
        or anchor_w < 1
        or anchor_h < 1
        or not en
    ):
        return "ERROR: Invalid location response"
    resolved_surface = surface
    if len(parts) >= 7:
        resolved_surface = parts[6]
        if (
            not resolved_surface
            or any(
                not (
                    char.islower()
                    or char.isdigit()
                    or char in "-_"
                )
                for char in resolved_surface
            )
            or (surface != "current" and resolved_surface != surface)
        ):
            return "ERROR: Invalid location response"
    layout = parts[7] if len(parts) >= 8 else "standard"
    if layout not in ("standard", "aquilo-compact"):
        return "ERROR: Invalid location response"
    placement_mode = parts[8] if len(parts) == 9 else "strict"
    if placement_mode not in ("strict", "fallback"):
        return "ERROR: Invalid location response"
    extensions = []
    if len(parts) >= 6 and parts[5]:
        for encoded in parts[5].split(";"):
            try:
                px_text, py_text = encoded.split(":")
                px = float(px_text)
                py = float(py_text)
            except (ValueError, TypeError):
                return "ERROR: Invalid location response"
            if (
                not math.isfinite(px)
                or not math.isfinite(py)
                or not (px * 2).is_integer()
                or not (py * 2).is_integer()
                or int(px * 2) % 2 == 0
                or int(py * 2) % 2 == 0
                or (px, py) in extensions
            ):
                return "ERROR: Invalid location response"
            extensions.append((px, py))
    if len(extensions) > production_cell_max_extension_poles:
        return "ERROR: Invalid location response"
    if layout == "aquilo-compact" and (
        extensions or resolved_surface != "aquilo"
    ):
        return "ERROR: Invalid location response"
    anchor_ax = str(int(anchor_ax_value))
    anchor_ay = str(int(anchor_ay_value))
    extensions_lua = "{" + ",".join(
        f"{{{px},{py}}}" for px, py in extensions
    ) + "}"
    phase2_surface_lua = json.dumps(resolved_surface)

    phase2 = (
        f"/silent-command "
        f"local s=game.surfaces[{phase2_surface_lua}];"
        f"local x={anchor_ax};local y={anchor_ay};"
        f"local w={anchor_w};local h={anchor_h};"
        f"local cx=x+w/2;local cy=y+h/2;"
        f"local row=y+math.floor(h/2)+0.5;"
        f"local en={json.dumps(en)};"
        f"local item={item_lua};"
        f"local layout={json.dumps(layout)};"
        f"local allow_support_warnings="
        f"{'true' if placement_mode == 'fallback' else 'false'};"
        f"local extensions={extensions_lua};"
        f"local player=game.get_player({player_lua});"
        f"local cleanup={{}};"
        f"local warnings={{}};local warning_seen={{}};"
        f"local function support_issue(text) "
        f"if not allow_support_warnings then error(text) end;"
        f"if not warning_seen[text] then warning_seen[text]=true;"
        f"warnings[#warnings+1]=text end end;"
        f"local function rb() "
        f"for i=#cleanup,1,-1 do local g=cleanup[i];"
        f"if g and g.valid then pcall(function() g.destroy() end) end end;"
        f"local remaining=0;"
        f"for _,g in ipairs(cleanup) do "
        f"if g and g.valid then remaining=remaining+1 end end;"
        f"return remaining end;"
        f"local ok,err=pcall(function() "
        f"if not s then error('surface not found') end;"
        f"if not player then error('requesting player not found') end;"
        f"local r=prototypes.recipe[item];"
        f"local e=prototypes.entity[en];"
        f"local pole_proto=prototypes.entity['medium-electric-pole'];"
        f"if not r or not e or (layout=='standard' and not pole_proto) then "
        f"error('prototype changed after preflight') end;"
        f"if e.tile_width~=w or e.tile_height~=h then "
        f"error('building dimensions changed after preflight') end;"
        f"local pole_pos={{x+math.floor(w/2)+0.5,y-0.5}};"
        f"local area=nil;local plans=nil;"
        f"if layout=='aquilo-compact' then "
        f"area={{{{x,y}},{{x+w,y+h+2}}}};"
        f"plans={{"
        f"{{name=en,position={{cx,cy}}}},"
        f"{{name='requester-chest',position={{x+0.5,y+h+1.5}}}},"
        f"{{name='passive-provider-chest',position={{x+1.5,y+h+1.5}}}},"
        f"{{name='inserter',position={{x+0.5,y+h+0.5}},"
        f"direction=defines.direction.south}},"
        f"{{name='inserter',position={{x+1.5,y+h+0.5}},"
        f"direction=defines.direction.north}}"
        f"}} "
        f"else area={{{{x-2,y-1}},{{x+w+2,y+h}}}};plans={{"
        f"{{name=en,position={{cx,cy}}}},"
        f"{{name='requester-chest',position={{x-1.5,row}}}},"
        f"{{name='passive-provider-chest',position={{x+w+1.5,row}}}},"
        f"{{name='inserter',position={{x-0.5,row}},"
        f"direction=defines.direction.west}},"
        f"{{name='inserter',position={{x+w+0.5,row}},"
        f"direction=defines.direction.west}},"
        f"{{name='medium-electric-pole',position=pole_pos}}"
        f"}} end;"
        f"local requires_heat=s.planet and s.planet.name=='aquilo';"
        f"local heat_source_types={{'heat-pipe','reactor','heat-interface'}};"
        f"local heat_source_type={{['heat-pipe']=true,['reactor']=true,"
        f"['heat-interface']=true}};"
        f"local max_heat_reach=0;"
        f"if requires_heat then "
        f"for _,source_type in ipairs(heat_source_types) do "
        f"for _,p in pairs(prototypes.get_entity_filtered{{"
        f"{{filter='type',type=source_type}}}}) do "
        f"local radius=p.heating_radius or 0;local box=p.collision_box;"
        f"local extent=math.max(math.abs(box.left_top.x),"
        f"math.abs(box.left_top.y),math.abs(box.right_bottom.x),"
        f"math.abs(box.right_bottom.y));"
        f"max_heat_reach=math.max(max_heat_reach,radius+extent) end end end;"
        f"local function plan_is_heated(plan) "
        f"if not requires_heat then return true end;"
        f"local p=prototypes.entity[plan.name];"
        f"if not p or p.heating_energy<=0 then return true end;"
        f"local box=p.collision_box;"
        f"local left=plan.position[1]+box.left_top.x;"
        f"local top=plan.position[2]+box.left_top.y;"
        f"local right=plan.position[1]+box.right_bottom.x;"
        f"local bottom=plan.position[2]+box.right_bottom.y;"
        f"local sources=s.find_entities_filtered{{"
        f"area={{{{left-max_heat_reach,top-max_heat_reach}},"
        f"{{right+max_heat_reach,bottom+max_heat_reach}}}},"
        f"type=heat_source_types}};"
        f"for _,source in ipairs(sources) do "
        f"local radius=source.prototype.heating_radius or 0;"
        f"local heat_box=source.bounding_box;"
        f"if radius>0 and source.temperature and source.temperature>=30 "
        f"and right>heat_box.left_top.x-radius "
        f"and left<heat_box.right_bottom.x+radius "
        f"and bottom>heat_box.left_top.y-radius "
        f"and top<heat_box.right_bottom.y+radius then return true end end;"
        f"return false end;"
        f"local function plan_overlaps_heat_source(plan) "
        f"if not requires_heat then return false end;"
        f"local p=prototypes.entity[plan.name];local box=p.collision_box;"
        f"local left=plan.position[1]+box.left_top.x;"
        f"local top=plan.position[2]+box.left_top.y;"
        f"local right=plan.position[1]+box.right_bottom.x;"
        f"local bottom=plan.position[2]+box.right_bottom.y;"
        f"for _,source in ipairs(s.find_entities_filtered{{"
        f"area={{{{left,top}},{{right,bottom}}}},type=heat_source_types}}) do "
        f"local heat_box=source.bounding_box;"
        f"if right>heat_box.left_top.x and left<heat_box.right_bottom.x "
        f"and bottom>heat_box.left_top.y and top<heat_box.right_bottom.y then "
        f"return true end end;return false end;"
        f"local function count_blockers(area) "
        f"if not requires_heat then "
        f"return s.count_entities_filtered{{area=area}} end;"
        f"local count=0;for _,existing in ipairs("
        f"s.find_entities_filtered{{area=area}}) do "
        f"if not heat_source_type[existing.type] then count=count+1 end end;"
        f"return count end;"
        f"local function plan_has_live_power(plan) "
        f"for _,pole in ipairs(s.find_entities_filtered{{type='electric-pole',"
        f"area={{{{plan.position[1]-64,plan.position[2]-64}},"
        f"{{plan.position[1]+64,plan.position[2]+64}}}},force='player'}}) do "
        f"if pole.electric_network then "
        f"local supply=pole.prototype.get_supply_area_distance(pole.quality);"
        f"if math.abs(pole.position.x-plan.position[1])<=supply "
        f"and math.abs(pole.position.y-plan.position[2])<=supply then "
        f"return true end end end;return false end;"
        f"local count=count_blockers(area);"
        f"if count>0 then error(count..' entities appeared in area') end;"
        f"for _,plan in ipairs(plans) do "
        f"if plan_overlaps_heat_source(plan) or not "
        f"s.can_place_entity{{name=plan.name,position=plan.position,"
        f"direction=plan.direction,force='player',"
        f"build_check_type=defines.build_check_type.script_ghost}} then "
        f"error('cannot place '..plan.name) end end;"
        f"for _,plan in ipairs(plans) do "
        f"if not plan_is_heated(plan) then "
        f"support_issue('no heat coverage for '..plan.name) end end;"
        f"local requester=plans[2].position;"
        f"if not s.find_logistic_network_by_position(requester,'player') then "
        f"support_issue('no logistic network coverage') end;"
        f"local construction=true;"
        f"for _,plan in ipairs(plans) do "
        f"if #s.find_logistic_networks_by_construction_area("
        f"plan.position,'player')==0 then "
        f"construction=false break end end;"
        f"if not construction then "
        f"support_issue('no construction network coverage for full cell') end;"
        f"if layout=='aquilo-compact' then "
        f"if not requires_heat then error('compact layout requires Aquilo') end;"
        f"if #extensions~=0 then error('compact layout cannot use extension poles') end;"
        f"if not plan_has_live_power(plans[1]) "
        f"or not plan_has_live_power(plans[4]) "
        f"or not plan_has_live_power(plans[5]) then "
        f"support_issue('no existing power coverage for compact cell') end "
        f"else "
        f"if #extensions>{production_cell_max_extension_poles} then "
        f"error('too many extension poles') end;"
        f"local function overlaps_cell(pos) "
        f"local left=pos[1]-0.5;local right=pos[1]+0.5;"
        f"local top=pos[2]-0.5;local bottom=pos[2]+0.5;"
        f"return not (right<=area[1][1] or left>=area[2][1] "
        f"or bottom<=area[1][2] or top>=area[2][2]) end;"
        f"for _,pos in ipairs(extensions) do "
        f"if overlaps_cell(pos) then error('extension pole overlaps cell') end;"
        f"local cell={{{{pos[1]-0.5,pos[2]-0.5}},"
        f"{{pos[1]+0.5,pos[2]+0.5}}}};"
        f"if s.count_entities_filtered{{area=cell}}>0 then "
        f"error('entity appeared at extension pole') end;"
        f"if not s.can_place_entity{{name='medium-electric-pole',position=pos,"
        f"force='player',"
        f"build_check_type=defines.build_check_type.script_ghost}} then "
        f"error('cannot place extension pole') end;"
        f"if #s.find_logistic_networks_by_construction_area("
        f"pos,'player')==0 then "
        f"support_issue('no construction network coverage for extension pole') "
        f"end end;"
        f"local supply=pole_proto.get_supply_area_distance('normal');"
        f"if math.abs(cx-pole_pos[1])>supply "
        f"or math.abs(cy-pole_pos[2])>supply then "
        f"support_issue('planned pole cannot power building') end;"
        f"local new_wire=pole_proto.get_max_wire_distance('normal');"
        f"local previous=pole_pos;"
        f"for _,pos in ipairs(extensions) do "
        f"local dx=pos[1]-previous[1];local dy=pos[2]-previous[2];"
        f"if dx*dx+dy*dy>new_wire*new_wire then "
        f"error('extension pole chain exceeds wire reach') end;"
        f"previous=pos end;"
        f"local connected=false;"
        f"local poles=s.find_entities_filtered{{type='electric-pole',"
        f"area={{{{previous[1]-new_wire,previous[2]-new_wire}},"
        f"{{previous[1]+new_wire,previous[2]+new_wire}}}},force='player'}};"
        f"for _,pole in ipairs(poles) do "
        f"if pole.electric_network then "
        f"local reach=math.min(new_wire,"
        f"pole.prototype.get_max_wire_distance(pole.quality));"
        f"local dx=pole.position.x-previous[1];"
        f"local dy=pole.position.y-previous[2];"
        f"if dx*dx+dy*dy<=reach*reach then connected=true break end end end;"
        f"if not connected then "
        f"support_issue('no live power connection for extension chain') end end;"
        f"local b=s.create_entity{{"
        f"name='entity-ghost',position=plans[1].position,force='player',"
        f"inner_name=en,recipe=item"
        f"}};"
        f"if not b then error('building') end;cleanup[#cleanup+1]=b;"
        f"local req=s.create_entity{{"
        f"name='entity-ghost',position=plans[2].position,"
        f"force='player',inner_name='requester-chest'"
        f"}};"
        f"if not req then error('requester') end;cleanup[#cleanup+1]=req;"
        f"local prov=s.create_entity{{"
        f"name='entity-ghost',position=plans[3].position,"
        f"force='player',inner_name='passive-provider-chest'"
        f"}};"
        f"if not prov then error('provider') end;cleanup[#cleanup+1]=prov;"
        f"local ii=s.create_entity{{"
        f"name='entity-ghost',position=plans[4].position,"
        f"force='player',inner_name='inserter',"
        f"direction=plans[4].direction"
        f"}};"
        f"if not ii then error('input inserter') end;cleanup[#cleanup+1]=ii;"
        f"local oi=s.create_entity{{"
        f"name='entity-ghost',position=plans[5].position,"
        f"force='player',inner_name='inserter',"
        f"direction=plans[5].direction"
        f"}};"
        f"if not oi then error('output inserter') end;cleanup[#cleanup+1]=oi;"
        f"local po=nil;if layout=='standard' then po=s.create_entity{{"
        f"name='entity-ghost',position=pole_pos,"
        f"force='player',inner_name='medium-electric-pole'"
        f"}};"
        f"if not po then error('pole') end;cleanup[#cleanup+1]=po end;"
        f"if layout=='standard' then for _,pos in ipairs(extensions) do "
        f"local extra=s.create_entity{{name='entity-ghost',position=pos,"
        f"force='player',inner_name='medium-electric-pole'}};"
        f"if not extra then error('extension pole') end;"
        f"cleanup[#cleanup+1]=extra end end;"
        f"local actual_recipe=b.get_recipe();"
        f"if not actual_recipe or actual_recipe.name~=item then "
        f"error('building recipe was not set') end;"
        f"if r.ingredients then "
        f"req.copy_settings(b,player);"
        f"local sections=req.get_logistic_sections().sections;"
        f"for _,ing in ipairs(r.ingredients) do "
        f"local found=false;"
        f"for _,section in ipairs(sections) do "
        f"for _,filter in ipairs(section.filters) do "
        f"if filter.value and filter.value.name==ing.name "
        f"and filter.min and filter.min>0 then found=true end "
        f"end end;"
        f"if not found then error('request filter missing for '..ing.name) end "
        f"end "
        f"end;"
        f"for _,g in ipairs(cleanup) do "
        f"if not g.is_registered_for_construction() then "
        f"support_issue(g.ghost_name..' not registered for construction') end "
        f"end;"
        f"end);"
        f"if not ok then "
        f"local remaining=rb();"
        f"if remaining>0 then "
        f"rcon.print('ERROR: '..err..'; rollback incomplete: '..remaining) "
        f"else rcon.print('ERROR: '..err) end "
        f"else rcon.print("
        f"'SUCCESS: [gps='..x..','..y..','..s.name..'] '"
        f"..w..'x'..h..' '..item..' cell placed with '..en.."
        f"', requester-chest, 2 inserters, passive-provider-chest'.."
        f"(layout=='aquilo-compact' and "
        f"(#warnings==0 and ' using existing power' or ' using compact layout') or "
        f"', medium-electric-pole'..(#extensions>0 and "
        f"', '..#extensions..' extension medium-electric-pole'.."
        f"(#extensions==1 and '' or 's') or '')).."
        f"(#warnings>0 and '; WARNING: '..table.concat(warnings,', ') or '')) end"
    )

    response = client.run(phase2, retry=False)
    return response.strip() if response else "ERROR: empty response"


def dispatch_production_cell(client, produce_request, username):
    surface, item, hint = produce_request
    return place_production_cell(
        client,
        surface,
        item,
        hint,
        requesting_player=username,
    )


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
        "local function display(t) local base=t.name:match(\"^(.*)%-%d+$\");"
        "local repeatable=t.prototype.max_level>1;"
        "local name=repeatable and (base or t.name)..\" \"..t.level or t.name;"
        "return name:gsub(\"-\",\" \") end;"
        "local current=f.current_research;"
        "out[#out+1]=\"Current: \"..(current and display(current) or \"none\");"
        "out[#out+1]=string.format(\"Progress: %.2f%%\",f.research_progress*100);"
        "out[#out+1]=\"Queue:\";"
        "for i,t in ipairs(f.research_queue) do "
        "out[#out+1]=i..\": \"..display(t) end;"
        "rcon.print(table.concat(out,\"\\n\"))"
    )
    response = client.run(cmd, retry=True)
    return response.strip() if response else "(unavailable)"


def get_online_player_count(client):
    response = client.run(
        "/silent-command rcon.print(#game.connected_players)", retry=True
    )
    return int(response.strip())


def update_research_stall_state(research_text, spontaneous_state):
    name = None
    level = None
    progress = None
    for line in research_text.splitlines():
        if line.startswith("Current: "):
            name = line[len("Current: "):].strip()
        elif line.startswith("Current level: "):
            level = line[len("Current level: "):].strip()
        elif line.startswith("Progress: "):
            try:
                progress = float(line[len("Progress: "):].strip().rstrip("%"))
            except ValueError:
                pass
    if name is None or progress is None:
        return "unavailable", name, progress
    if level is not None:
        name = f"{name} (level {level})"

    unchanged = (
        name != "none"
        and name == spontaneous_state.get("research_name")
        and progress == spontaneous_state.get("research_progress")
    )
    if unchanged:
        status = (
            "stalled"
            if spontaneous_state.get("stall_announced")
            else "new_stall"
        )
    else:
        status = "changed"
        spontaneous_state["stall_announced"] = False
    spontaneous_state["research_name"] = name
    spontaneous_state["research_progress"] = progress
    return status, name, progress


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
        "- /version — check the Factorio version\n"
        "- Recipe ingredients — use one-line /silent-command Lua with "
        "prototypes.recipe[\"internal-name\"].ingredients. Factorio 2.x does not "
        "have game.recipe_prototypes.\n"
        "- LOGISTICS|surface|item-name,item-name — check requested items across "
        "player logistic networks on a planet. Use lowercase internal surface and "
        "item names, resolve references such as 'those materials' from recent chat, "
        "and include every requested item. Use LOGISTICS for requests asking what is "
        "available, on hand, or in stock on a named planet even when the player does "
        "not explicitly say 'logistic network'. Use surface 'all' when asked about "
        "anywhere, everywhere, all planets, or the whole solar system. Examples: "
        "LOGISTICS|fulgora|holmium-plate,superconductor,supercapacitor.\n"
         "- PRODUCE|surface|item-name|optional-location — place a compact "
        "production cell with a crafting machine, requester and provider chests, "
        "two inserters, and a power pole. Use lowercase internal names when the "
        "current player asks Jimbo to make, produce, craft, build, or set up "
        "manufacturing of a specific item. Copy an explicit player-supplied GPS "
        "map ping exactly; never invent or adjust coordinates. Otherwise use "
        "the normalized location 'view' for 'here', 'where I am looking', or the "
        "current remote view; use 'standing' only for the player's physical "
        "character position. Combine an origin and normalized direction as "
        "'standing:north' for 'north of my current location' or where the player "
        "is standing, and 'view:north' for north of the current map view. The "
        "eight directions are north, north-east, east, south-east, south, "
        "south-west, west, and north-west. A direction without an explicit origin "
        "remains relative to the current view. Use an empty fourth field when no "
        "location was supplied. Use surface 'current' when the request is relative "
        "to the player and does not name a surface. Examples: "
        "PRODUCE|current|electronic-circuit|standing:north, "
        "PRODUCE|current|electronic-circuit|view and "
        "PRODUCE|nauvis|electronic-circuit|[gps=-622,51,nauvis].\n"
        "- TAG|surface|entity-type|optional-label — find every entity of a given "
        "type on a surface and add a chart tag at each position. Use lowercase "
        "internal entity type names such as artillery-turret, electric-pole, "
        "rocket-silo, or roboport. The optional label is free text; when omitted, "
        "each tag shows the entity type and unit number. Examples: "
        "TAG|nauvis|artillery-turret, TAG|nauvis|artillery-turret|My Guns.\n"
        "- UNTAG|surface|entity-type|optional-label — find every chart tag on a "
        "surface whose text starts with the given entity type (or matches the "
        "exact label) and remove it. Examples: UNTAG|nauvis|artillery-turret, "
        "UNTAG|nauvis|artillery-turret|My Guns.\n"
        "- TOP_DAMAGE|surface|entity-type — find the entity of a given type "
        "with the highest stat on a surface and tag it. Uses damage_dealt for "
        "turrets, products_finished for machines (labeled \"launches\" for "
        "rocket-silo, \"products\" for other machines). Use entity-type \"any\" "
        "to search all machine types for the one with the most products_finished. "
        "Examples: TOP_DAMAGE|nauvis|artillery-turret, "
        "TOP_DAMAGE|nauvis|rocket-silo, TOP_DAMAGE|nauvis|any.\n"

        "- Any other Factorio slash command needed to perform a requested server "
        "action. Use one-line /silent-command Lua for scripted actions and call "
        "rcon.print with the actual outcome. When querying research, print the "
        "technology's level property; a repeatable technology's internal name "
        "suffix is not its current level.\n\n"
        "Recent chat (background context only, do NOT act on these):\n"
        f"{history_text}\n\n"
        "--- Current message to evaluate ---\n"
        f'{username} said: "{message}".\n\n'
        "Only the current message may request an action. Older mentions of Jimbo "
        "are context only. Use history to resolve references in the current message, "
        "never to revive an old request.\n\n"
        "Reply with exactly one line. Choose the best match:\n"
        "- SKIP (default) — player-to-player chat, casual greetings or comments "
        "NOT directed at Jimbo. If the message does not contain the word Jimbo, "
        "reply SKIP. If the current message contains the word Jimbo, never reply "
        "SKIP; use NONE for direct conversation with no action or query.\n"
        "- PLATFORMS — someone asking Jimbo about space platforms or ships.\n"
        "- PLANETS — someone asking Jimbo to list or identify the available planets. "
        "Do not use this for where an item or material comes from; a planet list "
        "does not establish material sources. Use NONE for established Factorio "
        "knowledge or query relevant prototypes when live data is needed.\n"
         "- PRODUCE|surface|item-name|optional-location — the current player asks "
        "Jimbo to place a production cell for a specific item. Use their explicit "
        "GPS ping, view, standing, an origin-qualified normalized direction, a "
        "backward-compatible view-relative direction, or an empty fourth field "
        "as described above.\n"
        "- TAG|surface|entity-type|optional-label — the current player asks Jimbo "
        "to tag, ping, or mark entities of a specific type on a named surface, "
        "such as nauvis or fulgora. Use a real surface name — "
        "\"current\" is not valid. Examples: TAG|nauvis|artillery-turret, "
        "TAG|nauvis|rocket-silo.\n"
        "- UNTAG|surface|entity-type|optional-label — the current player asks Jimbo "
        "to remove chart tags for entities of a specific type from a surface. "
        "When label is empty, matches tags whose text starts with the entity type "
        "name. When label is provided, matches only tags with that exact text. "
        "Examples: UNTAG|nauvis|artillery-turret, "
        "UNTAG|nauvis|artillery-turret|My Guns.\n"
        "- TOP_DAMAGE|surface|entity-type — the current player asks Jimbo to find "
        "the entity with the highest stat (damage_dealt for turrets, "
        "products_finished for machines) on a named surface and tag it. "
        "Use \"any\" as entity-type to search all machine types for the one "
        "with the most products_finished. Examples: "
        "TOP_DAMAGE|nauvis|artillery-turret, TOP_DAMAGE|nauvis|rocket-silo, "
        "TOP_DAMAGE|nauvis|any.\n"

        "- /players online, /players, /evolution, /time, /version — for those "
        "specific queries directed at Jimbo.\n"
        "- /<Factorio command> — an executable slash command when the player asks "
        "Jimbo to perform another server action. Never literally reply 'A Factorio "
        "slash command'. Do not return NONE for an actionable request.\n"
        "- NONE — someone directly addressing Jimbo by name but just chatting "
        "(greetings, thanks) with no server info needed. Also use NONE when the "
        "player asks for something that does not match any available action. "
        "Do NOT substitute a different action (e.g. TAG all instead of the "
        "one with the most launches) — instead return NONE and explain."
    )


def build_reply_prompt(username, message, history_text, rcon_command, rcon_response):
    context = (
        "Recent shared chat (background context only):\n"
        f"{history_text}\n\n"
        "For repeatable research, use its base name plus its actual level as a "
        "natural player-facing name, even when its internal name has no numeric "
        "suffix. For example, mining-productivity-3 at level 8 is mining "
        "productivity 8, and the next level is mining productivity 9. Similarly, "
        "scrap-recycling-productivity at level 3 is scrap recycling productivity "
        "3. Do not mention the internal name or redundantly append '(level 8)'.\n\n"
    )
    none_hint = ""
    if rcon_command == "NONE":
        none_hint = (
            "No action was taken — the request does not match any available "
            "command. Do NOT fabricate a result. Explain that you cannot "
            "fulfill this specific request and suggest what you CAN do "
            "(tag all, untag all, etc.).\n"
        )
    if rcon_response is not None:
        time_hint = ""
        if rcon_command == "/time":
            time_hint = (
                "The /time result is elapsed server/game time, not the current "
                "wall-clock time.\n"
            )
        planet_hint = ""
        if rcon_command == "RCON: list planets":
            planet_hint = (
                "This response establishes only which planets are available. It "
                "does not establish where an item comes from. Never claim that "
                "every listed planet supplies requested materials; answer each "
                "source specifically from established Factorio knowledge, or say "
                "the response does not determine it.\n"
            )
        logistics_hint = ""
        if rcon_command == "RCON: logistic availability":
            logistics_hint = (
                "Each item count is available stock, never a recipe shortfall. "
                "Compare it with any required quantity in recent chat. Zero means "
                "none is available, so the full required quantity is still needed.\n"
            )
        produce_hint = ""
        if rcon_command == "RCON: production cell":
            produce_hint = (
                "This response is the verified result of a production-cell "
                "placement request. On SUCCESS, report the anchor map ping and "
                "every created entity named in the response. If SUCCESS includes "
                "a WARNING, clearly say the cell was placed but repeat every "
                "reported heat, power, logistics, or construction issue that still "
                "needs attention. On ERROR, clearly say the cell was not placed "
                "and explain the reported reason. Never claim that placement "
                "succeeded when the response reports an error.\n"
            )
        tag_hint = ""
        if rcon_command == "RCON: map tags":
            tag_hint = (
                "This response reports how many entities were tagged on the "
                "surface. If it found none, say so clearly. If it succeeded, "
                "tell the player how many were tagged and of what type.\n"
            )
        untag_hint = ""
        if rcon_command == "RCON: remove tags":
            untag_hint = (
                "This response reports how many chart tags were removed from "
                "the surface. If it found no matching tags, say so clearly. "
                "If it succeeded, tell the player how many were removed.\n"
            )
        top_damage_hint = ""
        if rcon_command == "RCON: top damage":
            top_damage_hint = (
                "This response reports which entity of the requested type had "
                "the highest stat (damage_dealt or products_finished), its "
                "position, and the stat value. The response text either "
                "describes what was tagged or says nothing was found. "
                "Read the response literally and report its content — "
                "do NOT fabricate a failure when the response describes "
                "a successful tag. When the response includes an exact "
                "[gps=x,y,surface] map ping, include that markup verbatim "
                "in your reply so it renders as a clickable ping; never "
                "invent or change the coordinates.\n"
            )
        return (
            context
            + f'{username} currently asked: "{message}".\n'
            + f"Address your reply to {username}.\n"
            + f'I ran "{rcon_command}" and got the response: "{rcon_response}".\n'
            + time_hint
            + planet_hint
            + logistics_hint
            + produce_hint
            + tag_hint
            + untag_hint
            + none_hint
            + top_damage_hint
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
        + f'{username} (the player currently talking to Jimbo) said: "{message}".\n'
        + f"Address your reply to {username}.\n"
        + none_hint
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
    if not force and time.time() - last_spontaneous < 1200:
        return last_spontaneous
    if not force and spontaneous_state["skip_next"]:
        spontaneous_state["skip_next"] = False
        print("Skipping scheduled spontaneous comment after quiet request", flush=True)
        return time.time()

    try:
        online_players = get_online_player_count(client)
    except Exception as e:
        print(f"Online player count error: {e}", flush=True)
        return time.time()
    if online_players == 0:
        recent_chat.clear()
        spontaneous_state["failed_attempts"] = 0
        spontaneous_state["research_name"] = None
        spontaneous_state["research_progress"] = None
        spontaneous_state["stall_announced"] = False
        print("Skipping spontaneous comment with no players online", flush=True)
        return time.time()

    try:
        research_text = get_research_snapshot(client)
    except Exception as e:
        print(f"Research snapshot error: {e}", flush=True)
        research_text = "(unavailable)"
    stall_status, research_name, research_progress = update_research_stall_state(
        research_text, spontaneous_state
    )
    stall_reply = None
    if stall_status == "new_stall":
        readable_name = research_name.replace("-", " ")
        stall_reply = (
            f"Science research seems to be stalled: {readable_name} is still at "
            f"{research_progress:g}%."
        )
    elif stall_status == "stalled":
        if not recent_chat:
            print("Skipping already-announced research stall", flush=True)
            return time.time()
        research_text = (
            "(Research remains stalled and was already announced. Do not comment "
            "on research.)"
        )

    recent_text = "\n".join(recent_chat) if recent_chat else "(none)"
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
        "Research names in this snapshot are already player-facing; use them "
        "exactly rather than appending a separate level.\n"
        f"{focus_text}\n"
        "You can make a spontaneous comment if something interesting is "
        "happening. Reply with a short chat message (1 sentence) or just 'SKIP'. "
        "Do not simply rephrase, echo, or restate what was just said. If you "
        "cannot add something original, reply SKIP."
    )
    last_spontaneous = time.time()
    successful = False
    try:
        reply = stall_reply if stall_reply is not None else ask_ai(prompt)
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
                if stall_reply is not None:
                    spontaneous_state["stall_announced"] = True
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
    spontaneous_state = {
        "skip_next": False,
        "failed_attempts": 0,
        "research_name": None,
        "research_progress": None,
        "stall_announced": False,
    }
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
                        spontaneous_state["research_name"] = None
                        spontaneous_state["research_progress"] = None
                        spontaneous_state["stall_announced"] = False
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
                    directly_addressed = directly_addresses_jimbo(msg)
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
                    request_failed = False
                    run_platforms = False
                    run_planets = False
                    logistics_request = None
                    produce_request = None
                    tag_request = None
                    untag_request = None
                    top_damage_request = None

                    if not loosely_refers_to_jimbo(msg):
                        print("Model decided to skip", flush=True)
                    else:
                        try:
                            raw = classify_current_message(
                                username, msg, history_text
                            )
                            skip = False
                        except Exception as e:
                            print(f"AI error (step 1): {e}", flush=True)
                            skip = True
                            request_failed = True

                    if not skip:
                        if raw == "SKIP":
                            if directly_addressed:
                                request_failed = True
                                print(
                                    "Classifier failed a direct Jimbo message "
                                    "after retry",
                                    flush=True,
                                )
                            else:
                                print("Model decided to skip", flush=True)
                            skip = True
                        elif raw == "PLATFORMS":
                            run_platforms = True
                            print(f"Model requested PLATFORMS", flush=True)
                        elif raw == "PLANETS":
                            run_planets = True
                            print(f"Model requested PLANETS", flush=True)
                        elif parse_logistics_decision(raw) is not None:
                            logistics_request = parse_logistics_decision(raw)
                            print(
                                f"Model requested LOGISTICS: {logistics_request}",
                                flush=True,
                            )
                        elif parse_produce_decision(raw) is not None:
                            produce_request = parse_produce_decision(raw)
                            print(
                                f"Model requested PRODUCE: {produce_request}",
                                flush=True,
                            )
                        elif parse_tag_decision(raw) is not None:
                            tag_request = parse_tag_decision(raw)
                            print(
                                f"Model requested TAG: {tag_request}",
                                flush=True,
                            )
                        elif parse_untag_decision(raw) is not None:
                            untag_request = parse_untag_decision(raw)
                            print(
                                f"Model requested UNTAG: {untag_request}",
                                flush=True,
                            )
                        elif parse_top_damage_decision(raw) is not None:
                            top_damage_request = parse_top_damage_decision(raw)
                            print(
                                f"Model requested TOP_DAMAGE: {top_damage_request}",
                                flush=True,
                            )
                        elif raw in ("/players online", "/players", "/evolution", "/time", "/version") or raw.startswith("/"):
                            rcon_cmd = raw
                            print(f"Model command: {rcon_cmd}", flush=True)
                        elif raw.upper().startswith("NONE"):
                            rcon_cmd = "NONE"
                            print(f"Model command: NONE", flush=True)
                        else:
                            skip = True
                            request_failed = True
                            print(
                                f"Model returned unrecognized response {raw!r}, skipping",
                                flush=True,
                            )

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

                    if logistics_request is not None:
                        rcon_cmd = "RCON: logistic availability"
                        try:
                            rcon_response = get_logistic_availability(
                                client, *logistics_request
                            )
                            print(
                                f"LOGISTICS response: {rcon_response}", flush=True
                            )
                        except Exception as e:
                            print(f"RCON error: {e}", flush=True)
                            rcon_response = f"[error: {e}]"

                    if produce_request is not None:
                        rcon_cmd = "RCON: production cell"
                        try:
                            rcon_response = dispatch_production_cell(
                                client, produce_request, username
                            )
                            print(
                                f"PRODUCE response: {rcon_response}", flush=True
                            )
                        except Exception as e:
                            print(f"RCON error: {e}", flush=True)
                            rcon_response = f"[error: {e}]"

                    if tag_request is not None:
                        rcon_cmd = "RCON: map tags"
                        try:
                            rcon_response = run_tag_command(
                                client, *tag_request
                            )
                            print(
                                f"TAG response: {rcon_response}", flush=True
                            )
                        except Exception as e:
                            print(f"RCON error: {e}", flush=True)
                            rcon_response = f"[error: {e}]"

                    if untag_request is not None:
                        rcon_cmd = "RCON: remove tags"
                        try:
                            rcon_response = run_untag_command(
                                client, *untag_request
                            )
                            print(
                                f"UNTAG response: {rcon_response}", flush=True
                            )
                        except Exception as e:
                            print(f"RCON error: {e}", flush=True)
                            rcon_response = f"[error: {e}]"

                    if top_damage_request is not None:
                        rcon_cmd = "RCON: top damage"
                        try:
                            rcon_response = run_top_damage_command(
                                client, *top_damage_request
                            )
                            print(
                                f"TOP_DAMAGE response: {rcon_response}",
                                flush=True,
                            )
                        except Exception as e:
                            print(f"RCON error: {e}", flush=True)
                            rcon_response = f"[error: {e}]"
                    if skip:
                        if request_failed and directly_addressed:
                            report_request_failure(client, dialogue, recent_chat)
                        continue

                    # Execute built-in command if given
                    rcon_failed = False
                    if (
                        rcon_cmd
                        and rcon_cmd != "NONE"
                        and not rcon_cmd.startswith("RCON: ")
                    ):
                        print(f"RCON command: {rcon_cmd}", flush=True)
                        try:
                            raw_resp = client.run(
                                rcon_cmd, retry=rcon_cmd in safe_retry_commands
                            )
                            rcon_response = raw_resp.strip() if raw_resp else "[empty response]"
                            print(f"RCON response: {rcon_response}", flush=True)
                            if rcon_response.startswith("[empty"):
                                rcon_response = None
                                rcon_failed = True
                        except Exception as e:
                            print(f"RCON error: {e}", flush=True)
                            rcon_response = None
                            rcon_failed = True

                    if rcon_failed:
                        if directly_addressed:
                            report_request_failure(client, dialogue, recent_chat)
                        continue

                    # Step 3: Ask the model to compose a reply
                    reply = None
                    reply_failed = False
                    try:
                        step3_prompt = build_reply_prompt(
                            username, msg, history_text, rcon_cmd, rcon_response
                        )
                        reply = ask_ai(step3_prompt)
                        if reply == "SKIP":
                            reply = None
                            if directly_addressed:
                                reply_failed = True
                                print(
                                    "Model tried to stay silent on a direct "
                                    "Jimbo message",
                                    flush=True,
                                )
                            else:
                                print("Model chose to stay silent", flush=True)
                        else:
                            print(f"Model reply: {reply}", flush=True)
                            if not reply.strip():
                                reply = None
                                reply_failed = True
                    except Exception as e:
                        print(f"AI error (step 3): {e}", flush=True)
                        reply_failed = True

                    if reply_failed:
                        if directly_addressed:
                            report_request_failure(client, dialogue, recent_chat)
                        continue

                    if reply:
                        reply = ensure_gps_ping(reply, rcon_cmd, rcon_response)
                        sent_lines, send_error = send_jimbo_lines(client, reply)
                        record_direct_reply(
                            dialogue,
                            recent_chat,
                            sent_lines,
                            rcon_command=(
                                rcon_cmd if rcon_cmd and rcon_cmd != "NONE" else None
                            ),
                            rcon_response=rcon_response,
                        )
                        if send_error is not None:
                            print(f"RCON error: {send_error}", flush=True)
                            if directly_addressed:
                                report_request_failure(
                                    client, dialogue, recent_chat
                                )
                        elif not sent_lines and directly_addressed:
                            print(
                                "Reply contained no deliverable lines",
                                flush=True,
                            )
                            report_request_failure(
                                client, dialogue, recent_chat
                            )

                    last_spontaneous = maybe_spontaneous(
                        client, recent_chat, dialogue, last_spontaneous,
                        spontaneous_state,
                    )

            except (OSError, ValueError):
                print("Lost log file, reopening...", flush=True)
            finally:
                f.close()
