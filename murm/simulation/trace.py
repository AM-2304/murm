"""
Append-only JSONL trace writer for simulation actions.
Each line is a self-contained JSON record of one agent action.
The trace is the ground truth record for the report agent and post-hoc analysis.
"""

from __future__ import annotations

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class TraceWriter:
    """
    Buffered JSONL writer. Writes are buffered in memory and flushed
    either explicitly or when the buffer reaches the flush threshold.
    """

    def __init__(self, path: Path, flush_every: int = 50) -> None:
        self._path = path
        self._flush_every = flush_every
        self._buffer: list[str] = []
        path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, action: dict) -> None:
        self._buffer.append(json.dumps(action, ensure_ascii=False))
        if len(self._buffer) >= self._flush_every:
            self.flush()

    def flush(self) -> None:
        if not self._buffer:
            return
        with self._path.open("a", encoding="utf-8") as f:
            f.write("\n".join(self._buffer) + "\n")
        self._buffer.clear()

    def read_all(self) -> list[dict]:
        """Read the complete trace back as a list of action dicts."""
        if not self._path.exists():
            return []
        records = []
        with self._path.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        logger.warning("Corrupt trace line skipped: %s", line[:80])
        return records

    def sample(self, n: int = 100) -> list[dict]:
        """Return a representative sample of the trace for use in report prompts."""
        all_records = self.read_all()
        if len(all_records) <= n:
            return all_records
        # Return evenly spaced records across the full run
        step = len(all_records) // n
        return all_records[::step][:n]
