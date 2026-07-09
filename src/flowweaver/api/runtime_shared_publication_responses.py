from __future__ import annotations

from typing import Any

from flowweaver.engine.runtime_models import SharedPublication


def shared_publication_to_jsonable(value: SharedPublication) -> dict[str, Any]:
    return {
        "publication_id": value.publication_id,
        "share_name": value.share_name,
        "publication_version": value.publication_version,
        "producer_workflow_id": value.producer_workflow_id,
        "producer_run_id": value.producer_run_id,
        "status": value.status,
        "input_snapshot_id": value.input_snapshot_id,
        "retention_policy": value.retention_policy,
        "created_at": value.created_at.isoformat(),
        "members": [
            {
                "publication_id": member.publication_id,
                "export_name": member.export_name,
                "table_ref_id": member.table_ref_id,
                "exact_table_version": member.exact_table_version,
            }
            for member in value.members
        ],
    }
