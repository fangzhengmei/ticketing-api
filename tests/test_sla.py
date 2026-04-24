from datetime import datetime, timedelta
import pytest
import os


def test_create_ticket_with_sla_deadline(client):
    deadline = (datetime.utcnow() + timedelta(days=2)).isoformat()
    response = client.post(
        "/tickets",
        json={"title": "SLA Test Ticket", "status": "open", "sla_deadline": deadline},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "SLA Test Ticket"
    assert data["sla_deadline"] is not None
    assert data["sla_breached"] == False
    assert data["sla_status"] == "on_track"


def test_create_ticket_without_sla_deadline(client):
    response = client.post(
        "/tickets",
        json={"title": "No SLA Ticket", "status": "open"},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["sla_deadline"] is None
    assert data["sla_status"] == "not_set"


def test_get_ticket_includes_sla_fields(client):
    response = client.post(
        "/tickets",
        json={"title": "Test Ticket", "status": "open"},
    )
    ticket_id = response.json()["id"]

    get_response = client.get(f"/tickets/{ticket_id}")
    assert get_response.status_code == 200
    data = get_response.json()
    
    assert "created_at" in data
    assert "sla_deadline" in data
    assert "sla_breached" in data
    assert "sla_status" in data
    assert "resolved_at" in data


def test_update_ticket_sla_deadline(client):
    response = client.post(
        "/tickets",
        json={"title": "Update SLA Test", "status": "open"},
    )
    ticket_id = response.json()["id"]
    assert response.json()["sla_deadline"] is None

    new_deadline = (datetime.utcnow() + timedelta(days=3)).isoformat()
    patch_response = client.patch(
        f"/tickets/{ticket_id}",
        json={"status": "open", "sla_deadline": new_deadline},
    )

    assert patch_response.status_code == 200
    data = patch_response.json()
    assert data["sla_deadline"] is not None
    assert data["sla_status"] == "on_track"


def test_list_tickets_filter_by_sla_status(client):
    future_deadline = (datetime.utcnow() + timedelta(days=2)).isoformat()
    client.post("/tickets", json={"title": "On Track", "status": "open", "sla_deadline": future_deadline})
    client.post("/tickets", json={"title": "No SLA", "status": "open"})

    response = client.get("/tickets?sla_status=on_track")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] >= 1

    response_not_set = client.get("/tickets?sla_status=not_set")
    assert response_not_set.status_code == 200
    data_not_set = response_not_set.json()
    assert data_not_set["total"] >= 1


def test_get_sla_statistics(client):
    future_deadline = (datetime.utcnow() + timedelta(days=2)).isoformat()
    client.post("/tickets", json={"title": "With SLA", "status": "open", "sla_deadline": future_deadline})
    client.post("/tickets", json={"title": "Without SLA", "status": "open"})

    response = client.get("/sla/statistics")
    assert response.status_code == 200
    data = response.json()
    
    assert "total" in data
    assert "on_track" in data
    assert "warning" in data
    assert "breached" in data
    assert "not_set" in data
    assert "warning_threshold_hours" in data
    assert data["total"] >= 2


def test_resolve_ticket_records_resolved_at(client):
    deadline = (datetime.utcnow() + timedelta(days=2)).isoformat()
    create_response = client.post(
        "/tickets",
        json={"title": "To Resolve", "status": "open", "sla_deadline": deadline},
    )
    ticket_id = create_response.json()["id"]
    assert create_response.json()["resolved_at"] is None

    patch_response = client.patch(
        f"/tickets/{ticket_id}",
        json={"status": "resolved"},
    )

    assert patch_response.status_code == 200
    data = patch_response.json()
    assert data["resolved_at"] is not None
    assert data["sla_status"] == "on_track"


def test_create_ticket_with_past_deadline_returns_422(client):
    past_deadline = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    response = client.post(
        "/tickets",
        json={"title": "Past Deadline Ticket", "status": "open", "sla_deadline": past_deadline},
    )

    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    assert any("sla_deadline" in str(err) or "past" in str(err).lower() for err in data["detail"])


def test_update_ticket_with_past_deadline_returns_422(client):
    create_response = client.post(
        "/tickets",
        json={"title": "Test Ticket", "status": "open"},
    )
    ticket_id = create_response.json()["id"]

    past_deadline = (datetime.utcnow() - timedelta(hours=1)).isoformat()
    patch_response = client.patch(
        f"/tickets/{ticket_id}",
        json={"status": "open", "sla_deadline": past_deadline},
    )

    assert patch_response.status_code == 422


def test_warning_status_near_deadline(client):
    original_threshold = os.environ.get("SLA_WARNING_THRESHOLD_HOURS")
    try:
        os.environ["SLA_WARNING_THRESHOLD_HOURS"] = "48"
        
        soon_deadline = (datetime.utcnow() + timedelta(hours=12)).isoformat()
        response = client.post(
            "/tickets",
            json={"title": "Warning Test", "status": "open", "sla_deadline": soon_deadline},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["sla_status"] == "warning"
        
        stats_response = client.get("/sla/statistics")
        assert stats_response.status_code == 200
        assert stats_response.json()["warning_threshold_hours"] == 48
    finally:
        if original_threshold:
            os.environ["SLA_WARNING_THRESHOLD_HOURS"] = original_threshold
        else:
            os.environ.pop("SLA_WARNING_THRESHOLD_HOURS", None)
        
        from app.config import Settings
        Settings._instance = None


def test_on_track_status_far_from_deadline(client):
    original_threshold = os.environ.get("SLA_WARNING_THRESHOLD_HOURS")
    try:
        os.environ["SLA_WARNING_THRESHOLD_HOURS"] = "24"
        
        far_deadline = (datetime.utcnow() + timedelta(hours=48)).isoformat()
        response = client.post(
            "/tickets",
            json={"title": "On Track Test", "status": "open", "sla_deadline": far_deadline},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["sla_status"] == "on_track"
    finally:
        if original_threshold:
            os.environ["SLA_WARNING_THRESHOLD_HOURS"] = original_threshold
        else:
            os.environ.pop("SLA_WARNING_THRESHOLD_HOURS", None)
        
        from app.config import Settings
        Settings._instance = None
