from __future__ import annotations

import json
import os
import re

_CHECKPOINT_DIR = os.path.normpath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "scripts", "checkpoints")
)

class CheckpointManager:
    def __init__(self, auction_house: str | None, checkpoint_kind: str = "all_items") -> None:
        slug = re.sub(r"[^\w]", "_", auction_house.lower()) if auction_house else "all"
        kind = re.sub(r"[^\w]", "_", checkpoint_kind.lower())
        os.makedirs(_CHECKPOINT_DIR, exist_ok=True)
        self._path = os.path.join(_CHECKPOINT_DIR, f"matching_{slug}_{kind}.json")

    def load(self) -> int:
        """Return last completed checkpoint id, or -1 if no checkpoint exists."""
        if not os.path.exists(self._path):
            return -1
        with open(self._path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return int(data.get("last_completed_offset", -1))

    def save(self, offset: int) -> None:
        """Persist the last fully completed checkpoint id."""
        with open(self._path, "w", encoding="utf-8") as f:
            json.dump({"last_completed_offset": offset}, f)

    def clear(self) -> None:
        """Delete the checkpoint file (triggers a full restart on next run)."""
        if os.path.exists(self._path):
            os.remove(self._path)
