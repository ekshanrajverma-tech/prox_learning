#!/usr/bin/env python3
"""A fingerprint of the code an environment actually resolves.

    python -m environments.fingerprint            # every environment
    python -m environments.fingerprint v107_spaced

The repo carries a single molmospaces pin shared by every environment, so moving
it to satisfy a new one can silently change an old one. That is not theoretical:
the move to ``70dedc07`` rewrote ``PactPlaceCorridorV5Sampler`` and
``PactPlaceCorridorV9Sampler``, two ancestors ``hf_v12`` inherits from, and the
only thing that caught it was reading the diff by hand.

``EnvSpec.class_fingerprint`` closes that hole. It hashes the source of every
class the environment resolves — the sampler, the policy, its config, and each
ancestor molmo_spaces defines — so ``verify_hf_env`` fails when a pin move
changes any of them. Comparing the commit strings alone would not: bump the pin,
update each spec to match, and the check passes while the resolved behaviour has
changed underneath.

Read it as *what this checkout resolves*, not *what produced the dump*. For
``hf_v12`` those differ on purpose: it was collected at ``ed045d7`` and resolves
``70dedc07``, whose V5 and V9 samplers changed additively. Its fingerprint is
therefore the pin's, and the argument for why that is safe lives in its spec
notes. What the fingerprint guarantees is that the difference stays the reviewed
one.

When a fingerprint legitimately changes, print the new one and paste it into the
spec in the same commit that moves the pin, so review sees both together.
"""

from __future__ import annotations

import hashlib
import inspect
import sys

from .spec import EnvSpec

MOLMO = "molmo_spaces"


def _resolved_classes(spec: EnvSpec) -> list[type]:
    """Every molmo_spaces class this environment's behaviour depends on.

    The sampler and policy named by the spec, the policy's config class, and the
    ancestors of each. Classes from outside molmo_spaces are skipped: they move
    with the interpreter and the conda env, not with the pin.
    """
    from molmo_spaces.tasks import enclosure_reach

    seeds = [getattr(enclosure_reach, spec.sampler_class), getattr(enclosure_reach, spec.policy_class)]
    config = getattr(enclosure_reach, spec.policy_class + "Config", None)
    if config is not None:
        seeds.append(config)

    seen: dict[str, type] = {}
    for seed in seeds:
        for cls in seed.__mro__:
            if getattr(cls, "__module__", "").split(".")[0] == MOLMO:
                seen[f"{cls.__module__}.{cls.__qualname__}"] = cls
    return [seen[k] for k in sorted(seen)]


def compute(spec: EnvSpec) -> str:
    digest = hashlib.sha256()
    for cls in _resolved_classes(spec):
        digest.update(f"{cls.__module__}.{cls.__qualname__}\0".encode())
        digest.update(inspect.getsource(cls).encode())
        digest.update(b"\0")
    return digest.hexdigest()


def main(argv: list[str]) -> int:
    from . import ROOT, all_specs

    sys.path.insert(0, str(ROOT / "submodules" / "molmospaces"))
    specs = all_specs()
    for name in argv or sorted(specs):
        spec = specs[name]
        classes = _resolved_classes(spec)
        print(f"{spec.hub_split}: {compute(spec)}")
        print(f"    over {len(classes)} classes: {', '.join(c.__qualname__ for c in classes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
