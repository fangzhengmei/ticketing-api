def test_create_ticket(client):
    response = client.post(
        "/tickets",
        json={"title": "Test ticket", "status": "open"},
    )

    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert data["title"] == "Test ticket"
    assert data["status"] == "open"


def test_list_tickets_returns_metadata(client):
    client.post("/tickets", json={"title": "Ticket A", "status": "open"})
    client.post("/tickets", json={"title": "Ticket B", "status": "open"})

    response = client.get("/tickets?limit=1&offset=0")
    assert response.status_code == 200

    data = response.json()
    assert "total" in data
    assert "limit" in data
    assert "offset" in data
    assert "items" in data

    assert data["limit"] == 1
    assert data["offset"] == 0

    assert isinstance(data["items"], list)
    assert len(data["items"]) == 1

def test_list_tickets_limit_constraints(client):
    res = client.get("/tickets?limit=0&offset=0")
    assert res.status_code == 422

    res = client.get("/tickets?limit=101&offset=0")
    assert res.status_code == 422

    res = client.get("/tickets?limit=1&offset=-1")
    assert res.status_code == 422

def test_get_ticket_not_found(client):
    res = client.get("/tickets/999999")
    assert res.status_code == 404
    assert res.json()["detail"] == "Ticket not found"


def test_patch_ticket_not_found(client):
    res = client.patch("/tickets/999999", json={"status": "resolved"})
    assert res.status_code == 404
    assert res.json()["detail"] == "Ticket not found"


def test_delete_ticket_not_found(client):
    res = client.delete("/tickets/999999")
    assert res.status_code == 404
    assert res.json()["detail"] == "Ticket not found"


def test_delete_ticket_success_and_then_404(client):
    # create a ticket
    created = client.post("/tickets", json={"title": "To delete", "status": "open"})
    assert created.status_code == 201
    ticket_id = created.json()["id"]

    # delete it
    deleted = client.delete(f"/tickets/{ticket_id}")
    assert deleted.status_code == 204
    assert deleted.text == ""  # 204 should have no body

    # now it should be gone
    res = client.get(f"/tickets/{ticket_id}")
    assert res.status_code == 404

def test_create_ticket_missing_title_returns_422(client):
    # Missing "title"
    res = client.post("/tickets", json={"status": "open"})
    assert res.status_code == 422


def test_patch_ticket_invalid_status_returns_422(client):
    # Create a ticket first
    created = client.post("/tickets", json={"title": "Ticket", "status": "open"})
    assert created.status_code == 201
    ticket_id = created.json()["id"]

    # Send invalid status (not in your allowed enum)
    res = client.patch(f"/tickets/{ticket_id}", json={"status": "not_a_real_status"})
    assert res.status_code == 422


def test_list_tickets_offset_beyond_total_returns_empty_items(client):
    # Create 2 tickets
    client.post("/tickets", json={"title": "A", "status": "open"})
    client.post("/tickets", json={"title": "B", "status": "open"})

    # Offset bigger than total -> should return empty list, not error
    res = client.get("/tickets?limit=10&offset=999")
    assert res.status_code == 200

    data = res.json()
    assert data["total"] == 2
    assert data["limit"] == 10
    assert data["offset"] == 999
    assert data["items"] == []


def test_list_tickets_limit_above_max_returns_422(client):
    res = client.get("/tickets?limit=101&offset=0")
    assert res.status_code == 422

def test_patch_ticket_forbidden_transition_returns_409(client):
    created = client.post("/tickets", json={"title": "X", "status": "resolved"})
    ticket_id = created.json()["id"]

    res = client.patch(f"/tickets/{ticket_id}", json={"status": "open"})
    assert res.status_code == 409
    assert res.json()["detail"] == "Invalid status transition"


def test_patch_ticket_allowed_transition_ok(client):
    created = client.post("/tickets", json={"title": "X", "status": "open"})
    ticket_id = created.json()["id"]

    res = client.patch(f"/tickets/{ticket_id}", json={"status": "in_progress"})
    assert res.status_code == 200
    assert res.json()["status"] == "in_progress"

import pytest


@pytest.mark.parametrize(
    "start_status,new_status",
    [
        ("open", "in_progress"),
        ("open", "resolved"),
        ("in_progress", "resolved"),
    ],
)
def test_status_transitions_allowed(client, start_status, new_status):
    created = client.post("/tickets", json={"title": "T", "status": start_status})
    assert created.status_code == 201
    ticket_id = created.json()["id"]

    res = client.patch(f"/tickets/{ticket_id}", json={"status": new_status})
    assert res.status_code == 200
    assert res.json()["status"] == new_status


@pytest.mark.parametrize(
    "start_status,new_status",
    [
        ("resolved", "open"),
        ("resolved", "in_progress"),
        ("in_progress", "open"),
    ],
)
def test_status_transitions_forbidden_return_409(client, start_status, new_status):
    created = client.post("/tickets", json={"title": "T", "status": start_status})
    assert created.status_code == 201
    ticket_id = created.json()["id"]

    res = client.patch(f"/tickets/{ticket_id}", json={"status": new_status})
    assert res.status_code == 409
    assert res.json()["detail"] == "Invalid status transition"


from datetime import datetime, timedelta, timezone


def test_create_ticket_with_deadline(client):
    future_deadline = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
    
    response = client.post(
        "/tickets",
        json={
            "title": "Test ticket with deadline",
            "status": "open",
            "deadline": future_deadline
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert data["title"] == "Test ticket with deadline"
    assert data["status"] == "open"
    assert data["deadline"] is not None
    assert "is_overdue" in data


def test_create_ticket_without_deadline(client):
    response = client.post(
        "/tickets",
        json={
            "title": "Test ticket without deadline",
            "status": "open",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["deadline"] is None
    assert data["is_overdue"] is False


def test_is_overdue_not_expired_ticket(client):
    future_deadline = (datetime.utcnow() + timedelta(days=7)).isoformat() + "Z"
    
    response = client.post(
        "/tickets",
        json={
            "title": "Not expired ticket",
            "status": "open",
            "deadline": future_deadline
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["is_overdue"] is False
    
    ticket_id = data["id"]
    get_response = client.get(f"/tickets/{ticket_id}")
    assert get_response.status_code == 200
    assert get_response.json()["is_overdue"] is False


def test_is_overdue_expired_ticket(client):
    past_deadline = (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"
    
    response = client.post(
        "/tickets",
        json={
            "title": "Expired ticket",
            "status": "open",
            "deadline": past_deadline
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["is_overdue"] is True
    
    ticket_id = data["id"]
    get_response = client.get(f"/tickets/{ticket_id}")
    assert get_response.status_code == 200
    assert get_response.json()["is_overdue"] is True


def test_is_overdue_in_progress_expired_ticket(client):
    past_deadline = (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"
    
    response = client.post(
        "/tickets",
        json={
            "title": "In progress expired ticket",
            "status": "in_progress",
            "deadline": past_deadline
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["is_overdue"] is True


def test_is_overdue_resolved_ticket_not_expired(client):
    future_deadline = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
    
    created = client.post(
        "/tickets",
        json={
            "title": "Will be resolved",
            "status": "open",
            "deadline": future_deadline
        },
    )
    assert created.status_code == 201
    ticket_id = created.json()["id"]
    assert created.json()["is_overdue"] is False
    
    resolved = client.patch(f"/tickets/{ticket_id}", json={"status": "resolved"})
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["is_overdue"] is False


def test_is_overdue_resolved_ticket_even_if_deadline_passed(client):
    past_deadline = (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"
    
    created = client.post(
        "/tickets",
        json={
            "title": "Resolved after deadline",
            "status": "open",
            "deadline": past_deadline
        },
    )
    assert created.status_code == 201
    ticket_id = created.json()["id"]
    assert created.json()["is_overdue"] is True
    
    resolved = client.patch(f"/tickets/{ticket_id}", json={"status": "resolved"})
    assert resolved.status_code == 200
    assert resolved.json()["status"] == "resolved"
    assert resolved.json()["is_overdue"] is False


def test_patch_update_deadline(client):
    created = client.post(
        "/tickets",
        json={"title": "Ticket to update deadline", "status": "open"},
    )
    assert created.status_code == 201
    ticket_id = created.json()["id"]
    assert created.json()["deadline"] is None
    
    future_deadline = (datetime.utcnow() + timedelta(days=3)).isoformat() + "Z"
    updated = client.patch(
        f"/tickets/{ticket_id}",
        json={"deadline": future_deadline}
    )
    assert updated.status_code == 200
    assert updated.json()["deadline"] is not None
    assert updated.json()["is_overdue"] is False


def test_filter_tickets_by_is_overdue_true(client):
    past_deadline = (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"
    future_deadline = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
    
    client.post("/tickets", json={
        "title": "Expired ticket 1",
        "status": "open",
        "deadline": past_deadline
    })
    client.post("/tickets", json={
        "title": "Expired ticket 2",
        "status": "in_progress",
        "deadline": past_deadline
    })
    client.post("/tickets", json={
        "title": "Not expired",
        "status": "open",
        "deadline": future_deadline
    })
    client.post("/tickets", json={
        "title": "No deadline",
        "status": "open"
    })
    
    response = client.get("/tickets?is_overdue=true")
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 2
    assert len(data["items"]) == 2
    for item in data["items"]:
        assert item["is_overdue"] is True


def test_filter_tickets_by_is_overdue_false(client):
    past_deadline = (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"
    future_deadline = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
    
    client.post("/tickets", json={
        "title": "Expired ticket",
        "status": "open",
        "deadline": past_deadline
    })
    client.post("/tickets", json={
        "title": "Not expired",
        "status": "open",
        "deadline": future_deadline
    })
    client.post("/tickets", json={
        "title": "No deadline",
        "status": "open"
    })
    client.post("/tickets", json={
        "title": "Resolved but expired",
        "status": "resolved",
        "deadline": past_deadline
    })
    
    response = client.get("/tickets?is_overdue=false")
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 3
    for item in data["items"]:
        assert item["is_overdue"] is False


def test_filter_without_is_overdue_returns_all(client):
    past_deadline = (datetime.utcnow() - timedelta(hours=1)).isoformat() + "Z"
    future_deadline = (datetime.utcnow() + timedelta(days=1)).isoformat() + "Z"
    
    client.post("/tickets", json={
        "title": "Expired",
        "status": "open",
        "deadline": past_deadline
    })
    client.post("/tickets", json={
        "title": "Not expired",
        "status": "open",
        "deadline": future_deadline
    })
    client.post("/tickets", json={
        "title": "No deadline",
        "status": "open"
    })
    
    response = client.get("/tickets")
    assert response.status_code == 200
    data = response.json()
    
    assert data["total"] == 3
