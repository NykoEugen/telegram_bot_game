"""Daily and weekly task definitions and progress helpers."""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Literal, Tuple

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

TaskFrequency = Literal["daily", "weekly"]


@dataclass(frozen=True)
class DailyTaskDefinition:
    """Immutable representation of a daily or weekly task."""

    id: str
    name: str
    description: str
    icon: str
    metric: str
    target: int
    reward: Dict[str, int]
    frequency: TaskFrequency


class DailyTaskCatalog:
    """Loads daily and weekly task definitions from JSON."""

    _definitions: Dict[str, List[DailyTaskDefinition]] | None = None

    @classmethod
    def _load_definitions(cls) -> Dict[str, List[DailyTaskDefinition]]:
        if cls._definitions is not None:
            return cls._definitions

        root_path = Path(__file__).resolve().parents[1]
        candidate_paths = [
            root_path / "data" / "dailies.json",
            root_path / "app" / "data" / "dailies.json",
        ]

        data_path: Path | None = None
        for candidate in candidate_paths:
            if candidate.exists():
                data_path = candidate
                break

        if data_path is None:
            raise FileNotFoundError(
                "Не знайдено файл з щоденними завданнями (data/dailies.json)."
            )

        with data_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        definitions: Dict[str, List[DailyTaskDefinition]] = {"daily": [], "weekly": []}
        for frequency in ("daily", "weekly"):
            for raw in payload.get(frequency, []):
                definitions[frequency].append(
                    DailyTaskDefinition(
                        id=raw["id"],
                        name=raw["name"],
                        description=raw["description"],
                        icon=raw.get("icon", "📌"),
                        metric=raw["metric"],
                        target=int(raw["target"]),
                        reward=raw.get("reward", {}),
                        frequency=frequency,  # type: ignore[arg-type]
                    )
                )

        cls._definitions = definitions
        return cls._definitions

    @classmethod
    def all_tasks(cls, frequency: TaskFrequency) -> List[DailyTaskDefinition]:
        return list(cls._load_definitions()[frequency])

    @classmethod
    def by_id(cls, task_id: str) -> DailyTaskDefinition | None:
        for collection in cls._load_definitions().values():
            for definition in collection:
                if definition.id == task_id:
                    return definition
        return None

    @classmethod
    def by_frequency_and_metric(cls, frequency: TaskFrequency, metric: str) -> List[DailyTaskDefinition]:
        return [definition for definition in cls.all_tasks(frequency) if definition.metric == metric]

    @classmethod
    def by_metric(cls, metric: str) -> List[DailyTaskDefinition]:
        tasks: List[DailyTaskDefinition] = []
        for frequency in ("daily", "weekly"):
            tasks.extend(cls.by_frequency_and_metric(frequency, metric))
        return tasks


@dataclass
class TaskProgress:
    definition: DailyTaskDefinition
    progress: int
    completed: bool
    completed_at: str | None

    @property
    def completion_percent(self) -> int:
        if self.definition.target <= 0:
            return 100
        return min(100, int((self.progress / self.definition.target) * 100))


class DailyTaskTracker:
    """Persists per-hero task progress and handles reset logic."""

    @staticmethod
    def _now_iso() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    async def ensure_progress_structures(session: AsyncSession, hero) -> None:
        """Make sure hero has default progress JSON fields."""
        needs_commit = False
        if not hero.daily_progress:
            hero.daily_progress = "{}"
            needs_commit = True
        if not hero.weekly_progress:
            hero.weekly_progress = "{}"
            needs_commit = True
        if not hero.daily_reset_at:
            hero.daily_reset_at = DailyTaskTracker._now_iso()
            needs_commit = True
        if not hero.weekly_reset_at:
            hero.weekly_reset_at = DailyTaskTracker._now_iso()
            needs_commit = True
        if needs_commit:
            session.add(hero)
            await session.commit()
            await session.refresh(hero)

    @staticmethod
    def _needs_reset(last_reset: str | None, frequency: TaskFrequency) -> bool:
        if not last_reset:
            return True
        try:
            last_dt = datetime.fromisoformat(last_reset)
        except ValueError:
            return True
        now = datetime.now(timezone.utc)
        if frequency == "daily":
            return now.date() > last_dt.date()
        # Weekly reset on Monday 00:00 UTC
        last_week = last_dt.isocalendar()[:2]
        current_week = now.isocalendar()[:2]
        return current_week != last_week

    @staticmethod
    def _reset_timestamp(frequency: TaskFrequency) -> str:
        now = datetime.now(timezone.utc)
        if frequency == "daily":
            return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        return now.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()

    @staticmethod
    def _coerce_progress_map(raw: str) -> Dict[str, Dict[str, str | int | bool]]:
        try:
            data = json.loads(raw or "{}")
            if isinstance(data, dict):
                return data
        except json.JSONDecodeError:
            pass
        return {}

    @staticmethod
    def _dump_progress_map(data: Dict[str, Dict[str, str | int | bool]]) -> str:
        return json.dumps(data, ensure_ascii=False)

    @staticmethod
    async def reset_if_needed(session: AsyncSession, hero) -> None:
        """Reset daily/weekly progress if the reset timestamps have passed."""
        await DailyTaskTracker.ensure_progress_structures(session, hero)

        changed = False
        daily_needs_reset = DailyTaskTracker._needs_reset(hero.daily_reset_at, "daily")
        weekly_needs_reset = DailyTaskTracker._needs_reset(hero.weekly_reset_at, "weekly")

        if daily_needs_reset:
            hero.daily_progress = "{}"
            hero.daily_reset_at = DailyTaskTracker._reset_timestamp("daily")
            changed = True
        if weekly_needs_reset:
            hero.weekly_progress = "{}"
            hero.weekly_reset_at = DailyTaskTracker._reset_timestamp("weekly")
            changed = True

        if changed:
            session.add(hero)
            await session.commit()
            await session.refresh(hero)

    @staticmethod
    async def record_metric(session: AsyncSession, hero, metric: str, amount: int = 1) -> Tuple[List[DailyTaskDefinition], List[DailyTaskDefinition]]:
        """Increment progress for matching tasks and return lists of newly completed daily/weekly tasks."""
        await DailyTaskTracker.reset_if_needed(session, hero)

        daily_progress = DailyTaskTracker._coerce_progress_map(hero.daily_progress)
        weekly_progress = DailyTaskTracker._coerce_progress_map(hero.weekly_progress)

        newly_completed_daily: List[DailyTaskDefinition] = []
        newly_completed_weekly: List[DailyTaskDefinition] = []

        for definition in DailyTaskCatalog.by_metric(metric):
            progress_map = daily_progress if definition.frequency == "daily" else weekly_progress
            entry = progress_map.setdefault(
                definition.id,
                {"progress": 0, "completed": False, "completed_at": None},
            )
            if entry.get("completed"):
                continue
            entry["progress"] = int(entry.get("progress", 0)) + amount
            if entry["progress"] >= definition.target:
                entry["completed"] = True
                entry["completed_at"] = DailyTaskTracker._now_iso()
                if definition.frequency == "daily":
                    newly_completed_daily.append(definition)
                else:
                    newly_completed_weekly.append(definition)

        hero.daily_progress = DailyTaskTracker._dump_progress_map(daily_progress)
        hero.weekly_progress = DailyTaskTracker._dump_progress_map(weekly_progress)
        session.add(hero)
        await session.commit()
        await session.refresh(hero)

        return newly_completed_daily, newly_completed_weekly

    @staticmethod
    async def get_progress(session: AsyncSession, hero, frequency: TaskFrequency) -> List[TaskProgress]:
        """Return progress entries for a hero for the requested frequency."""
        await DailyTaskTracker.reset_if_needed(session, hero)

        raw_map = hero.daily_progress if frequency == "daily" else hero.weekly_progress
        progress_map = DailyTaskTracker._coerce_progress_map(raw_map)

        progress_entries: List[TaskProgress] = []
        for definition in DailyTaskCatalog.all_tasks(frequency):
            entry = progress_map.get(definition.id, {})
            progress_entries.append(
                TaskProgress(
                    definition=definition,
                    progress=int(entry.get("progress", 0)),
                    completed=bool(entry.get("completed", False)),
                    completed_at=entry.get("completed_at") if entry.get("completed") else None,
                )
            )

        return progress_entries
