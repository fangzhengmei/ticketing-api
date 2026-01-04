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
