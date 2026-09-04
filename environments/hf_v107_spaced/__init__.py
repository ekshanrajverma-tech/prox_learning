#!/usr/bin/env python3
"""Environment for Hugging Face ``data/v107_spaced`` (200 accepted episodes).

This is ``pact_place_corridor_v10_7_spaced_bench`` driven by
``PactPlaceCorridorV106Sampler`` across three frozen pendant poses, so it is a
different sampler family from either of the other published splits.
"""

from __future__ import annotations

from ..spec import EnvSpec

SPEC = EnvSpec(
    hub_split="v107_spaced",
    hub_path="data/v107_spaced",
    n_episodes=200,
    environment_version="pact_place_corridor_v10_7_spaced_bench",
    sampler_class="PactPlaceCorridorV106Sampler",
    policy_class="PactPlaceCorridorPolicy",
    schema_version="pact_place_v107_spaced_accepted_v1",
    scene_relative=(
        "custom_scenes/pact_place_corridor_v10_7_neg5.xml",
        "custom_scenes/pact_place_corridor_v10_7_center.xml",
        "custom_scenes/pact_place_corridor_v10_7_pos5.xml",
    ),
    collect_entrypoint="scripts/run_pact_place_v107_spaced_n200_collect.py",
    contract_module="pact_place_v107_spaced_n200_collection_contract",
    molmospaces_commit="70dedc07f34ed7f8335aed7f694ddef7ef823d3d",
    class_fingerprint="9c0ef4ccdcac32ce0a325fd2956e1209affb47cd974293b4d75b2ff3644c0579",
    notes=(
        "200 accepted of 267 attempts, quotas met on all 24 cells: four stagger "
        "families crossed with two approach sides and three pendant poses, "
        "100 left / 100 right. One scene per pose; the contract resolves them "
        "under the submodule rather than custom_scenes/, and the two copies are "
        "byte-identical, so the recorded sha256 is the same either way. This "
        "collect "
        "writes its own contract.json into the collection root on first run, "
        "so unlike v1011d it binds no gate artifacts from the checkout. Rows "
        "carry the same hybrid exo schema as v12 and v1011d, so the same "
        "conversion path applies. The closeout reports phase0_passed false and "
        "every authorizes_* flag false: a development collection that does not "
        "self-authorize training or evaluation."
    ),
)

__all__ = ["SPEC"]
