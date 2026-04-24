import os
import io
import pytest
from fastapi.testclient import TestClient


def create_test_image():
    return io.BytesIO(b"fake image content")


def create_test_text():
    return io.BytesIO(b"test log content here")


def test_upload_attachment_success(client: TestClient):
    ticket_response = client.post("/tickets", json={"title": "Test ticket", "status": "open"})
    assert ticket_response.status_code == 201
    ticket_id = ticket_response.json()["id"]

    files = {
        "file": ("screenshot.png", create_test_image(), "image/png")
    }
    data = {"description": "Bug screenshot"}

    response = client.post(
        f"/tickets/{ticket_id}/attachments",
        files=files,
        data=data
    )

    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["original_name"] == "screenshot.png"
    assert data["content_type"] == "image/png"
    assert data["description"] == "Bug screenshot"
    assert data["file_size"] > 0
    assert "created_at" in data


def test_upload_attachment_ticket_not_found(client: TestClient):
    files = {
        "file": ("test.png", create_test_image(), "image/png")
    }

    response = client.post("/tickets/999999/attachments", files=files)
    assert response.status_code == 404
    assert response.json()["detail"] == "Ticket not found"


def test_upload_attachment_unsupported_file_type(client: TestClient):
    ticket_response = client.post("/tickets", json={"title": "Test ticket", "status": "open"})
    ticket_id = ticket_response.json()["id"]

    files = {
        "file": ("test.exe", b"binary content", "application/x-msdownload")
    }

    response = client.post(f"/tickets/{ticket_id}/attachments", files=files)
    assert response.status_code == 400
    assert "Unsupported file type" in response.json()["detail"]


def test_list_attachments_empty(client: TestClient):
    ticket_response = client.post("/tickets", json={"title": "Test ticket", "status": "open"})
    ticket_id = ticket_response.json()["id"]

    response = client.get(f"/tickets/{ticket_id}/attachments")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


def test_list_attachments(client: TestClient):
    ticket_response = client.post("/tickets", json={"title": "Test ticket", "status": "open"})
    ticket_id = ticket_response.json()["id"]

    files1 = {"file": ("screenshot.png", create_test_image(), "image/png")}
    files2 = {"file": ("log.txt", create_test_text(), "text/plain")}

    client.post(f"/tickets/{ticket_id}/attachments", files=files1)
    client.post(f"/tickets/{ticket_id}/attachments", files=files2)

    response = client.get(f"/tickets/{ticket_id}/attachments")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 2
    assert len(data["items"]) == 2


def test_list_attachments_ticket_not_found(client: TestClient):
    response = client.get("/tickets/999999/attachments")
    assert response.status_code == 404


def test_get_attachment(client: TestClient):
    ticket_response = client.post("/tickets", json={"title": "Test ticket", "status": "open"})
    ticket_id = ticket_response.json()["id"]

    files = {"file": ("screenshot.png", create_test_image(), "image/png")}
    upload_response = client.post(f"/tickets/{ticket_id}/attachments", files=files)
    attachment_id = upload_response.json()["id"]

    response = client.get(f"/tickets/{ticket_id}/attachments/{attachment_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == attachment_id
    assert data["original_name"] == "screenshot.png"


def test_get_attachment_not_found(client: TestClient):
    ticket_response = client.post("/tickets", json={"title": "Test ticket", "status": "open"})
    ticket_id = ticket_response.json()["id"]

    response = client.get(f"/tickets/{ticket_id}/attachments/999999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Attachment not found"


def test_get_attachment_wrong_ticket(client: TestClient):
    ticket1_response = client.post("/tickets", json={"title": "Ticket 1", "status": "open"})
    ticket1_id = ticket1_response.json()["id"]

    ticket2_response = client.post("/tickets", json={"title": "Ticket 2", "status": "open"})
    ticket2_id = ticket2_response.json()["id"]

    files = {"file": ("screenshot.png", create_test_image(), "image/png")}
    upload_response = client.post(f"/tickets/{ticket1_id}/attachments", files=files)
    attachment_id = upload_response.json()["id"]

    response = client.get(f"/tickets/{ticket2_id}/attachments/{attachment_id}")
    assert response.status_code == 404


def test_delete_attachment(client: TestClient):
    ticket_response = client.post("/tickets", json={"title": "Test ticket", "status": "open"})
    ticket_id = ticket_response.json()["id"]

    files = {"file": ("screenshot.png", create_test_image(), "image/png")}
    upload_response = client.post(f"/tickets/{ticket_id}/attachments", files=files)
    attachment_id = upload_response.json()["id"]

    delete_response = client.delete(f"/tickets/{ticket_id}/attachments/{attachment_id}")
    assert delete_response.status_code == 204

    get_response = client.get(f"/tickets/{ticket_id}/attachments/{attachment_id}")
    assert get_response.status_code == 404


def test_delete_attachment_not_found(client: TestClient):
    ticket_response = client.post("/tickets", json={"title": "Test ticket", "status": "open"})
    ticket_id = ticket_response.json()["id"]

    response = client.delete(f"/tickets/{ticket_id}/attachments/999999")
    assert response.status_code == 404


def test_update_attachment_description(client: TestClient):
    ticket_response = client.post("/tickets", json={"title": "Test ticket", "status": "open"})
    ticket_id = ticket_response.json()["id"]

    files = {"file": ("screenshot.png", create_test_image(), "image/png")}
    upload_response = client.post(f"/tickets/{ticket_id}/attachments", files=files)
    attachment_id = upload_response.json()["id"]

    update_response = client.patch(
        f"/tickets/{ticket_id}/attachments/{attachment_id}",
        json={"description": "Updated description for the bug screenshot"}
    )
    assert update_response.status_code == 200
    assert update_response.json()["description"] == "Updated description for the bug screenshot"

    get_response = client.get(f"/tickets/{ticket_id}/attachments/{attachment_id}")
    assert get_response.json()["description"] == "Updated description for the bug screenshot"


def test_update_attachment_description_to_null(client: TestClient):
    ticket_response = client.post("/tickets", json={"title": "Test ticket", "status": "open"})
    ticket_id = ticket_response.json()["id"]

    files = {"file": ("screenshot.png", create_test_image(), "image/png")}
    data = {"description": "Initial description"}
    upload_response = client.post(f"/tickets/{ticket_id}/attachments", files=files, data=data)
    attachment_id = upload_response.json()["id"]
    assert upload_response.json()["description"] == "Initial description"

    update_response = client.patch(
        f"/tickets/{ticket_id}/attachments/{attachment_id}",
        json={"description": None}
    )
    assert update_response.status_code == 200
    assert update_response.json()["description"] is None


def test_get_ticket_with_attachments(client: TestClient):
    ticket_response = client.post("/tickets", json={"title": "Test ticket", "status": "open"})
    ticket_id = ticket_response.json()["id"]

    files = {"file": ("screenshot.png", create_test_image(), "image/png")}
    client.post(f"/tickets/{ticket_id}/attachments", files=files)

    response = client.get(f"/tickets/{ticket_id}?include_attachments=true")
    assert response.status_code == 200
    data = response.json()
    assert "attachments" in data
    assert len(data["attachments"]) == 1
    assert data["attachments"][0]["original_name"] == "screenshot.png"


def test_get_ticket_without_attachments(client: TestClient):
    ticket_response = client.post("/tickets", json={"title": "Test ticket", "status": "open"})
    ticket_id = ticket_response.json()["id"]

    files = {"file": ("screenshot.png", create_test_image(), "image/png")}
    client.post(f"/tickets/{ticket_id}/attachments", files=files)

    response = client.get(f"/tickets/{ticket_id}")
    assert response.status_code == 200
    data = response.json()
    assert "attachments" not in data


def test_delete_ticket_cascades_attachments(client: TestClient):
    from app.services.attachments import UPLOAD_DIR

    ticket_response = client.post("/tickets", json={"title": "Test ticket", "status": "open"})
    ticket_id = ticket_response.json()["id"]

    files = {"file": ("screenshot.png", create_test_image(), "image/png")}
    upload_response = client.post(f"/tickets/{ticket_id}/attachments", files=files)
    attachment_data = upload_response.json()

    stored_filename = attachment_data["original_name"]

    delete_response = client.delete(f"/tickets/{ticket_id}")
    assert delete_response.status_code == 204

    list_response = client.get(f"/tickets/{ticket_id}/attachments")
    assert list_response.status_code == 404


def test_upload_attachment_without_description(client: TestClient):
    ticket_response = client.post("/tickets", json={"title": "Test ticket", "status": "open"})
    ticket_id = ticket_response.json()["id"]

    files = {"file": ("log.txt", create_test_text(), "text/plain")}

    response = client.post(f"/tickets/{ticket_id}/attachments", files=files)

    assert response.status_code == 201
    data = response.json()
    assert data["description"] is None