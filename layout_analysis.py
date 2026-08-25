"""Deterministic balance/throughput analysis for proposed Factorio layouts.

Planning tool for FIX_PLAN item 3 Step 3 (replan): given a recipe and the
machines/modules in a proposed multi-building layout, compute per-building
throughput and utilization, the bottleneck stage, expected output, and rough
buffer guidance. Jimbo's custom-cell worker will call this in its design loop so
the AI composes against flow feedback, not just geometry.

The model is deliberately deterministic and testable. Module-effect values are
INPUTS (verified against the live server / prototype dump) rather than
hardcoded guesses, so the analysis never silently assumes unverified Factorio
numbers.
"""

# The documented quality-upgrade model, in order. After an initial upgrade roll
# of chance Q, each further tier jump succeeds with a 10% continuation chance,
# capped at Legendary (see the old-repo qup SPEC).
QUALITY_TIERS = ("normal", "uncommon", "rare", "epic", "legendary")

# Recycling returns this share of reversible solid ingredients before quality
# rolls apply (25%).
RECYCLING_RECOVERY_SHARE = 0.25


def quality_chance_distribution(total_quality_chance):
    """Map a total quality chance Q to per-tier probabilities.

    Returns a dict {tier: probability} for QUALITY_TIERS whose entries sum to 1.
    Model: normal = 1 - Q; each upgrade roll succeeds with chance Q, then
    continues upward at 10% per extra tier, capped at Legendary.

    >>> d = quality_chance_distribution(0.1)
    >>> (d["normal"], d["uncommon"], d["rare"], d["epic"], d["legendary"])
    (0.9, 0.09, 0.009, 0.0009, 0.0001)
    """
    continuation = 0.10
    if not (0.0 <= total_quality_chance <= 1.0):
        raise ValueError("total_quality_chance must be within [0, 1]")
    normal = 1.0 - total_quality_chance
    distribution = {"normal": normal}
    higher = QUALITY_TIERS[1:]
    for index, tier in enumerate(higher):
        is_cap = index == len(higher) - 1
        power = continuation ** index
        if is_cap:
            distribution[tier] = total_quality_chance * power
        else:
            distribution[tier] = (
                total_quality_chance * power * (1.0 - continuation)
            )
    return distribution


def machine_quality_chance(modules, module_effects):
    """Total quality chance for one machine given its module names.

    Module effects of the same kind are ADDITIVE within a single machine (the
    standard Factorio rule). Returns the summed quality bonus from every module
    whose effect entry exists in module_effects.

    module_effects is {module_name: {"quality": float, "speed": float}}.
    """
    total = 0.0
    for module in modules or []:
        effect = module_effects.get(module)
        if effect:
            total += effect.get("quality", 0.0)
    return min(1.0, max(0.0, total))


def effective_speed_multiplier(modules, module_effects):
    """Speed multiplier (1 + sum of additive speed bonuses) for one machine."""
    bonus = 0.0
    for module in modules or []:
        effect = module_effects.get(module)
        if effect:
            bonus += effect.get("speed", 0.0)
    return 1.0 + bonus


def craft_time_seconds(recipe_energy, machine_speed, speed_multiplier):
    """Seconds per craft for one machine at the given effective speed."""
    effective = machine_speed * max(1e-9, speed_multiplier)
    return recipe_energy / effective


def per_building_throughput(
    recipe_energy,
    product_amount,
    machine_speed,
    speed_multiplier,
    count=1,
):
    """Primary-product items/second produced by `count` identical machines.

    Assumes continuous operation (never starved or blocked); that is the
    optimistic ceiling the bottleneck comparison is normalized against.
    """
    single = product_amount / craft_time_seconds(
        recipe_energy, machine_speed, speed_multiplier
    )
    return single * count


def summarize_buildings(recipe, buildings, module_effects):
    """Compute per-building flow numbers for a proposed layout.

    buildings is a list of dicts:
      {"name", "count", "recipe_energy", "product_amount",
       "machine_speed", "modules", "recipe_quality", "feeds"}

    Returns a list of per-building result dicts (input plus computed:
    quality_chance, throughput, quality_distribution, expected_recycled_rate,
    expected_recovery_rate), and the overall bottleneck stage name or None.
    """
    results = []
    for building in buildings:
        quality = machine_quality_chance(
            building.get("modules", []), module_effects
        )
        speed_mult = effective_speed_multiplier(
            building.get("modules", []), module_effects
        )
        throughput = per_building_throughput(
            building.get("recipe_energy", recipe.get("energy", 0)),
            building.get("product_amount", 1),
            building.get("machine_speed", 1),
            speed_mult,
            building.get("count", 1),
        )
        distribution = quality_chance_distribution(quality)
        lower = sum(
            distribution[tier]
            for tier in QUALITY_TIERS
            if tier != "legendary"
        )
        results.append({
            "name": building["name"],
            "count": building.get("count", 1),
            "recipe_quality": building.get("recipe_quality", "normal"),
            "quality_chance": quality,
            "speed_multiplier": speed_mult,
            "craft_time": craft_time_seconds(
                building.get("recipe_energy", recipe.get("energy", 0)),
                building.get("machine_speed", 1),
                speed_mult,
            ),
            "throughput": throughput,
            "quality_distribution": distribution,
            "lower_quality_share": lower,
            "expected_recycled_rate": throughput * lower,
            "expected_recovery_rate": (
                throughput * lower * RECYCLING_RECOVERY_SHARE
            ),
        })
    bottleneck = None
    if len(results) > 1:
        bottlenecks = min(results, key=lambda r: r["throughput"])
        bottleneck = f"{bottlenecks['name']} ({bottlenecks['count']})"
    return results, bottleneck


def format_analysis_text(recipe, results, bottleneck):
    """Human-readable summary for feeding back into the worker's prompt."""
    lines = [
        f"Throughput analysis for '{recipe.get('name', '?')}' "
        f"(crafting time {recipe.get('energy', 0)}s):"
    ]
    for result in results:
        lines.append(
            f"- {result['name']} x{result['count']} (quality "
            f"{result['recipe_quality']}): craft {result['craft_time']:.3f}s, "
            f"quality chance {result['quality_chance']:.3f}, output "
            f"{result['throughput']:.3f} items/s"
        )
    if bottleneck:
        lines.append(f"Bottleneck: {bottleneck}")
    return "\n".join(lines)


def analyze_layout(recipe, buildings, module_effects):
    """Full analysis entry point returning (results, bottleneck, summary)."""
    results, bottleneck = summarize_buildings(recipe, buildings, module_effects)
    summary = format_analysis_text(recipe, results, bottleneck)
    return results, bottleneck, summary
