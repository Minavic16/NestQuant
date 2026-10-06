"""Minimal, dependency-free metrics primitives."""
from __future__ import annotations

import threading
from typing import Dict


class Counter:
    def __init__(self, name: str, value: float = 0.0) -> None:
        self.name = name
        self._v = value
        self._lock = threading.Lock()

    def inc(self, n: float = 1.0) -> None:
        with self._lock:
            self._v += n

    def get(self) -> float:
        return self._v


class Gauge:
    def __init__(self, name: str, value: float = 0.0) -> None:
        self.name = name
        self._v = value
        self._lock = threading.Lock()

    def set(self, v: float) -> None:
        with self._lock:
            self._v = v

    def get(self) -> float:
        return self._v


class Histogram:
    def __init__(self, name: str) -> None:
        self.name = name
        self._values: list[float] = []
        self._lock = threading.Lock()

    def observe(self, v: float) -> None:
        with self._lock:
            self._values.append(v)

    def count(self) -> int:
        return len(self._values)

    def sum(self) -> float:
        return sum(self._values)


class Metrics:
    def __init__(self) -> None:
        self._operators: Dict[str, object] = {}
        self._lock = threading.Lock()

    def counter(self, name: str) -> Counter:
        with self._lock:
            return self._operators.setdefault(name, Counter(name))  # type: ignore[return-value]

    def gauge(self, name: str) -> Gauge:
        with self._lock:
            return self._operators.setdefault(name, Gauge(name))  # type: ignore[return-value]

    def histogram(self, name: str) -> Histogram:
        with self._lock:
            return self._operators.setdefault(name, Histogram(name))  # type: ignore[return-value]

    def snapshot(self) -> dict:
        out: dict = {}
        for name, op in self._operators.items():
            if isinstance(op, (Counter, Gauge)):
                out[name] = op.get()
            elif isinstance(op, Histogram):
                out[name] = {"count": op.count(), "sum": op.sum()}
        return out
