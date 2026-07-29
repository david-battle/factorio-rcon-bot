# Alert Awareness

Give Jimbo awareness of active game alerts (entity damage, destroyed
buildings, logistic shortages, etc.) so his spontaneous comments and direct
replies are grounded in what is actually happening on each surface.

## Motivating Failure

Moon-O-Cronic said "there are teslas available". Jimbo replied "sounds like
a great way to keep the biters honest", assuming the threat was Nauvis
biters. The actual context was Gleba pentapod stompers. If Jimbo had seen
active `turret_enemy` alerts on Gleba he would have replied appropriately.

## Factorio Alert API

`game.forces.player.alerts` is a table of `LuaAlert` objects. Each alert has:

| Field | Type | Meaning |
|---|---|---|
| `type` | string | `"turret_enemy"`, `"custom"`, `"not_enough_construction_robots"`, `"no_material_for_construction"`, `"entity_destroyed"`, `"cannot_build_ghost"`, `"not_enough_repair_packs"`, `"train_out_of_fuel"`, `"missing_research_science_packs"` |
| `target` | `LuaEntity` | The entity that triggered the alert |
| `surface` | `LuaSurface` | The surface the alert is on |
| `icon` | `LuaPrototype` | Signal prototype used for the alert icon |
| `ticks_to_live` | uint | Remaining ticks before the alert expires |
| `message` | string | Custom alert message (only for `"custom"` type) |
| `show_on_map` | boolean | Whether the alert appears on the map |

## Design

Add a `get_alerts_snapshot(client)` function, mirroring
`get_research_snapshot()`. It returns a compact human-readable summary of
current alerts grouped by surface and type.

Include the alert snapshot in the spontaneous commentary prompt alongside
research and recent chat. Also include it in the reply prompt when the model
selects NONE and the player message references something that might be
alert-related.

### Lua Query

```text
/silent-command local f=game.forces.player;local out={};local groups={};
for _,a in ipairs(f.alerts) do
  local key=a.surface.name.."|"..a.type;
  if not groups[key] then groups[key]=0 end;
  groups[key]=groups[key]+1;
end;
for k,c in pairs(groups) do out[#out+1]=k..":"..c end;
rcon.print(table.concat(out,"\n"))
```

Returns lines like:

```
nauvis|turret_enemy:1
gleba|entity_destroyed:1
fulgora|not_enough_construction_robots:2
```

Optionally include the positions of a sample of alert targets so the model
has a GPS reference.

### Player-directed alert query

Add a classifier trigger so a player can directly ask Jimbo about alerts:

```
ALERTS|surface
```

- `ALERTS|all` — shows alerts on every surface.
- `ALERTS|gleba` — shows alerts on Gleba only.
- `ALERTS|nauvis` — shows alerts on Nauvis only.

The classifier prompt gains:

```
- ALERTS|surface — list current alerts for the named surface, or "all" for
  everything. Use when someone asks about problems, damage, attacks,
  warnings, or what is wrong on a planet.
```

### Spontaneous integration

When building the spontaneous commentary prompt, append a compact alert
summary:

```
Current alerts:
nauvis|turret_enemy:1 at [gps=123,456,nauvis]
```

This lets Jimbo reference real events without querying the model separately.

If there are no active alerts, include "No active alerts." so the model
knows the lack of data is meaningful rather than absent.

## Implementation Order

### Step 1: `get_alerts_snapshot(client)`

Add a function that runs the Lua query and returns a parsed summary string.
Test with mocked RCON.

### Step 2: Include in spontaneous prompt

Append the alert snapshot to the `maybe_spontaneous()` prompt alongside
research. The model can then reference alerts in its spontaneous comments.

### Step 3: Classifier + dispatch

Add `ALERTS|surface` to the classifier prompt, `parse_alerts_decision()`,
and a dispatch block that runs the filtered query and returns the result
through the reply pipeline.

### Step 4: Include in reply prompt for alert-related NONE replies

When the model returns NONE and the message references something potentially
alert-related (attacks, damage, warnings, problems), include the alert
snapshot as background context in the reply prompt.

## Safety

- Read-only query — no mutation.
- Alert data is transient; never store or replay it.
- Keep the output compact so it does not crowd out other prompt context.
- Suppress alerts older than a configurable threshold (default: ignore
  alerts with fewer than N ticks_to_live remaining, or just take the
  current snapshot as-is since Factorio expires them naturally).

## Testing

Follow existing patterns:

- **`test_get_alerts_snapshot`** — mock RCON returns multi-surface alert
  data; verify parsed output includes correct counts.
- **`test_alerts_snapshot_empty`** — mock returns no alerts; verify output
  indicates no active alerts.
- **`test_parse_alerts_decision_valid`** — `ALERTS|all`, `ALERTS|gleba`.
- **`test_parse_alerts_decision_invalid`** — wrong prefix, invalid surface.
- **`test_spontaneous_includes_alerts`** — verify alert text appears in the
  prompt when alerts exist.
- **`test_spontaneous_omits_alerts_when_none`** — verify "No active alerts"
  appears instead.
