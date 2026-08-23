#!/usr/bin/env python3
"""Generate the model-facing Factorio scripting reference (lua_essentials.txt).

Source of truth is the machine-readable API documentation shipped inside the
full game install (doc-html/runtime-api.json), which matches the running
server binary exactly. Regenerate this file after every game upgrade so the
reference never drifts from the server:

    python generate_lua_reference.py

The output is committed; the source JSON is not.
"""
import json
import os
import sys
import textwrap

DEFAULT_SOURCE = (
    "/mnt/d/factorio-standalone/current/doc-html/runtime-api.json"
)
OUTPUT_NAME = "lua_essentials.txt"

RULES = """\
CORE RULES FOR /silent-command LUA (violations abort the whole command):
- Output with rcon.print(value). Plain Lua returns nothing over RCON; an \
empty response is not proof of success. Aggregate counts in Lua and keep \
total output under ~4000 characters.
- Reading a nonexistent key or method RAISES and kills the command; it never \
returns nil. Wrap every uncertain read: pcall(function() return obj.key end)
- Iterate collections with pairs(): game.surfaces, game.players (includes \
offline players), game.forces.
- Filtered searches: surface.find_entities_filtered{name=..., type=..., \
position={x,y}, radius=..., area={{x1,y1},{x2,y2}}}. Area bounds are \
exclusive: a w x h box anchored at tile (x,y) is {{x,y},{x+w,y+h}}.
- LuaInventory.get_contents() returns an array of {name=..., quality=..., \
count=...} entries indexed by slot; prefer get_item_count(name).
- Compare entity status against defines.entity_status.<name> constants; the \
numbers are not reverse-indexable.
- Lua 5.1: use string.char(...) (no chr()); never place a number literal \
directly before .. (write (n) .. ' suffix').
"""


def collapse(text, cap=140):
    parts = " ".join(text.split())
    if len(parts) > cap:
        parts = parts[: cap - 1].rstrip() + "…"
    return parts


def build_essentials(doc, source_path):
    lines = []
    version = doc.get("application_version", "unknown")
    lines.append(
        f"FACTORIO {version} SCRIPTING REFERENCE (authoritative for this "
        f"server; generated from {os.path.basename(source_path)}):"
    )

    lines.append("")
    lines.append("GLOBAL OBJECTS:")
    for obj in doc.get("global_objects", []):
        name = obj.get("name", "?")
        typ = obj.get("type", "")
        desc = collapse(obj.get("description", ""), cap=90)
        line = f"- {name} :: {typ}" if typ else f"- {name}"
        if desc:
            line += f" — {desc}"
        lines.append(line)

    lines.append("")
    lines.append("GLOBALS AS FUNCTIONS:")
    for fn in doc.get("global_functions", []):
        name = fn.get("name", "?")
        desc = collapse(fn.get("description", ""), cap=90)
        line = f"- {name}()"
        if desc:
            line += f" — {desc}"
        lines.append(line)

    lines.append("")
    wrapped = textwrap.fill(
        ", ".join(c["name"] for c in doc.get("classes", [])),
        width=96,
        initial_indent="",
        subsequent_indent="  ",
    )
    lines.append("ALL LUA CLASSES (members exist only if listed here; do not "
                 "invent class or member names):")
    lines.append(wrapped)

    lines.append("")
    lines.append(RULES.rstrip())
    return "\n".join(lines) + "\n"


def main(argv):
    source = argv[1] if len(argv) > 1 else DEFAULT_SOURCE
    try:
        with open(source, encoding="utf-8") as f:
            doc = json.load(f)
    except OSError as e:
        print(f"Cannot read {source}: {e}", flush=True)
        return 1

    essentials = build_essentials(doc, source)
    out_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), OUTPUT_NAME
    )
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(essentials)
    print(
        f"Wrote {out_path} ({len(essentials)} chars) from "
        f"{doc.get('application_version', '?')} docs"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
