#!/usr/bin/env python3
"""V10.7 spaced-bench layout: tall upright clutter, full 8-slot table use.

Same planner (``PactPlaceCorridorPolicy`` / V10.6 sampler). Does **not** MimicGen.
Does **not** stretch meshes — selects accepted palette UIDs that are already
tall/standing (soap bottles, spray can, can, candle), not potatoes/mugs/plates.

Palette = 2 vessels (glass mid-bench + front route blocker) + 6 tall decor.
All 8 are active; side rails fill left/right so the table is used, not empty.
"""

from __future__ import annotations

from typing import Any

from pact_place_v95_contract import V95_LAYOUT_FAMILIES, load_v95_palette
from pact_place_v9_contract import SHELF_TOP_Z, WORKSPACE_HIGH_XYZ, WORKSPACE_LOW_XYZ
from pact_place_v105_contract import V95_LAYOUT_FAMILY_IDS, V95_VESSEL_JITTER

ENVIRONMENT_VERSION_SPACED = "pact_place_corridor_v10_7_spaced_bench"
LAYOUT_CONTRACT_VERSION = "pact_place_v107_spaced_bench_v4"
# Decor↔anything uses a wide gap; the two vessels keep V9's 10 mm.
MIN_DECOR_GAP_M = 0.040
MIN_VESSEL_GAP_M = 0.010
# All six decor slots are active (full 8-object table).
ACTIVE_DECOR_SLOTS = ("02", "03", "04", "05", "07", "08")

# Tall standing UIDs only (accepted in palette_v9_1). Natural sizes — not resized.
# Vessels (slots 06 / 01) stay Soap_Bottle_11 + Soap_Bottle_30 from V9.5.
#
# Sampler enforces ≤2 props per category string. Vessels already consume both
# ``soapbottle`` slots, so the two extra soap-bottle *meshes* are labeled
# ``vase`` / ``pot`` (approved tall vessel-like categories) — same UIDs, no
# stretch, no potatoes/mugs.
#
# Tippy tall candle 857d3f1a… removed (settled/toppled every episode at step 9).
# Slot 05 is the second stable can instead.
TALL_STANDING_DECOR: tuple[tuple[str, str, str], ...] = (
    ("02", "Soap_Bottle_3", "vase"),  # tall soap-bottle mesh
    ("03", "Soap_Bottle_1", "pot"),  # tall soap-bottle mesh
    ("04", "e3227ecd37d44cd6be1331941d9cfa2f", "spray can"),
    ("05", "663b5edc92a543668c1b602981e724a4", "can"),  # stable can (replaces tippy candle)
    ("07", "5d13903e21044558bfb2bb7b72e76b4d", "can"),
    ("08", "Candle_4", "candle"),
)

# Glass sits in the empty mid-bench; ONE bottle stays up front as the route blocker.
# Y stagger follows intrusion_side so the open lane stays on the panel side.
SPACED_VESSEL_XY_M: dict[str, dict[str, tuple[float, float]]] = {
    "left": {
        "inbound": (1.02, -0.08),  # Soap_Bottle_11 (glass) — mid/back empty zone
        "outbound": (0.68, 0.02),  # Soap_Bottle_30 — front route blocker
    },
    "right": {
        "inbound": (1.02, 0.08),
        "outbound": (0.68, -0.02),
    },
}

# Side rails around the glass + blocker; front corners freed beside the blocker.
# Workspace ~ x[0.50, 1.34] × y[-0.43, 0.43].
SPACED_DECOR_XY_M: dict[str, tuple[float, float]] = {
    "02": (0.72, 0.34),   # Soap_Bottle_3   — front right
    "03": (0.72, -0.34),  # Soap_Bottle_1   — front left
    "04": (0.95, 0.36),   # spray can       — mid right
    "05": (0.95, -0.36),  # stable can      — mid left
    "07": (1.22, 0.28),   # can             — back right
    "08": (1.22, -0.28),  # Candle_4        — back left
}


def _record_by_uid(palette_document: dict[str, Any]) -> dict[str, dict[str, Any]]:
    return {
        str(item["uid"]): item
        for item in (palette_document.get("records") or [])
        if item.get("accepted")
    }


def _slot_from_record(
    *,
    slot: str,
    role: str,
    uid: str,
    category: str,
    record: dict[str, Any],
) -> dict[str, Any]:
    dimensions = [float(value) for value in record["collision_dimensions_m"]]
    return {
        "slot": slot,
        "slot_class": "prop",
        "role": role,
        "uid": uid,
        "category": category,
        "dimensions_m": dimensions,
        "annotation_dimensions_m": [float(value) for value in record["dimensions_m"]],
        "half_m": [value / 2.0 for value in dimensions],
        "max_dimension_m": max(dimensions),
        "support": "shelf_standing",
        "quat_wxyz": [2**-0.5, 2**-0.5, 0.0, 0.0],
        "body_prefix": f"pact_clutter_{slot}/",
    }


def load_spaced_palette() -> dict[str, Any]:
    """2 vessels (V9.5 glass + blocker) + 6 tall standing decor (natural sizes)."""
    base = load_v95_palette()
    records = _record_by_uid(base)
    by_slot = {str(item["slot"]): dict(item) for item in base["palette"]}

    inbound = dict(by_slot["06"])
    inbound["role"] = "inbound_vessel"
    outbound = dict(by_slot["01"])
    outbound["role"] = "outbound_vessel"

    decor: list[dict[str, Any]] = []
    for slot, uid, category in TALL_STANDING_DECOR:
        record = records.get(uid)
        if record is None:
            raise ValueError(f"spaced palette missing accepted UID {uid}")
        height = float(record["collision_dimensions_m"][2])
        if height < 0.11:
            raise ValueError(f"decor {uid} is not standing-tall enough (h={height:.3f})")
        decor.append(
            _slot_from_record(
                slot=slot, role="decor", uid=uid, category=category, record=record
            )
        )

    palette = [inbound, outbound, *decor]
    palette.sort(key=lambda item: str(item["slot"]))
    if len(palette) != 8:
        raise ValueError(f"expected 8 palette entries, got {len(palette)}")

    return {
        "palette": palette,
        "derived_for_environment_version": ENVIRONMENT_VERSION_SPACED,
        "layout_contract_version": LAYOUT_CONTRACT_VERSION,
        "selection_policy": {
            "stretch_meshes": False,
            "tall_standing_only": True,
            "active_decor_slots": list(ACTIVE_DECOR_SLOTS),
            "parked_decor_slots": [],
            "min_decor_gap_m": MIN_DECOR_GAP_M,
            "min_vessel_gap_m": MIN_VESSEL_GAP_M,
            "category_cap_note": (
                "soapbottle capped at 2 by vessels; Soap_Bottle_3/1 labeled "
                "vase/pot so extra tall bottle meshes can sit on the table"
            ),
        },
        "records_sha_source": "diagnostics_output/pact_place_v9_v0b/palette_v9_1.json",
    }


def _object_entry(item: dict[str, Any], xy: tuple[float, float]) -> dict[str, Any]:
    dimensions = [float(value) for value in item["dimensions_m"]]
    half = [value / 2.0 for value in dimensions]
    x, y = xy
    return {
        "palette_slot": str(item["slot"]),
        "uid": str(item["uid"]),
        "role": str(item["role"]),
        "category": str(item["category"]),
        "support": "bench_standing",
        "center_m": [float(x), float(y), float(SHELF_TOP_Z + half[2])],
        "half_m": half,
        "quat_wxyz": [float(value) for value in item["quat_wxyz"]],
        "size_class": (
            "small"
            if max(dimensions) <= 0.10
            else "medium"
            if max(dimensions) <= 0.18
            else "large"
        ),
    }


def validate_spaced_layout(layout: dict[str, Any]) -> None:
    objects = list(layout.get("objects") or [])
    if len(objects) != 8:
        raise ValueError(f"spaced layout expects 8 active objects, got {len(objects)}")

    for item in objects:
        center = tuple(map(float, item["center_m"]))
        half = tuple(map(float, item["half_m"]))
        for k in range(3):
            if center[k] - half[k] < WORKSPACE_LOW_XYZ[k] - 1e-6:
                raise ValueError(f"slot {item['palette_slot']} escapes low workspace")
            if center[k] + half[k] > WORKSPACE_HIGH_XYZ[k] + 1e-6:
                raise ValueError(f"slot {item['palette_slot']} escapes high workspace")

    vessel_roles = {"inbound_vessel", "outbound_vessel"}
    for i, left in enumerate(objects):
        lc = tuple(map(float, left["center_m"]))
        lh = tuple(map(float, left["half_m"]))
        for right in objects[i + 1 :]:
            rc = tuple(map(float, right["center_m"]))
            rh = tuple(map(float, right["half_m"]))
            both_vessels = (
                left["role"] in vessel_roles and right["role"] in vessel_roles
            )
            gap = MIN_VESSEL_GAP_M if both_vessels else MIN_DECOR_GAP_M
            separated = any(
                abs(lc[k] - rc[k]) >= lh[k] + rh[k] + gap for k in (0, 1)
            )
            if not separated:
                raise ValueError(
                    f"spaced overlap: {left['palette_slot']} vs {right['palette_slot']}"
                )


def build_spaced_layout(
    palette_document: dict[str, Any], *, family_id: str, intrusion_side: str
) -> dict[str, Any]:
    if family_id not in V95_LAYOUT_FAMILIES:
        raise ValueError(f"unknown family {family_id}")
    if intrusion_side not in {"left", "right"}:
        raise ValueError(f"bad intrusion_side {intrusion_side}")

    # Family id kept for row metadata / jitter; vessel XY is spaced-bench:
    # blocker stays front, glass sits in the empty mid-bench.
    vessel_xy = SPACED_VESSEL_XY_M[intrusion_side]
    inbound_xy = vessel_xy["inbound"]
    outbound_xy = vessel_xy["outbound"]
    by_slot = {str(item["slot"]): item for item in palette_document["palette"]}
    inbound = by_slot["06"]
    outbound = by_slot["01"]

    objects = [
        _object_entry(inbound, tuple(map(float, inbound_xy))),
        _object_entry(outbound, tuple(map(float, outbound_xy))),
    ]
    for slot in ACTIVE_DECOR_SLOTS:
        objects.append(_object_entry(by_slot[slot], SPACED_DECOR_XY_M[slot]))

    expected_bow = "-y" if intrusion_side == "left" else "+y"
    layout = {
        "layout_id": f"v107_spaced_{intrusion_side}_{family_id}",
        "layout_family_id": family_id,
        "layout_contract_version": LAYOUT_CONTRACT_VERSION,
        "intrusion_side": intrusion_side,
        "objects": objects,
        "inbound_vessel_slot": "06",
        "outbound_vessel_slot": "01",
        "route_blocker_slot": "01",
        "route_blocker_center_xy_m": list(map(float, outbound_xy)),
        "inbound_vessel_center_xy_m": list(map(float, inbound_xy)),
        "expected_bow_direction": expected_bow,
        "shelf_top_z_m": SHELF_TOP_Z,
        "support": "bench_standing",
        "workspace_bounds_m": [list(WORKSPACE_LOW_XYZ), list(WORKSPACE_HIGH_XYZ)],
        "legacy_panel_active": True,
        "spaced_bench": True,
        "n_active_objects": len(objects),
        "n_parked_decor": 0,
    }
    validate_spaced_layout(layout)
    return layout


def spaced_row_payload(family_id: str, intrusion_side: str) -> dict[str, Any]:
    """Drop-in replacement for ``v95_row_payload`` with tall spaced clutter."""
    palette = load_spaced_palette()
    layout = build_spaced_layout(
        palette, family_id=family_id, intrusion_side=intrusion_side
    )
    jitter = V95_VESSEL_JITTER[V95_LAYOUT_FAMILY_IDS.index(family_id)]
    return {
        "family": family_id,
        "layout_family_id": family_id,
        "layout_id": layout["layout_id"],
        "family_attempt": 0,
        "scene_template_house_index": 1,
        "max_sampling_retries": 12,
        "clutter_x_jitter_m": dict(jitter[0]),
        "clutter_y_jitter_m": dict(jitter[1]),
        "panel_face_jitter_m": 0.0,
        "panel_x_jitter_m": 0.0,
        "target_x_jitter_m": 0.0,
        "target_y_jitter_m": 0.0,
        "pact_clutter_palette": list(palette["palette"]),
        "pact_clutter_layout": layout,
        "pact_v107_spaced_bench": True,
        "environment_layout_version": ENVIRONMENT_VERSION_SPACED,
    }


def main() -> int:
    """Print a one-family smoke summary (no sim)."""
    import json

    palette = load_spaced_palette()
    layout = build_spaced_layout(
        palette, family_id="F0_target_side_stagger", intrusion_side="left"
    )
    print(
        json.dumps(
            {
                "environment": ENVIRONMENT_VERSION_SPACED,
                "layout_contract": LAYOUT_CONTRACT_VERSION,
                "palette_n": len(palette["palette"]),
                "active_n": len(layout["objects"]),
                "active": [
                    {
                        "slot": o["palette_slot"],
                        "uid": o["uid"],
                        "role": o["role"],
                        "xy": [round(o["center_m"][0], 3), round(o["center_m"][1], 3)],
                        "h": round(2 * o["half_m"][2], 3),
                    }
                    for o in layout["objects"]
                ],
                "selection_policy": palette["selection_policy"],
            },
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
