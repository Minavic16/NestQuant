from __future__ import annotations

import uuid


def new_id(prefix: str = "") -> str:
    u = str(uuid.uuid4())
    return f"{prefix}{u}" if prefix else u