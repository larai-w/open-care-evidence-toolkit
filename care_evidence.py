#!/usr/bin/env python3
"""Deterministic, offline checks for a small observation-event schema."""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from datetime import datetime
from pathlib import Path

REQUIRED = ("event_id", "observed_at", "timezone", "source", "recorder_role", "observation", "interpretation", "status", "corrects", "schema_version")
STATUSES = {"observed", "not_recorded", "not_occurring"}
RULES = {item["id"]: item for item in json.loads((Path(__file__).parent / "rules.json").read_text(encoding="utf-8"))}


# Explicit shared grammar; do not delegate format acceptance to platform parsers.
TIMESTAMP = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}(?:\.[0-9]{1,6})?(?:Z|[+-][0-9]{2}:[0-9]{2})")
BLANK = re.compile(r"[\u0009-\u000d\u0020\u0085\u00a0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000\ufeff]")


def nonblank(value: object) -> bool:
    return isinstance(value, str) and bool(BLANK.sub("", value))


def valid_timestamp(value: object) -> bool:
    if not isinstance(value, str) or not TIMESTAMP.fullmatch(value):
        return False
    if value[-1] != "Z" and (int(value[-5:-3]) > 23 or int(value[-2:]) > 59):
        return False
    try:
        datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return False
    return True


def check_event(event: dict, lang: str = "en") -> list[dict]:
    def message(en: str, ja: str) -> str:
        return ja if lang == "ja" else en

    issues: list[dict] = []
    def add(rule: str, en: str, ja: str) -> None:
        issues.append({"rule": rule, "message": message(en, ja)})

    missing = [key for key in REQUIRED if key not in event]
    if missing:
        add("required_fields", f"Missing fields: {', '.join(missing)}", f"不足: {', '.join(missing)}")
    invalid_schema = []
    if "event_id" in event and not nonblank(event["event_id"]):
        invalid_schema.append("event_id")
    if "schema_version" in event and not (type(event["schema_version"]) in (int, float) and event["schema_version"] == 1):
        invalid_schema.append("schema_version")
    if invalid_schema:
        add("required_fields", "Require a nonblank string event_id and numeric schema_version 1", "event_idは空でない文字列、schema_versionは数値1が必要です")

    if not valid_timestamp(event.get("observed_at")):
        add("timestamp_timezone", "Use YYYY-MM-DDTHH:MM:SS[.ffffff] with Z or +/-HH:MM and a valid calendar date", "observed_atは実在する日時と対応するオフセット形式が必要です")
    if not nonblank(event.get("timezone")):
        add("timestamp_timezone", "timezone must be a nonblank string", "timezoneは空でない文字列が必要です")

    observation, interpretation = event.get("observation", ""), event.get("interpretation", "")
    if not isinstance(observation, str) or not isinstance(interpretation, str):
        add("observation_interpretation", "observation and interpretation must be strings", "observationとinterpretationは文字列が必要です")
    else:
        if any(token in observation.lower() for token in ("と思う", "かもしれない", "likely", "maybe")):
            add("observation_interpretation", "Move speculative wording from observation to interpretation", "観察欄に推測表現があります。解釈欄へ分けてください")
        if event.get("status") == "observed" and not nonblank(observation):
            add("observation_interpretation", "observed requires observation text", "observedには観察内容が必要です")
            if nonblank(interpretation):
                add("observation_interpretation", "An interpretation needs an observation when status is observed", "解釈だけで、観察の根拠がありません")

    if not nonblank(event.get("source")) or not nonblank(event.get("recorder_role")):
        add("provenance", "Record source and recorder_role as nonblank strings", "sourceとrecorder_roleを空でない文字列で記録してください")
    status = event.get("status")
    if not isinstance(status, str) or status not in STATUSES:
        add("missingness_status", f"status must be one of {sorted(STATUSES)}", f"statusは{sorted(STATUSES)}のいずれかです")
    if status == "not_recorded" and (nonblank(observation) or nonblank(interpretation)):
        add("missingness_status", "not_recorded must not contain observation or interpretation text", "not_recordedに観察・解釈を入れないでください")
    if "corrects" in event:
        corrects = event["corrects"]
        if not (nonblank(corrects) or isinstance(corrects, list) and all(nonblank(item) for item in corrects)):
            add("correction_reference", "Use a nonblank correction ID or a list of nonblank IDs; use [] for no correction", "correctsは空でないIDまたはID配列、訂正なしは[]を使用してください")
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
            if isinstance(event.get("schema_version"), str) and re.fullmatch(r"0*1", event["schema_version"]) is not None:
                event["schema_version"] = 1
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
