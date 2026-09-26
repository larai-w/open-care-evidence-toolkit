#!/usr/bin/env python3
"""Deterministic, offline checks for a small observation-event schema."""
from __future__ import annotations

import argparse
import csv
import json
import sys
from datetime import datetime
from pathlib import Path

REQUIRED = ("event_id", "observed_at", "timezone", "source", "recorder_role", "observation", "interpretation", "status", "corrects", "schema_version")
STATUSES = {"observed", "not_recorded", "not_occurring"}
RULES = {item["id"]: item for item in json.loads((Path(__file__).parent / "rules.json").read_text(encoding="utf-8"))}


def check_event(event: dict, lang: str = "en") -> list[dict]:
    def message(en: str, ja: str) -> str:
        return ja if lang == "ja" else en

    issues: list[dict] = []
    missing = [key for key in REQUIRED if key not in event]
    if missing:
        issues.append({"rule": "required_fields", "message": message(f"Missing fields: {', '.join(missing)}", f"不足: {', '.join(missing)}")})

    try:
        parsed_at = datetime.fromisoformat(str(event.get("observed_at", "")).replace("Z", "+00:00"))
        if parsed_at.tzinfo is None:
            raise ValueError("timezone offset missing")
    except ValueError:
        issues.append({"rule": "timestamp_timezone", "message": message("observed_at must be an ISO 8601 timestamp with a timezone offset", "observed_at はISO 8601形式で必要です")})
    if not event.get("timezone"):
        issues.append({"rule": "timestamp_timezone", "message": message("timezone is missing", "timezone がありません")})

    observation = str(event.get("observation", "")).strip()
    interpretation = str(event.get("interpretation", "")).strip()
    if observation and any(token in observation.lower() for token in ("と思う", "かもしれない", "likely", "maybe")):
        issues.append({"rule": "observation_interpretation", "message": message("Move speculative wording from observation to interpretation", "観察欄に推測表現があります。解釈欄へ分けてください")})
    if event.get("status") == "observed" and not observation:
        issues.append({"rule": "observation_interpretation", "message": message("observed requires observation text", "observed には観察内容が必要です")})
    if interpretation and not observation and event.get("status") == "observed":
        issues.append({"rule": "observation_interpretation", "message": message("An interpretation needs an observation when status is observed", "解釈だけで、観察の根拠がありません")})

    if not event.get("source") or not event.get("recorder_role"):
        issues.append({"rule": "provenance", "message": message("Record source and recorder_role", "source と recorder_role を記録してください")})

    status = event.get("status")
    if not isinstance(status, str) or status not in STATUSES:
        issues.append({"rule": "missingness_status", "message": message(f"status must be one of {sorted(STATUSES)}", f"status は {sorted(STATUSES)} のいずれかです")})
    if status == "not_recorded" and (observation or interpretation):
        issues.append({"rule": "missingness_status", "message": message("not_recorded must not contain observation or interpretation text", "not_recorded に観察・解釈を入れないでください")})

    corrects = event.get("corrects")
    if corrects is not None and not isinstance(corrects, (str, list)):
        issues.append({"rule": "correction_reference", "message": message("corrects must be an earlier event ID or a list of IDs", "corrects は元イベントIDまたはID配列です")})
    return issues


def inspect(path: Path, lang: str = "en") -> dict:
    if path.suffix.lower() == ".csv":
        with path.open(newline="", encoding="utf-8-sig") as handle:
            reader = csv.DictReader(handle, strict=True)
            fields = reader.fieldnames
            if not fields or any(not field.strip() for field in fields) or len(fields) != len(set(fields)):
                raise ValueError("CSV requires non-empty, unique column names")
            events = []
            for event in reader:
                if None in event or any(value is None for value in event.values()):
                    raise ValueError(f"CSV column count mismatch near line {reader.line_num}")
                events.append(event)
        for event in events:
            if isinstance(event.get("corrects"), str):
                event["corrects"] = [item for item in event["corrects"].split(";") if item]
            if isinstance(event.get("schema_version"), str) and event["schema_version"].isdigit():
                event["schema_version"] = int(event["schema_version"])
    else:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        if isinstance(payload, list):
            events = payload
        elif isinstance(payload, dict):
            events = payload.get("events", [payload])
        else:
            raise ValueError("JSON must contain an event object, an event array, or an events array wrapper")
    if not isinstance(events, list) or not events:
        raise ValueError("Input must contain a non-empty event array")
    if any(not isinstance(event, dict) for event in events):
        raise ValueError("Every event must be an object")
    results = []
    for event in events:
        issues = check_event(event, lang)
        results.append({"event_id": event.get("event_id"), "issues": issues})
    return {"tool": "open-care-evidence-toolkit-mvp", "events": len(results), "issues": sum(len(item["issues"]) for item in results), "results": results}


def render(report: dict, fmt: str, lang: str = "en") -> str:
    if fmt == "json":
        return json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if lang == "ja":
        lines = ["# データ品質サマリー\n", f"- イベント数: {report['events']}", f"- 問題数: {report['issues']}", ""]
    else:
        lines = ["# Data quality summary\n", f"- Events: {report['events']}", f"- Issues: {report['issues']}", ""]
    for item in report["results"]:
        missing_id = "(event_idなし)" if lang == "ja" else "(missing event_id)"
        lines.append(f"## {item['event_id'] or missing_id}")
        if not item["issues"]:
            lines.append("✅ 6規則を通過" if lang == "ja" else "✅ Passed all 6 rules")
        else:
            for issue in item["issues"]:
                lines.append(f"- ⚠️ {RULES[issue['rule']][lang]}: {issue['message']}")
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline checks for synthetic care evidence events")
    parser.add_argument("input", type=Path)
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown")
    parser.add_argument("--lang", choices=("en", "ja"), default="en", help="diagnostic language (default: en)")
    parser.add_argument("--fail-on-issues", action="store_true", help="exit with status 1 when quality issues are found")
    args = parser.parse_args()
    try:
        report = inspect(args.input, args.lang)
    except (OSError, ValueError, csv.Error) as error:
        # Keep stdout report-only so callers never consume a partial report.
        label = "入力エラー" if args.lang == "ja" else "Input error"
        print(f"{label}: {error}", file=sys.stderr)
        return 2
    print(render(report, args.format, args.lang), end="")
    return 1 if args.fail_on_issues and report["issues"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
