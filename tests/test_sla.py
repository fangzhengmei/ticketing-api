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
    assert "created_by" in data


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


def test_create_ticket_records_created_by(client):
    user_id = "user-123"
    response = client.post(
        "/tickets",
        json={"title": "Test Ticket", "status": "open"},
        headers={"X-User-Id": user_id},
    )

    assert response.status_code == 201
    data = response.json()
    assert data["created_by"] == user_id


def test_creator_can_modify_sla(client):
    user_id = "user-456"
    create_response = client.post(
        "/tickets",
        json={"title": "Creator Test", "status": "open"},
        headers={"X-User-Id": user_id},
    )
    ticket_id = create_response.json()["id"]

    new_deadline = (datetime.utcnow() + timedelta(days=5)).isoformat()
    patch_response = client.patch(
        f"/tickets/{ticket_id}",
        json={"status": "open", "sla_deadline": new_deadline},
        headers={"X-User-Id": user_id},
    )

    assert patch_response.status_code == 200
    data = patch_response.json()
    assert data["sla_deadline"] is not None


def test_other_user_cannot_modify_sla(client):
    creator_id = "user-creator"
    other_user_id = "user-other"
    
    create_response = client.post(
        "/tickets",
        json={"title": "Permission Test", "status": "open"},
        headers={"X-User-Id": creator_id},
    )
    ticket_id = create_response.json()["id"]

    new_deadline = (datetime.utcnow() + timedelta(days=5)).isoformat()
    patch_response = client.patch(
        f"/tickets/{ticket_id}",
        json={"status": "open", "sla_deadline": new_deadline},
        headers={"X-User-Id": other_user_id},
    )

    assert patch_response.status_code == 403
    data = patch_response.json()
    assert "detail" in data
    assert "Not authorized" in data["detail"]


def test_admin_can_modify_any_sla(client):
    creator_id = "user-creator"
    admin_user_id = "user-admin"
    
    create_response = client.post(
        "/tickets",
        json={"title": "Admin Test", "status": "open"},
        headers={"X-User-Id": creator_id},
    )
    ticket_id = create_response.json()["id"]

    new_deadline = (datetime.utcnow() + timedelta(days=10)).isoformat()
    patch_response = client.patch(
        f"/tickets/{ticket_id}",
        json={"status": "open", "sla_deadline": new_deadline},
        headers={"X-User-Id": admin_user_id, "X-Is-Admin": "true"},
    )

    assert patch_response.status_code == 200
    data = patch_response.json()
    assert data["sla_deadline"] is not None


def test_ticket_without_created_by_allows_any_modification(client):
    create_response = client.post(
        "/tickets",
        json={"title": "No Creator Test", "status": "open"},
    )
    ticket_id = create_response.json()["id"]
    assert create_response.json()["created_by"] is None

    new_deadline = (datetime.utcnow() + timedelta(days=7)).isoformat()
    patch_response = client.patch(
        f"/tickets/{ticket_id}",
        json={"status": "open", "sla_deadline": new_deadline},
        headers={"X-User-Id": "random-user"},
    )

    assert patch_response.status_code == 200


def test_update_only_status_without_sla_change_does_not_check_permission(client):
    creator_id = "user-creator"
    other_user_id = "user-other"
    
    create_response = client.post(
        "/tickets",
        json={"title": "Status Only Test", "status": "open", "sla_deadline": (datetime.utcnow() + timedelta(days=2)).isoformat()},
        headers={"X-User-Id": creator_id},
    )
    ticket_id = create_response.json()["id"]

    patch_response = client.patch(
        f"/tickets/{ticket_id}",
        json={"status": "in_progress"},
        headers={"X-User-Id": other_user_id},
    )

    assert patch_response.status_code == 200
    data = patch_response.json()
    assert data["status"] == "in_progress"
