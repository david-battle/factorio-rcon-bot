"""Geometry helpers for Jimbo's code-authoring layout worker.

The custom-cell worker asks the model to WRITE a small Python generator (not a
static JSON blob). That generator runs as a normal Python script in the job's
subdirectory and imports these helpers to compute a valid plan. Running as the
same user with the same reach as Jimbo itself, per owner direction; the
generator's OUTPUT is still gated by the deterministic validator before any
ghost is stamped.
"""

REACH = {
    "inserter": {"pickup": 1.0, "drop": 1.2},
    "burner-inserter": {"pickup": 1.0, "drop": 1.2},
    "long-handed-inserter": {"pickup": 2.0, "drop": 2.2},
}

_ORDER = ("east", "south", "west", "north")


def plan(name, x, y, d="", role="part"):
    """Build one plan entry at a half-tile center."""
    return {"n": name, "x": x, "y": y, "d": d, "r": role}


def building(name, x, y):
    return plan(name, x, y, "", "building")


def inserter(name, x, y, d):
    return plan(name, x, y, d, "inserter")


def belt(x, y, d="east"):
    return plan("transport-belt", x, y, d, "belt")


def pole(x, y):
    return plan("medium-electric-pole", x, y, "", "pole")


def requester(x, y):
    return plan("requester-chest", x, y, "", "requester")


def provider(x, y):
    return plan("passive-provider-chest", x, y, "", "provider")


def splitter(x, y, d="east"):
    return plan("splitter", x, y, d, "splitter")


def underground_belt(x, y, d="east"):
    return plan("underground-belt", x, y, d, "underground-belt")


def dims(facts, name):
    """Return the {w, h} footprint of a building known to the survey, or None."""
    return facts.get("machines", {}).get(name)


def center(facts, name, x, y):
    """Entity center of a building whose top-left anchor tile is (x, y)."""
    size = dims(facts, name)
    if not size:
        raise ValueError(f"no surveyed dimensions for '{name}'")
    return x + size["w"] / 2, y + size["h"] / 2


def box(facts, entry):
    """Return (x1, y1, x2, y2) for a plan entry, honoring building footprints."""
    if entry["r"] == "building":
        size = dims(facts, entry["n"])
        if not size:
            return None
        width = size["w"]
        height = size["h"]
    else:
        width = height = 1
    return (
        entry["x"] - width / 2,
        entry["y"] - height / 2,
        entry["x"] + width / 2,
        entry["y"] + height / 2,
    )


def boxes_intersect(a, b, epsilon=1e-9):
    return (
        a[0] < b[2] - epsilon
        and b[0] < a[2] - epsilon
        and a[1] < b[3] - epsilon
        and b[1] < a[3] - epsilon
    )


def point_in_box(point, box, epsilon=1e-6):
    return (
        box[0] - epsilon <= point[0] <= box[2] + epsilon
        and box[1] - epsilon <= point[1] <= box[3] + epsilon
    )


def bounding_box(facts, entries):
    """Union bounding box of all plan entries as (x1, y1, x2, y2)."""
    boxes = [box(facts, entry) for entry in entries]
    boxes = [b for b in boxes if b is not None]
    if not boxes:
        return (0, 0, 0, 0)
    return (
        min(b[0] for b in boxes),
        min(b[1] for b in boxes),
        max(b[2] for b in boxes),
        max(b[3] for b in boxes),
    )


def bank(facts, name, count, row_x, row_y):
    """Canonical horizontal parallel bank (the dominant Factorio pattern):
    a shared input belt on the north edge feeding a row of `count` identical
    `name` machines via one inserter each, then one inserter each pushing to
    a shared output belt on the south edge, with a power pole per machine.

    `row_x`/`row_y` are the integer top-left tile of the first machine. All
    plan offsets are relative to that corner (the parent positions the plan
    around the first building's top-left). Returns a complete, validator-ready
    plan dict with `layout=custom`, `pole=True`, `req=False`.

    Raises ValueError if `name` has no surveyed dimensions.
    """
    size = dims(facts, name)
    if not size:
        raise ValueError(f"no surveyed dimensions for '{name}'")
    w, h = size["w"], size["h"]
    input_belt_row = row_y - 2
    output_belt_row = row_y + h + 1.5
    length = count * w
    x_end = row_x + length

    plans = []
    for i in range(count):
        left = row_x + i * w
        mc_x = left + w / 2
        mc_y = row_y + h / 2
        plans.append(building(name, mc_x, mc_y))
        plans.append(inserter("inserter", mc_x, row_y - 1, "south"))
        plans.append(
            inserter("inserter", mc_x, row_y + h + 0.5, "south")
        )
        plans.append(pole(mc_x, row_y + h + 3))
    for j in range(length):
        x = row_x + j + 0.5
        plans.append(belt(x, input_belt_row, "east"))
        plans.append(belt(x, output_belt_row, "east"))
    return {
        "layout": "custom",
        "plans": plans,
        "area": [row_x - 1, row_y - 3, x_end + 1, row_y + h + 4],
        "pole": True,
        "req": False,
    }


def rotate(entry, steps, w, h):
    """Rotate a plan entry by steps (0-3) quarter-turns around a w x h anchor."""
    x, y = rotate_offset(entry["x"], entry["y"], steps, w, h)
    return plan(
        entry["n"], x, y, rotate_direction(entry["d"], steps), entry["r"]
    )


def rotate_offset(dx, dy, steps, w, h):
    if steps == 0:
        return dx, dy
    if steps == 1:
        return h - dy, dx
    if steps == 2:
        return w - dx, h - dy
    return dy, w - dx


def rotate_direction(direction, steps):
    if not direction:
        return ""
    return _ORDER[(_ORDER.index(direction) + steps) % 4]
