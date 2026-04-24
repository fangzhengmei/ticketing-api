import pytest


class TestTagCRUD:
    def test_create_tag_success(self, client):
        response = client.post(
            "/tags",
            json={"name": "Bug", "color": "#ef4444", "description": "Bug related issues"},
        )
        assert response.status_code == 201
        
        data = response.json()
        assert "id" in data
        assert data["name"] == "Bug"
        assert data["color"] == "#ef4444"
        assert data["description"] == "Bug related issues"
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_tag_default_color(self, client):
        response = client.post(
            "/tags",
            json={"name": "Feature"},
        )
        assert response.status_code == 201
        assert response.json()["color"] == "#3b82f6"

    def test_create_tag_duplicate_name_returns_409(self, client):
        client.post("/tags", json={"name": "Bug", "color": "#ef4444"})
        
        response = client.post(
            "/tags",
            json={"name": "Bug", "color": "#ff0000"},
        )
        assert response.status_code == 409
        assert "already exists" in response.json()["detail"]

    def test_create_tag_invalid_color_returns_422(self, client):
        response = client.post(
            "/tags",
            json={"name": "Test", "color": "invalid"},
        )
        assert response.status_code == 422

    def test_create_tag_empty_name_returns_422(self, client):
        response = client.post(
            "/tags",
            json={"name": ""},
        )
        assert response.status_code == 422

    def test_list_tags_returns_metadata(self, client):
        client.post("/tags", json={"name": "Bug"})
        client.post("/tags", json={"name": "Feature"})
        
        response = client.get("/tags?limit=1&offset=0")
        assert response.status_code == 200
        
        data = response.json()
        assert "total" in data
        assert "limit" in data
        assert "offset" in data
        assert "items" in data
        assert data["total"] == 2
        assert len(data["items"]) == 1

    def test_list_tags_search(self, client):
        client.post("/tags", json={"name": "Bug"})
        client.post("/tags", json={"name": "Feature"})
        client.post("/tags", json={"name": "Bugfix"})
        
        response = client.get("/tags?search=bug")
        assert response.status_code == 200
        assert response.json()["total"] == 2

    def test_list_tags_sorted_by_name(self, client):
        client.post("/tags", json={"name": "Zebra"})
        client.post("/tags", json={"name": "Apple"})
        client.post("/tags", json={"name": "Monkey"})
        
        response = client.get("/tags")
        assert response.status_code == 200
        
        names = [item["name"] for item in response.json()["items"]]
        assert names == ["Apple", "Monkey", "Zebra"]

    def test_get_tag_success(self, client):
        created = client.post("/tags", json={"name": "Bug", "color": "#ef4444"})
        tag_id = created.json()["id"]
        
        response = client.get(f"/tags/{tag_id}")
        assert response.status_code == 200
        assert response.json()["name"] == "Bug"

    def test_get_tag_not_found_returns_404(self, client):
        response = client.get("/tags/99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Tag not found"

    def test_update_tag_name(self, client):
        created = client.post("/tags", json={"name": "OldName"})
        tag_id = created.json()["id"]
        
        response = client.patch(f"/tags/{tag_id}", json={"name": "NewName"})
        assert response.status_code == 200
        assert response.json()["name"] == "NewName"

    def test_update_tag_color(self, client):
        created = client.post("/tags", json={"name": "Test", "color": "#000000"})
        tag_id = created.json()["id"]
        
        response = client.patch(f"/tags/{tag_id}", json={"color": "#ffffff"})
        assert response.status_code == 200
        assert response.json()["color"] == "#ffffff"

    def test_update_tag_duplicate_name_returns_409(self, client):
        client.post("/tags", json={"name": "Existing"})
        created = client.post("/tags", json={"name": "ToUpdate"})
        tag_id = created.json()["id"]
        
        response = client.patch(f"/tags/{tag_id}", json={"name": "Existing"})
        assert response.status_code == 409

    def test_update_tag_not_found_returns_404(self, client):
        response = client.patch("/tags/99999", json={"name": "Test"})
        assert response.status_code == 404

    def test_delete_tag_success(self, client):
        created = client.post("/tags", json={"name": "ToDelete"})
        tag_id = created.json()["id"]
        
        response = client.delete(f"/tags/{tag_id}")
        assert response.status_code == 204
        
        response = client.get(f"/tags/{tag_id}")
        assert response.status_code == 404

    def test_delete_tag_not_found_returns_404(self, client):
        response = client.delete("/tags/99999")
        assert response.status_code == 404


class TestTicketTagAssociation:
    def test_create_ticket_with_tags(self, client):
        tag1 = client.post("/tags", json={"name": "Bug"}).json()
        tag2 = client.post("/tags", json={"name": "Urgent"}).json()
        
        response = client.post(
            "/tickets",
            json={
                "title": "Test ticket",
                "status": "open",
                "tag_ids": [tag1["id"], tag2["id"]]
            },
        )
        assert response.status_code == 201
        
        data = response.json()
        assert len(data["tags"]) == 2
        tag_names = {t["name"] for t in data["tags"]}
        assert tag_names == {"Bug", "Urgent"}

    def test_create_ticket_with_invalid_tag_returns_404(self, client):
        response = client.post(
            "/tickets",
            json={
                "title": "Test ticket",
                "status": "open",
                "tag_ids": [99999]
            },
        )
        assert response.status_code == 404
        assert "Tags not found" in response.json()["detail"]

    def test_add_tags_to_existing_ticket(self, client):
        ticket = client.post("/tickets", json={"title": "Test", "status": "open"}).json()
        tag = client.post("/tags", json={"name": "Bug"}).json()
        
        response = client.post(
            f"/tickets/{ticket['id']}/tags",
            json={"tag_ids": [tag["id"]]},
        )
        assert response.status_code == 200
        assert len(response.json()["tags"]) == 1
        assert response.json()["tags"][0]["name"] == "Bug"

    def test_add_tags_idempotent(self, client):
        ticket = client.post("/tickets", json={"title": "Test", "status": "open"}).json()
        tag = client.post("/tags", json={"name": "Bug"}).json()
        
        client.post(f"/tickets/{ticket['id']}/tags", json={"tag_ids": [tag["id"]]})
        response = client.post(f"/tickets/{ticket['id']}/tags", json={"tag_ids": [tag["id"]]})
        
        assert response.status_code == 200
        assert len(response.json()["tags"]) == 1

    def test_add_tags_empty_returns_422(self, client):
        ticket = client.post("/tickets", json={"title": "Test", "status": "open"}).json()
        
        response = client.post(
            f"/tickets/{ticket['id']}/tags",
            json={"tag_ids": []},
        )
        assert response.status_code == 422

    def test_add_tags_invalid_tag_returns_404(self, client):
        ticket = client.post("/tickets", json={"title": "Test", "status": "open"}).json()
        
        response = client.post(
            f"/tickets/{ticket['id']}/tags",
            json={"tag_ids": [99999]},
        )
        assert response.status_code == 404

    def test_remove_tag_from_ticket(self, client):
        ticket = client.post("/tickets", json={"title": "Test", "status": "open"}).json()
        tag = client.post("/tags", json={"name": "Bug"}).json()
        
        client.post(f"/tickets/{ticket['id']}/tags", json={"tag_ids": [tag["id"]]})
        
        response = client.delete(f"/tickets/{ticket['id']}/tags/{tag['id']}")
        assert response.status_code == 200
        assert len(response.json()["tags"]) == 0

    def test_remove_nonexistent_tag_from_ticket(self, client):
        ticket = client.post("/tickets", json={"title": "Test", "status": "open"}).json()
        tag = client.post("/tags", json={"name": "Bug"}).json()
        
        response = client.delete(f"/tickets/{ticket['id']}/tags/{tag['id']}")
        assert response.status_code == 200

    def test_remove_invalid_tag_returns_404(self, client):
        ticket = client.post("/tickets", json={"title": "Test", "status": "open"}).json()
        
        response = client.delete(f"/tickets/{ticket['id']}/tags/99999")
        assert response.status_code == 404

    def test_update_ticket_with_tag_ids(self, client):
        tag1 = client.post("/tags", json={"name": "Bug"}).json()
        tag2 = client.post("/tags", json={"name": "Feature"}).json()
        
        ticket = client.post(
            "/tickets",
            json={"title": "Test", "status": "open", "tag_ids": [tag1["id"]]}
        ).json()
        
        response = client.patch(
            f"/tickets/{ticket['id']}",
            json={"status": "in_progress", "tag_ids": [tag2["id"]]},
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "in_progress"
        assert len(data["tags"]) == 1
        assert data["tags"][0]["name"] == "Feature"

    def test_update_ticket_remove_all_tags(self, client):
        tag = client.post("/tags", json={"name": "Bug"}).json()
        
        ticket = client.post(
            "/tickets",
            json={"title": "Test", "status": "open", "tag_ids": [tag["id"]]}
        ).json()
        
        response = client.patch(
            f"/tickets/{ticket['id']}",
            json={"status": "in_progress", "tag_ids": []},
        )
        assert response.status_code == 200
        assert len(response.json()["tags"]) == 0


class TestTicketTagFiltering:
    def test_filter_tickets_by_single_tag(self, client):
        tag1 = client.post("/tags", json={"name": "Bug"}).json()
        tag2 = client.post("/tags", json={"name": "Feature"}).json()
        
        client.post("/tickets", json={"title": "Bug ticket", "status": "open", "tag_ids": [tag1["id"]]})
        client.post("/tickets", json={"title": "Feature ticket", "status": "open", "tag_ids": [tag2["id"]]})
        client.post("/tickets", json={"title": "No tag", "status": "open"})
        
        response = client.get(f"/tickets?tag_ids={tag1['id']}")
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["title"] == "Bug ticket"

    def test_filter_tickets_by_multiple_tags(self, client):
        tag1 = client.post("/tags", json={"name": "Bug"}).json()
        tag2 = client.post("/tags", json={"name": "Urgent"}).json()
        
        client.post(
            "/tickets",
            json={"title": "Urgent Bug", "status": "open", "tag_ids": [tag1["id"], tag2["id"]]}
        )
        client.post(
            "/tickets",
            json={"title": "Just Bug", "status": "open", "tag_ids": [tag1["id"]]}
        )
        
        response = client.get(f"/tickets?tag_ids={tag1['id']}&tag_ids={tag2['id']}")
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["title"] == "Urgent Bug"

    def test_filter_tickets_by_status_and_tag(self, client):
        tag = client.post("/tags", json={"name": "Bug"}).json()
        
        client.post(
            "/tickets",
            json={"title": "Open Bug", "status": "open", "tag_ids": [tag["id"]]}
        )
        client.post(
            "/tickets",
            json={"title": "Resolved Bug", "status": "resolved", "tag_ids": [tag["id"]]}
        )
        
        response = client.get(f"/tickets?status=open&tag_ids={tag['id']}")
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["title"] == "Open Bug"


class TestTagUsage:
    def test_tag_usage_counts(self, client):
        tag1 = client.post("/tags", json={"name": "Bug"}).json()
        tag2 = client.post("/tags", json={"name": "Feature"}).json()
        client.post("/tags", json={"name": "Unused"})
        
        client.post("/tickets", json={"title": "T1", "status": "open", "tag_ids": [tag1["id"]]})
        client.post("/tickets", json={"title": "T2", "status": "open", "tag_ids": [tag1["id"]]})
        client.post("/tickets", json={"title": "T3", "status": "open", "tag_ids": [tag2["id"]]})
        
        response = client.get("/tags/usage")
        assert response.status_code == 200
        
        usage_data = response.json()
        usage_dict = {item["name"]: item["ticket_count"] for item in usage_data}
        
        assert usage_dict["Bug"] == 2
        assert usage_dict["Feature"] == 1
        assert usage_dict["Unused"] == 0

    def test_tag_usage_sorted_by_count_desc(self, client):
        tag1 = client.post("/tags", json={"name": "High"}).json()
        tag2 = client.post("/tags", json={"name": "Medium"}).json()
        tag3 = client.post("/tags", json={"name": "Low"}).json()
        
        client.post("/tickets", json={"title": "T1", "status": "open", "tag_ids": [tag1["id"]]})
        client.post("/tickets", json={"title": "T2", "status": "open", "tag_ids": [tag1["id"]]})
        client.post("/tickets", json={"title": "T3", "status": "open", "tag_ids": [tag2["id"]]})
        
        response = client.get("/tags/usage")
        assert response.status_code == 200
        
        names = [item["name"] for item in response.json()]
        assert names.index("High") < names.index("Medium")
        assert names.index("Medium") < names.index("Low")


class TestCascadeDelete:
    def test_delete_tag_removes_from_tickets(self, client):
        tag = client.post("/tags", json={"name": "Bug"}).json()
        
        ticket = client.post(
            "/tickets",
            json={"title": "Test", "status": "open", "tag_ids": [tag["id"]]}
        ).json()
        
        client.delete(f"/tags/{tag['id']}")
        
        response = client.get(f"/tickets/{ticket['id']}")
        assert response.status_code == 200
        assert len(response.json()["tags"]) == 0

    def test_delete_ticket_removes_tag_associations(self, client):
        tag = client.post("/tags", json={"name": "Bug"}).json()
        
        ticket = client.post(
            "/tickets",
            json={"title": "Test", "status": "open", "tag_ids": [tag["id"]]}
        ).json()
        
        client.delete(f"/tickets/{ticket['id']}")
        
        response = client.get("/tags/usage")
        assert response.status_code == 200
        
        for item in response.json():
            if item["name"] == "Bug":
                assert item["ticket_count"] == 0
                break
