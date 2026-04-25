from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.db.models import Task, TaskPriority, TaskStatus


def test_bulk_task_update_and_outcome_tags(client, db_session: Session):
    first = Task(title="Call Ada", status=TaskStatus.open, priority=TaskPriority.medium, source="manual")
    second = Task(title="Email Grace", status=TaskStatus.open, priority=TaskPriority.low, source="manual")
    db_session.add_all([first, second])
    db_session.commit()

    response = client.post(
        "/api/v1/tasks/bulk",
        json={
            "task_ids": [first.id, second.id],
            "priority": "high",
            "outcome_tag": "needs_more_followup",
        },
    )
    assert response.status_code == 200
    assert response.json()["updated_count"] == 2

    db_session.refresh(first)
    db_session.refresh(second)
    assert first.priority == TaskPriority.high
    assert second.outcome_tag == "needs_more_followup"


def test_workflow_benchmark_events(client):
    response = client.post(
        "/api/v1/tasks/benchmarks",
        json={
            "workflow": "match_resolution",
            "action": "bulk_confirm_canvas",
            "duration_ms": 42000,
            "context_json": {"course_id": 1, "count": 3},
        },
    )
    assert response.status_code == 200
    assert response.json()["workflow"] == "match_resolution"

    response = client.get("/api/v1/tasks/benchmarks/summary")
    assert response.status_code == 200
    assert response.json()["workflows"][0]["average_duration_ms"] == 42000
