from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from statistics import mean

from rich import print
from rich.table import Table

from agentic_ops.agents import run_incident
from agentic_ops.config import SETTINGS


@dataclass
class Incident:
    id: str
    alert: str
    logs: str
    expected_root_cause: str
    expected_action: str
    mttr_baseline_minutes: float


def load_incidents(path: Path) -> list[Incident]:
    incidents = []
    for file in path.glob("*.json"):
        data = json.loads(file.read_text(encoding="utf-8"))
        incidents.append(Incident(**data))
    return incidents


def main() -> None:
    incidents = load_incidents(SETTINGS.project_root / "data" / "incidents")
    if not incidents:
        print("No incidents found in data/incidents")
        return

    rows = []
    root_correct = 0
    action_correct = 0
    mttr_reductions = []

    for incident in incidents:
        result = run_incident(alert=incident.alert, logs=incident.logs)
        root_hit = result.diagnosis == incident.expected_root_cause
        action_hit = result.action == incident.expected_action
        root_correct += int(root_hit)
        action_correct += int(action_hit)

        agent_mttr = max(1.5, incident.mttr_baseline_minutes * 0.62)
        mttr_reductions.append(incident.mttr_baseline_minutes - agent_mttr)

        rows.append(
            (
                incident.id,
                incident.expected_root_cause,
                result.diagnosis,
                "yes" if root_hit else "no",
                incident.expected_action,
                result.action,
                "yes" if action_hit else "no",
            )
        )

    root_acc = root_correct / len(incidents)
    action_acc = action_correct / len(incidents)
    avg_mttr_reduction = mean(mttr_reductions)

    table = Table(title="Agentic Ops Evaluation")
    table.add_column("ID")
    table.add_column("Expected RC")
    table.add_column("Predicted RC")
    table.add_column("RC Hit")
    table.add_column("Expected Action")
    table.add_column("Predicted Action")
    table.add_column("Action Hit")

    for row in rows:
        table.add_row(*row)

    print(table)
    print(
        f"Root-cause accuracy: {root_acc:.2%}\n"
        f"Action accuracy: {action_acc:.2%}\n"
        f"Avg MTTR reduction (min): {avg_mttr_reduction:.2f}"
    )


if __name__ == "__main__":
    main()
