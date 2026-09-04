#!/usr/bin/env python3
"""Collect 200 accepted V10.7 spaced-bench demos with the V12/V10.11d camera schema.

Planner is ``PactPlaceCorridorPolicy``. Sampler is the frozen V10.6/V10.7
``PactPlaceCorridorV106Sampler``. Clutter is the spaced long-native variant.
Observations match V12 / V10.11d: ``FrankaSkinHybridCameraSystem`` with
``exo_camera_1`` (not renamed ``table_camera``), padded ``episode_00000000_*``
media, and per-frame ``extrinsic_cv`` / ``cam2world_gl`` / ``intrinsic_cv``.
"""

from __future__ import annotations

import hashlib
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
for _path in (ROOT / "scripts", ROOT / "submodules" / "molmospaces"):
    if str(_path) not in sys.path:
        sys.path.insert(0, str(_path))

from pact_place_v105_contract import (  # noqa: E402
    canonical_payload_sha256,
    empty_authorization,
    sha256_file,
    sha256_payload,
    write_immutable_create_only,
)
from pact_place_v106_geometry import POSE_OFFSETS_M, build_assembly  # noqa: E402
from pact_place_v107_contract import (  # noqa: E402
    SAMPLER_CLASS,
    cells,
)
from pact_place_v107_spaced_layout import (  # noqa: E402
    ENVIRONMENT_VERSION_SPACED,
    LAYOUT_CONTRACT_VERSION,
    spaced_row_payload,
)

CONTRACT_VERSION = "pact_place_v107_spaced_collection_200_hybrid_exo_v1"
ENVIRONMENT_VERSION = ENVIRONMENT_VERSION_SPACED
POLICY_CLASS = "PactPlaceCorridorPolicy"
PLAN_RELATIVE = "docs/PACT_PLACE_V107_QUALIFICATION_REPAIR_PLAN.md"

COLLECTION_STREAM = "pact_place_v107_spaced_collection_200"
COLLECTION_MASTER_SEED = 2026107200
SMOKE_STREAM = "pact_place_v107_spaced_smoke"
SMOKE_MASTER_SEED = 2026107201
HISTORICAL_MASTER_SEEDS = (
    2026107811,  # prior Batman v107_spaced datagen dump
    2026108002,
    2026101145,
)

INSPECT_CELLS = (
    ("F0_target_side_stagger", "left", "neg5"),
    ("F1_inner_panel_stagger", "right", "neg5"),
    ("F1_inner_panel_stagger", "right", "center"),
    ("F0_target_side_stagger", "right", "center"),
    ("F2_outer_panel_stagger", "left", "center"),
    ("F3_aperture_side_stagger", "right", "center"),
)
BASE_QUOTA_PER_CELL = 8
BONUS_CELLS = (
    ("F0_target_side_stagger", "left", "neg5"),
    ("F1_inner_panel_stagger", "right", "center"),
    ("F2_outer_panel_stagger", "left", "center"),
    ("F3_aperture_side_stagger", "right", "pos5"),
)
BONUS_PER_CELL = 2
TARGET_SUCCESSES = 200
MAX_SCIENTIFIC_ATTEMPTS = 1800
MAX_WALL_CLOCK_HOURS = 24.0
MAX_SAMPLING_RETRIES = 12
MIN_FREE_GIB = 40.0
DEFAULT_WORKERS = 1 if sys.platform == "darwin" else 4
DEFAULT_GPUS = 2

COLLECTION_ROOT = "diagnostics_output/pact_place_v107_spaced_n200"
DATASET_ROOT = "output/pact_place_corridor_v107_spaced_n200"
CAMERA_SYSTEM = "FrankaSkinHybridCameraSystem"
TABLE_CAMERA = "exo_camera_1"
TABLE_CAMERA_CALIBRATION_KEYS = (
    "extrinsic_cv",
    "cam2world_gl",
    "intrinsic_cv",
)
INHERITED_PENDANT = {"x_m": 0.800, "r_neg_m": 0.330, "r_pos_m": 0.300}
SCENES_DIR_RELATIVE = (
    "submodules/molmospaces/molmo_spaces/data_generation/custom_scenes"
)
SCENE_BY_POSE = {
    pose: {
        "relative": f"{SCENES_DIR_RELATIVE}/pact_place_corridor_v10_7_{pose}.xml",
    }
    for pose in ("neg5", "center", "pos5")
}

IMPLEMENTATION_PATHS = (
    "scripts/pact_place_v107_spaced_n200_collection_contract.py",
    "scripts/run_pact_place_v107_spaced_n200_collect.py",
    "scripts/pact_place_v107_spaced_layout.py",
    "scripts/run_pact_place_v1010_tablecam_validation.py",
    "scripts/run_pact_place_v108_collect.py",
    "scripts/pact_place_v107_contract.py",
)


def cell_key(family: str, side: str, pose: str) -> str:
    return f"{family}|{side}|{pose}"


def active_clutter_slots() -> tuple[str, ...]:
    payload = spaced_row_payload(*INSPECT_CELLS[0][:2])
    layout = payload.get("pact_clutter_layout") or {}
    slots = []
    for item in layout.get("objects") or []:
        slot = str(item.get("palette_slot") or "")
        if slot:
            slots.append(slot)
    return tuple(slots)


def quotas() -> dict[str, int]:
    result = {cell_key(*cell): BASE_QUOTA_PER_CELL for cell in cells()}
    for cell in BONUS_CELLS:
        key = cell_key(*cell)
        if key not in result:
            raise ValueError(f"unknown bonus cell {key}")
        result[key] += BONUS_PER_CELL
    if sum(result.values()) != TARGET_SUCCESSES:
        raise ValueError(f"quota sum {sum(result.values())} != {TARGET_SUCCESSES}")
    return result


def quota_totals() -> dict[str, Any]:
    totals = quotas()
    by_family: dict[str, int] = {}
    by_side: dict[str, int] = {}
    by_pose: dict[str, int] = {}
    for key, count in totals.items():
        family, side, pose = key.split("|")
        by_family[family] = by_family.get(family, 0) + count
        by_side[side] = by_side.get(side, 0) + count
        by_pose[pose] = by_pose.get(pose, 0) + count
    return {
        "by_cell": totals,
        "by_family": by_family,
        "by_side": by_side,
        "by_pose": by_pose,
        "total": sum(totals.values()),
        "inspect_cells": [cell_key(*cell) for cell in INSPECT_CELLS],
    }


def cell_seed(
    family: str, side: str, pose: str, attempt_index: int
) -> dict[str, int]:
    digest = hashlib.sha256(
        f"{COLLECTION_STREAM}:{COLLECTION_MASTER_SEED}:"
        f"{family}:{side}:{pose}:{int(attempt_index)}".encode()
    ).digest()
    value = int.from_bytes(digest[:8], "big")
    return {"seed_u32": value % (2**32), "seed_u64": value}


def attempt_id(family: str, side: str, pose: str, attempt_index: int) -> str:
    return hashlib.sha256(
        f"{COLLECTION_STREAM}:{COLLECTION_MASTER_SEED}:"
        f"{family}:{side}:{pose}:{int(attempt_index)}:attempt".encode()
    ).hexdigest()


def scene_bindings() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for pose, entry in SCENE_BY_POSE.items():
        relative = entry["relative"]
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(relative)
        out[pose] = {"relative": relative, "sha256": sha256_file(path)}
    return out


def assembly_bindings() -> dict[str, str]:
    selected = INHERITED_PENDANT
    return {
        pose: sha256_payload(
            build_assembly(
                float(selected["x_m"]),
                float(selected["r_neg_m"]),
                float(selected["r_pos_m"]),
                POSE_OFFSETS_M[pose],
                pose_id=pose,
            )
        )
        for pose in SCENE_BY_POSE
    }


def _seed_for(
    family: str,
    side: str,
    pose: str,
    attempt_index: int,
    *,
    stream: str,
    master_seed: int,
) -> dict[str, int]:
    digest = hashlib.sha256(
        f"{stream}:{master_seed}:{family}:{side}:{pose}:{int(attempt_index)}".encode()
    ).digest()
    value = int.from_bytes(digest[:8], "big")
    return {"seed_u32": value % (2**32), "seed_u64": value}


def build_row(
    family: str,
    side: str,
    pose: str,
    attempt_index: int,
    *,
    stream: str = COLLECTION_STREAM,
    master_seed: int = COLLECTION_MASTER_SEED,
    smoke_only: bool = False,
) -> dict[str, Any]:
    seed = _seed_for(
        family, side, pose, attempt_index, stream=stream, master_seed=master_seed
    )
    identifier = hashlib.sha256(
        f"{stream}:{master_seed}:{family}:{side}:{pose}:{int(attempt_index)}:attempt".encode()
    ).hexdigest()
    scenes = scene_bindings()
    assemblies = assembly_bindings()
    clutter = spaced_row_payload(family, side)
    row: dict[str, Any] = {
        "role_index": 0,
        "attempt_index": int(attempt_index),
        "family_id": family,
        "intrusion_side": side,
        "pose_id": pose,
        "pose_offset_m": POSE_OFFSETS_M[pose],
        "seed_stream": stream,
        "task_seed_u32": int(seed["seed_u32"]),
        "task_seed_u64": int(seed["seed_u64"]),
        "environment_version": ENVIRONMENT_VERSION,
        "contract_version": CONTRACT_VERSION,
        "layout_contract_version": LAYOUT_CONTRACT_VERSION,
        "sampler_class": SAMPLER_CLASS,
        "task_sampler_class": SAMPLER_CLASS,
        "pact_v106_x_m": float(INHERITED_PENDANT["x_m"]),
        "pact_v106_r_neg_m": float(INHERITED_PENDANT["r_neg_m"]),
        "pact_v106_r_pos_m": float(INHERITED_PENDANT["r_pos_m"]),
        "pact_v106_scene_sha256": scenes[pose]["sha256"],
        "pact_v106_assembly_sha256": assemblies[pose],
        "pact_v107_scene_relative": scenes[pose]["relative"],
        "max_sampling_retries": MAX_SAMPLING_RETRIES,
        "pact_v107_spaced_collection_target": TARGET_SUCCESSES,
        "pact_v107_table_camera_required": True,
        "smoke_only": bool(smoke_only),
        "attempt_id": identifier,
        "episode_id": identifier,
        "cell": cell_key(family, side, pose),
        **{
            key: (
                dict(value) if isinstance(value, dict)
                else list(value) if isinstance(value, list)
                else value
            )
            for key, value in clutter.items()
        },
    }
    row.pop("row_sha256", None)
    row["row_sha256"] = sha256_payload(row)
    return row


def streams_are_disjoint() -> dict[str, Any]:
    overlap = sorted(
        set((SMOKE_MASTER_SEED, COLLECTION_MASTER_SEED))
        & set(HISTORICAL_MASTER_SEEDS)
    )
    return {
        "smoke_master_seed": SMOKE_MASTER_SEED,
        "collection_master_seed": COLLECTION_MASTER_SEED,
        "historical_master_seeds": list(HISTORICAL_MASTER_SEEDS),
        "overlap": overlap,
        "disjoint": not overlap and COLLECTION_MASTER_SEED != SMOKE_MASTER_SEED,
    }


def implementation_bindings() -> dict[str, Any]:
    bindings: dict[str, Any] = {}
    for relative in IMPLEMENTATION_PATHS:
        path = ROOT / relative
        if not path.is_file():
            raise FileNotFoundError(path)
        bindings[relative] = sha256_file(path)
    return {
        "files": bindings,
        "digest": sha256_payload(sorted(bindings.items())),
    }


def build_contract() -> dict[str, Any]:
    document = {
        **empty_authorization(),
        "schema_version": CONTRACT_VERSION,
        "environment_version": ENVIRONMENT_VERSION,
        "sampler_class": SAMPLER_CLASS,
        "policy_class": POLICY_CLASS,
        "plan": PLAN_RELATIVE,
        "owner_override": {
            "authorized": True,
            "requested_target_successes": TARGET_SUCCESSES,
            "does_not_claim_phase0_pass": True,
            "retain_failed_rows": True,
            "uses_v12_v1011d_hybrid_exo_schema": True,
        },
        "implementation": implementation_bindings(),
        "streams": streams_are_disjoint(),
        "pendant": dict(INHERITED_PENDANT),
        "scenes": scene_bindings(),
        "collection": {
            "target_successes": TARGET_SUCCESSES,
            "quota_totals": quota_totals(),
            "max_scientific_attempts": MAX_SCIENTIFIC_ATTEMPTS,
            "max_wall_clock_hours": MAX_WALL_CLOCK_HOURS,
            "one_in_flight_per_cell": True,
            "strict_clean_only": True,
            "retain_failed_rows": True,
        },
        "observations": {
            "camera_system": CAMERA_SYSTEM,
            "wrist_rgb": True,
            "wrist_depth": True,
            "table_camera_rgb": TABLE_CAMERA,
            "table_camera_depth": True,
            "table_camera_calibration_keys": list(TABLE_CAMERA_CALIBRATION_KEYS),
            "raw_proximity_sensors": 40,
            "contact_audit_storage": "summary_only",
            "media_names": [
                "episode_00000000_wrist_camera.mp4",
                "episode_00000000_wrist_camera_depth.mp4",
                "episode_00000000_exo_camera_1.mp4",
                "episode_00000000_exo_camera_1_depth.mp4",
                "episode_00000000_sensors_depth8_heatmap.mp4",
            ],
        },
        "active_clutter_slots": list(active_clutter_slots()),
        "layout_contract_version": LAYOUT_CONTRACT_VERSION,
    }
    document["payload_sha256"] = canonical_payload_sha256(document)
    return document


def write_contract(path: Path) -> None:
    write_immutable_create_only(path, build_contract())


__all__ = [name for name in globals() if name.isupper()] + [
    "attempt_id",
    "build_contract",
    "build_row",
    "cell_key",
    "cell_seed",
    "cells",
    "quota_totals",
    "quotas",
    "scene_bindings",
    "streams_are_disjoint",
    "implementation_bindings",
    "write_contract",
]
