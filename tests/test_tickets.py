import pytest
from tests.conftest import user_headers


def test_create_ticket(client):
    response = client.post(
        "/tickets",
        json={"title": "Test ticket", "status": "open"},
        headers=user_headers(),
    )

    assert response.status_code == 201

    data = response.json()
    assert "id" in data
    assert data["title"] == "Test ticket"
    assert data["status"] == "open"


def test_list_tickets_returns_metadata(client):
    client.post("/tickets", json={"title": "Ticket A", "status": "open"}, headers=user_headers())
    client.post("/tickets", json={"title": "Ticket B", "status": "open"}, headers=user_headers())

    response = client.get("/tickets?limit=1&offset=0", headers=user_headers())
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
    res = client.get("/tickets?limit=0&offset=0", headers=user_headers())
    assert res.status_code == 422

    res = client.get("/tickets?limit=101&offset=0", headers=user_headers())
    assert res.status_code == 422

    res = client.get("/tickets?limit=1&offset=-1", headers=user_headers())
    assert res.status_code == 422


def test_get_ticket_not_found(client):
    res = client.get("/tickets/999999", headers=user_headers())
    assert res.status_code == 404
    assert res.json()["detail"] == "Ticket not found"


def test_patch_ticket_not_found(client):
    res = client.patch(
        "/tickets/999999", 
        json={"status": "resolved"},
        headers=user_headers()
    )
    assert res.status_code == 404
    assert res.json()["detail"] == "Ticket not found"


def test_delete_ticket_not_found(client):
    res = client.delete("/tickets/999999", headers=user_headers())
    assert res.status_code == 404
    assert res.json()["detail"] == "Ticket not found"


def test_delete_ticket_success_and_then_404(client):
    created = client.post(
        "/tickets", 
        json={"title": "To delete", "status": "open"},
        headers=user_headers()
    )
    assert created.status_code == 201
    ticket_id = created.json()["id"]

    deleted = client.delete(f"/tickets/{ticket_id}", headers=user_headers())
    assert deleted.status_code == 204
    assert deleted.text == ""

    res = client.get(f"/tickets/{ticket_id}", headers=user_headers())
    assert res.status_code == 404


def test_create_ticket_missing_title_returns_422(client):
    res = client.post(
        "/tickets", 
        json={"status": "open"},
        headers=user_headers()
    )
    assert res.status_code == 422


def test_patch_ticket_invalid_status_returns_422(client):
    created = client.post(
        "/tickets", 
        json={"title": "Ticket", "status": "open"},
        headers=user_headers()
    )
    assert created.status_code == 201
    ticket_id = created.json()["id"]

    res = client.patch(
        f"/tickets/{ticket_id}", 
        json={"status": "not_a_real_status"},
        headers=user_headers()
    )
    assert res.status_code == 422


def test_list_tickets_offset_beyond_total_returns_empty_items(client):
    client.post(
        "/tickets", 
        json={"title": "A", "status": "open"},
        headers=user_headers()
    )
    client.post(
        "/tickets", 
        json={"title": "B", "status": "open"},
        headers=user_headers()
    )

    res = client.get("/tickets?limit=10&offset=999", headers=user_headers())
    assert res.status_code == 200

    data = res.json()
    assert data["total"] == 2
    assert data["limit"] == 10
    assert data["offset"] == 999
    assert data["items"] == []


def test_list_tickets_limit_above_max_returns_422(client):
    res = client.get("/tickets?limit=101&offset=0", headers=user_headers())
    assert res.status_code == 422


def test_patch_ticket_forbidden_transition_returns_409(client):
    created = client.post(
        "/tickets", 
        json={"title": "X", "status": "resolved"},
        headers=user_headers()
    )
    ticket_id = created.json()["id"]

    res = client.patch(
        f"/tickets/{ticket_id}", 
        json={"status": "open"},
        headers=user_headers()
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "Invalid status transition"


def test_patch_ticket_allowed_transition_ok(client):
    created = client.post(
        "/tickets", 
        json={"title": "X", "status": "open"},
        headers=user_headers()
    )
    ticket_id = created.json()["id"]

    res = client.patch(
        f"/tickets/{ticket_id}", 
        json={"status": "in_progress"},
        headers=user_headers()
    )
    assert res.status_code == 200
    assert res.json()["status"] == "in_progress"


@pytest.mark.parametrize(
    "start_status,new_status",
    [
        ("open", "in_progress"),
        ("open", "resolved"),
        ("in_progress", "resolved"),
    ],
)
def test_status_transitions_allowed(client, start_status, new_status):
    created = client.post(
        "/tickets", 
        json={"title": "T", "status": start_status},
        headers=user_headers()
    )
    assert created.status_code == 201
    ticket_id = created.json()["id"]

    res = client.patch(
        f"/tickets/{ticket_id}", 
        json={"status": new_status},
        headers=user_headers()
    )
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
    created = client.post(
        "/tickets", 
        json={"title": "T", "status": start_status},
        headers=user_headers()
    )
    assert created.status_code == 201
    ticket_id = created.json()["id"]

    res = client.patch(
        f"/tickets/{ticket_id}", 
        json={"status": new_status},
        headers=user_headers()
    )
    assert res.status_code == 409
    assert res.json()["detail"] == "Invalid status transition"
