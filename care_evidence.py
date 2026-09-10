#!/usr/bin/env python3
"""Deterministic, offline checks for a small observation-event schema."""
from __future__ import annotations

import argparse
import csv
import json
from datetime import datetime
from pathlib import Path

REQUIRED = ("event_id", "observed_at", "timezone", "source", "recorder_role", "observation", "interpretation", "status", "corrects", "schema_version")
STATUSES = {"observed", "not_recorded", "not_occurring"}
RULES = {item["id"]: item for item in json.loads((Path(__file__).parent / "rules.json").read_text(encoding="utf-8"))}


def check_event(event: dict) -> list[dict]:
    issues: list[dict] = []
    missing = [key for key in REQUIRED if key not in event]
    if missing:
        issues.append({"rule": "required_fields", "message": f"不足: {', '.join(missing)}"})

    try:
        parsed_at = datetime.fromisoformat(str(event.get("observed_at", "")).replace("Z", "+00:00"))
        if parsed_at.tzinfo is None:
            raise ValueError("timezone offset missing")
    except ValueError:
        issues.append({"rule": "timestamp_timezone", "message": "observed_at はISO 8601形式で必要です"})
    if not event.get("timezone"):
        issues.append({"rule": "timestamp_timezone", "message": "timezone がありません"})

    observation = str(event.get("observation", "")).strip()
    interpretation = str(event.get("interpretation", "")).strip()
    if observation and any(token in observation.lower() for token in ("と思う", "かもしれない", "likely", "maybe")):
        issues.append({"rule": "observation_interpretation", "message": "観察欄に推測表現があります。解釈欄へ分けてください"})
    if event.get("status") == "observed" and not observation:
        issues.append({"rule": "observation_interpretation", "message": "observed には観察内容が必要です"})
    if interpretation and not observation and event.get("status") == "observed":
        issues.append({"rule": "observation_interpretation", "message": "解釈だけで、観察の根拠がありません"})

    if not event.get("source") or not event.get("recorder_role"):
        issues.append({"rule": "provenance", "message": "source と recorder_role を記録してください"})

    status = event.get("status")
    if status not in STATUSES:
        issues.append({"rule": "missingness_status", "message": f"status は {sorted(STATUSES)} のいずれかです"})
    if status == "not_recorded" and (observation or interpretation):
        issues.append({"rule": "missingness_status", "message": "not_recorded に観察・解釈を入れないでください"})

    corrects = event.get("corrects")
    if corrects is not None and not isinstance(corrects, (str, list)):
        issues.append({"rule": "correction_reference", "message": "corrects は元イベントIDまたはID配列です"})
    return issues


def inspect(path: Path) -> dict:
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8") as handle:
            events = list(csv.DictReader(handle))
        for event in events:
            if isinstance(event.get("corrects"), str):
                event["corrects"] = [item for item in event["corrects"].split(";") if item]
            if isinstance(event.get("schema_version"), str) and event["schema_version"].isdigit():
                event["schema_version"] = int(event["schema_version"])
    else:
        payload = json.loads(path.read_text(encoding="utf-8"))
        events = payload if isinstance(payload, list) else payload.get("events", [payload])
    results = []
    for event in events:
        issues = check_event(event)
        results.append({"event_id": event.get("event_id"), "issues": issues})
    return {"tool": "open-care-evidence-toolkit-mvp", "events": len(results), "issues": sum(len(item["issues"]) for item in results), "results": results}


def render(report: dict, fmt: str) -> str:
    if fmt == "json":
        return json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    lines = [f"# データ品質サマリー\n", f"- イベント数: {report['events']}", f"- 問題数: {report['issues']}", ""]
    for item in report["results"]:
        lines.append(f"## {item['event_id'] or '(event_idなし)'}")
        if not item["issues"]:
            lines.append("✅ 6規則を通過")
        else:
            for issue in item["issues"]:
                lines.append(f"- ⚠️ {RULES[issue['rule']]['ja']}: {issue['message']}")
        lines.append("")
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description="Offline checks for synthetic care evidence events")
    parser.add_argument("input", type=Path)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    args = parser.parse_args()
    print(render(inspect(args.input), args.format), end="")


if __name__ == "__main__":
    main()
