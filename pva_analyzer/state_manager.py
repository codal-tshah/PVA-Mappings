"""
PVA Workbench Analyzer — State Manager (resume support)
"""
import json
from pathlib import Path
from datetime import datetime
from config import STATE_DIR
from logger import get_logger

log = get_logger("state_manager")


class StateManager:
    def __init__(self, workbook_path: str):
        safe = Path(workbook_path).stem.replace(" ", "_")
        self.state_file = STATE_DIR / f"{safe}_state.json"
        self.state = self._load()

    def _load(self) -> dict:
        if self.state_file.exists():
            with open(self.state_file) as f:
                state = json.load(f)
            log.info(f"Resumed state: {len(state.get('completed', []))} tabs already done")
            return state
        return {
            "started_at": datetime.now().isoformat(),
            "completed": [],
            "failed": [],
            "skipped": [],
            "tab_stats": {},
        }

    def save(self):
        self.state["updated_at"] = datetime.now().isoformat()
        with open(self.state_file, "w") as f:
            json.dump(self.state, f, indent=2)

    def is_done(self, tab: str) -> bool:
        return tab in self.state["completed"]

    def mark_done(self, tab: str, stats: dict):
        if tab not in self.state["completed"]:
            self.state["completed"].append(tab)
        self.state["tab_stats"][tab] = {**stats, "finished_at": datetime.now().isoformat()}
        self.save()
        log.info(f"✓ {tab} — {stats}")

    def mark_failed(self, tab: str, error: str):
        self.state["failed"].append({"tab": tab, "error": error, "at": datetime.now().isoformat()})
        self.save()
        log.error(f"✗ {tab} — {error}")

    def mark_skipped(self, tab: str, reason: str):
        self.state["skipped"].append({"tab": tab, "reason": reason})
        self.save()
        log.warning(f"~ {tab} skipped — {reason}")

    def summary(self) -> dict:
        return {
            "completed": len(self.state["completed"]),
            "failed":    len(self.state["failed"]),
            "skipped":   len(self.state["skipped"]),
            "tabs":      self.state["tab_stats"],
        }

    def reset(self):
        if self.state_file.exists():
            self.state_file.unlink()
        self.state = self._load()
        log.info("State reset.")
