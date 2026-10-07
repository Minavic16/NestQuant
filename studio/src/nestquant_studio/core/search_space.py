"""Deterministic candidate identity + search-space expansion."""
from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from dataclasses import dataclass
from itertools import product
from typing import Any


def _canonical(obj: Any) -> str:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False)


def candidate_key(params: dict) -> str:
    return hashlib.sha256(_canonical(params).encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class SearchSpace:
    """Generic multi-axis search space. Axis values come from data, not code constants."""

    definition: dict

    def axis_values(self, name: str, spec: dict) -> list:
        t = spec["type"]
        if t == "enum":
            return list(spec["values"])
        if t == "int_range":
            lo, hi, step = int(spec["min"]), int(spec["max"]), int(spec.get("step", 1))
            if step <= 0:
                raise ValueError("step must be > 0")
            return list(range(lo, hi + 1, step))
        if t == "float_range":
            lo, hi, step = float(spec["min"]), float(spec["max"]), float(spec["step"])
            if step <= 0:
                raise ValueError("step must be > 0")
            vals: list[float] = []
            x = lo
            for _ in range(1_000_000):
                if x > hi + 1e-12:
                    break
                vals.append(round(x, 10))
                x += step
            return vals
        raise ValueError(f"unsupported axis type: {t}")

    def iter_params(self) -> Iterator[dict]:
        axes: dict = self.definition.get("axes") or {}
        names = sorted(axes.keys())
        value_lists = [self.axis_values(n, axes[n]) for n in names]
        exclude = {_canonical(e) for e in self.definition.get("exclude") or []}
        include = self.definition.get("include") or []
        if names:
            for combo in product(*value_lists):
                params = dict(zip(names, combo))
                if _canonical(params) in exclude:
                    continue
                yield params
        for extra in include:
            yield dict(extra)

    def materialize(self, limit: int | None = None) -> list[tuple[str, dict]]:
        out: list[tuple[str, dict]] = []
        for params in self.iter_params():
            out.append((candidate_key(params), params))
            if limit is not None and len(out) >= limit:
                break
        return out

    def count(self, limit: int | None = None) -> int:
        return len(self.materialize(limit=limit))