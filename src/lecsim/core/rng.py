"""Named, seeded random streams.

Every stochastic draw in lecsim comes from ``RngStreams.get(name, ...)``. A stream is
derived from the run seed and a hash of its name, so adding a new stream (or a new
agent) never shifts the draws of existing ones.
"""

from __future__ import annotations

import hashlib

import numpy as np


class RngStreams:
    def __init__(self, seed: int) -> None:
        self.seed = seed
        self._streams: dict[str, np.random.Generator] = {}

    def get(self, *name: str) -> np.random.Generator:
        key = "/".join(name)
        if key not in self._streams:
            digest = hashlib.sha256(key.encode()).digest()
            spawn_key = tuple(int.from_bytes(digest[i : i + 4], "little") for i in range(0, 16, 4))
            seq = np.random.SeedSequence(self.seed, spawn_key=spawn_key)
            self._streams[key] = np.random.Generator(np.random.PCG64(seq))
        return self._streams[key]
