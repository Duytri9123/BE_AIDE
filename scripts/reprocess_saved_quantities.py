"""Reapply current evidence-based quantity rules to saved analysis results."""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.schemas.ai import ExtractedDeviceSchema
from app.services.ai.analysis_pipeline_service import AnalysisPipelineService


def reprocess_list(raw_value):
    payload = json.loads(raw_value) if isinstance(raw_value, str) else raw_value
    if not isinstance(payload, list):
        return raw_value, 0
    devices = [ExtractedDeviceSchema.model_validate(item) for item in payload if isinstance(item, dict)]
    AnalysisPipelineService._infer_practical_quantities(devices)
    return json.dumps([device.model_dump() for device in devices], ensure_ascii=False), len(devices)


def main() -> None:
    database = Path(__file__).resolve().parents[1] / "webbaogia.db"
    connection = sqlite3.connect(database)
    rows = connection.execute(
        "SELECT id, ai_parsed_devices, devices_after_validation FROM analysis_iterations"
    ).fetchall()
    updated = 0
    with connection:
        for iteration_id, parsed, validated in rows:
            parsed_value, parsed_count = reprocess_list(parsed)
            validated_value, validated_count = reprocess_list(validated)
            connection.execute(
                "UPDATE analysis_iterations SET ai_parsed_devices=?, devices_after_validation=? WHERE id=?",
                (parsed_value, validated_value, iteration_id),
            )
            updated += max(parsed_count, validated_count)
    connection.close()
    print(json.dumps({"iterations": len(rows), "devices_reprocessed": updated}))


if __name__ == "__main__":
    main()
