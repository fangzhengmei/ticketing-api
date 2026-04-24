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


class TestTagMerge:
    def test_merge_tags_basic(self, client):
        target = client.post("/tags", json={"name": "Bug", "color": "#ef4444"}).json()
        source1 = client.post("/tags", json={"name": "bug", "color": "#ff0000"}).json()
        source2 = client.post("/tags", json={"name": "BUG", "color": "#cc0000"}).json()
        
        client.post("/tickets", json={"title": "T1", "status": "open", "tag_ids": [source1["id"]]})
        client.post("/tickets", json={"title": "T2", "status": "open", "tag_ids": [source2["id"]]})
        client.post("/tickets", json={"title": "T3", "status": "open", "tag_ids": [target["id"]]})
        
        response = client.post(
            "/tags/merge",
            json={
                "target_tag_id": target["id"],
                "source_tag_ids": [source1["id"], source2["id"]]
            },
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["target_tag"]["id"] == target["id"]
        assert data["target_tag"]["name"] == "Bug"
        assert data["migrated_ticket_count"] == 2
        assert data["deleted_tag_count"] == 2
        assert "bug" in data["deleted_tag_names"]
        assert "BUG" in data["deleted_tag_names"]
        
        assert client.get(f"/tags/{source1['id']}").status_code == 404
        assert client.get(f"/tags/{source2['id']}").status_code == 404
        
        usage = client.get("/tags/usage").json()
        for item in usage:
            if item["name"] == "Bug":
                assert item["ticket_count"] == 3
                break

    def test_merge_tags_idempotent(self, client):
        target = client.post("/tags", json={"name": "Bug"}).json()
        source = client.post("/tags", json={"name": "bug"}).json()
        
        ticket = client.post(
            "/tickets",
            json={"title": "T1", "status": "open", "tag_ids": [target["id"], source["id"]]}
        ).json()
        
        response = client.post(
            "/tags/merge",
            json={
                "target_tag_id": target["id"],
                "source_tag_ids": [source["id"]]
            },
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["migrated_ticket_count"] == 0
        
        ticket_updated = client.get(f"/tickets/{ticket['id']}").json()
        assert len(ticket_updated["tags"]) == 1
        assert ticket_updated["tags"][0]["name"] == "Bug"

    def test_merge_tags_empty_source_returns_422(self, client):
        target = client.post("/tags", json={"name": "Bug"}).json()
        
        response = client.post(
            "/tags/merge",
            json={
                "target_tag_id": target["id"],
                "source_tag_ids": []
            },
        )
        assert response.status_code == 422

    def test_merge_tags_target_in_source_returns_400(self, client):
        target = client.post("/tags", json={"name": "Bug"}).json()
        source = client.post("/tags", json={"name": "bug"}).json()
        
        response = client.post(
            "/tags/merge",
            json={
                "target_tag_id": target["id"],
                "source_tag_ids": [target["id"], source["id"]]
            },
        )
        assert response.status_code == 400
        assert "target_tag_id cannot be in source_tag_ids" in response.json()["detail"]

    def test_merge_tags_source_not_found_returns_404(self, client):
        target = client.post("/tags", json={"name": "Bug"}).json()
        
        response = client.post(
            "/tags/merge",
            json={
                "target_tag_id": target["id"],
                "source_tag_ids": [99999]
            },
        )
        assert response.status_code == 404
        assert "Source tags not found" in response.json()["detail"]

    def test_merge_tags_target_not_found_returns_404(self, client):
        source = client.post("/tags", json={"name": "bug"}).json()
        
        response = client.post(
            "/tags/merge",
            json={
                "target_tag_id": 99999,
                "source_tag_ids": [source["id"]]
            },
        )
        assert response.status_code == 404
        assert "Tag not found" in response.json()["detail"]

    def test_merge_tags_with_duplicates_in_source(self, client):
        target = client.post("/tags", json={"name": "Bug"}).json()
        source = client.post("/tags", json={"name": "bug"}).json()
        
        client.post("/tickets", json={"title": "T1", "status": "open", "tag_ids": [source["id"]]})
        
        response = client.post(
            "/tags/merge",
            json={
                "target_tag_id": target["id"],
                "source_tag_ids": [source["id"], source["id"], source["id"]]
            },
        )
        assert response.status_code == 200
        assert response.json()["deleted_tag_count"] == 1

    def test_merge_unused_tags(self, client):
        target = client.post("/tags", json={"name": "Bug"}).json()
        source1 = client.post("/tags", json={"name": "bug"}).json()
        source2 = client.post("/tags", json={"name": "BUG"}).json()
        
        response = client.post(
            "/tags/merge",
            json={
                "target_tag_id": target["id"],
                "source_tag_ids": [source1["id"], source2["id"]]
            },
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["migrated_ticket_count"] == 0
        assert data["deleted_tag_count"] == 2


class TestTagMergePreview:
    def test_preview_merge_basic(self, client):
        target = client.post("/tags", json={"name": "Bug", "color": "#ef4444"}).json()
        source1 = client.post("/tags", json={"name": "bug", "color": "#ff0000"}).json()
        source2 = client.post("/tags", json={"name": "BUG", "color": "#cc0000"}).json()
        
        client.post("/tickets", json={"title": "T1", "status": "open", "tag_ids": [source1["id"]]})
        client.post("/tickets", json={"title": "T2", "status": "open", "tag_ids": [source2["id"]]})
        client.post("/tickets", json={"title": "T3", "status": "open", "tag_ids": [target["id"]]})
        
        response = client.post(
            "/tags/merge/preview",
            json={
                "target_tag_id": target["id"],
                "source_tag_ids": [source1["id"], source2["id"]]
            },
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["target_tag"]["id"] == target["id"]
        assert data["target_tag"]["name"] == "Bug"
        assert data["target_current_ticket_count"] == 1
        assert data["target_after_merge_ticket_count"] == 3
        assert data["tickets_to_migrate"] == 2
        assert data["total_tags_to_delete"] == 2
        
        assert len(data["sources_to_delete"]) == 2
        source_names = {s["name"] for s in data["sources_to_delete"]}
        assert source_names == {"bug", "BUG"}
        
        for s in data["sources_to_delete"]:
            if s["name"] == "bug":
                assert s["current_ticket_count"] == 1
            elif s["name"] == "BUG":
                assert s["current_ticket_count"] == 1

    def test_preview_merge_idempotent(self, client):
        target = client.post("/tags", json={"name": "Bug"}).json()
        source = client.post("/tags", json={"name": "bug"}).json()
        
        client.post(
            "/tickets",
            json={"title": "T1", "status": "open", "tag_ids": [target["id"], source["id"]]}
        )
        
        response = client.post(
            "/tags/merge/preview",
            json={
                "target_tag_id": target["id"],
                "source_tag_ids": [source["id"]]
            },
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["tickets_to_migrate"] == 0
        assert data["target_current_ticket_count"] == 1
        assert data["target_after_merge_ticket_count"] == 1

    def test_preview_merge_does_not_modify_data(self, client):
        target = client.post("/tags", json={"name": "Bug"}).json()
        source = client.post("/tags", json={"name": "bug"}).json()
        
        client.post("/tickets", json={"title": "T1", "status": "open", "tag_ids": [source["id"]]})
        
        client.post(
            "/tags/merge/preview",
            json={
                "target_tag_id": target["id"],
                "source_tag_ids": [source["id"]]
            },
        )
        
        assert client.get(f"/tags/{source['id']}").status_code == 200
        
        ticket_response = client.get("/tickets")
        assert ticket_response.status_code == 200
        ticket = ticket_response.json()["items"][0]
        ticket_tags = {t["name"] for t in ticket["tags"]}
        assert "bug" in ticket_tags
        assert "Bug" not in ticket_tags

    def test_preview_merge_empty_source_returns_422(self, client):
        target = client.post("/tags", json={"name": "Bug"}).json()
        
        response = client.post(
            "/tags/merge/preview",
            json={
                "target_tag_id": target["id"],
                "source_tag_ids": []
            },
        )
        assert response.status_code == 422

    def test_preview_merge_target_in_source_returns_400(self, client):
        target = client.post("/tags", json={"name": "Bug"}).json()
        source = client.post("/tags", json={"name": "bug"}).json()
        
        response = client.post(
            "/tags/merge/preview",
            json={
                "target_tag_id": target["id"],
                "source_tag_ids": [target["id"], source["id"]]
            },
        )
        assert response.status_code == 400
        assert "target_tag_id cannot be in source_tag_ids" in response.json()["detail"]

    def test_preview_merge_source_not_found_returns_404(self, client):
        target = client.post("/tags", json={"name": "Bug"}).json()
        
        response = client.post(
            "/tags/merge/preview",
            json={
                "target_tag_id": target["id"],
                "source_tag_ids": [99999]
            },
        )
        assert response.status_code == 404
        assert "Source tags not found" in response.json()["detail"]

    def test_preview_merge_target_not_found_returns_404(self, client):
        source = client.post("/tags", json={"name": "bug"}).json()
        
        response = client.post(
            "/tags/merge/preview",
            json={
                "target_tag_id": 99999,
                "source_tag_ids": [source["id"]]
            },
        )
        assert response.status_code == 404
        assert "Tag not found" in response.json()["detail"]

    def test_preview_merge_unused_tags(self, client):
        target = client.post("/tags", json={"name": "Bug"}).json()
        source1 = client.post("/tags", json={"name": "bug"}).json()
        source2 = client.post("/tags", json={"name": "BUG"}).json()
        
        response = client.post(
            "/tags/merge/preview",
            json={
                "target_tag_id": target["id"],
                "source_tag_ids": [source1["id"], source2["id"]]
            },
        )
        assert response.status_code == 200
        
        data = response.json()
        assert data["tickets_to_migrate"] == 0
        assert data["target_current_ticket_count"] == 0
        assert data["target_after_merge_ticket_count"] == 0
        assert data["total_tags_to_delete"] == 2

    def test_preview_merge_with_duplicates_in_source(self, client):
        target = client.post("/tags", json={"name": "Bug"}).json()
        source = client.post("/tags", json={"name": "bug"}).json()
        
        client.post("/tickets", json={"title": "T1", "status": "open", "tag_ids": [source["id"]]})
        
        response = client.post(
            "/tags/merge/preview",
            json={
                "target_tag_id": target["id"],
                "source_tag_ids": [source["id"], source["id"], source["id"]]
            },
        )
        assert response.status_code == 200
        assert response.json()["total_tags_to_delete"] == 1


class TestTagMergeHistory:
    def test_merge_creates_history(self, client):
        target = client.post("/tags", json={"name": "Bug", "color": "#ef4444"}).json()
        source1 = client.post("/tags", json={"name": "bug", "color": "#ff0000"}).json()
        source2 = client.post("/tags", json={"name": "BUG", "color": "#cc0000"}).json()
        
        client.post("/tickets", json={"title": "T1", "status": "open", "tag_ids": [source1["id"]]})
        client.post("/tickets", json={"title": "T2", "status": "open", "tag_ids": [source2["id"]]})
        
        history_before = client.get("/tags/merge/history").json()
        assert history_before["total"] == 0
        
        client.post(
            "/tags/merge",
            json={
                "target_tag_id": target["id"],
                "source_tag_ids": [source1["id"], source2["id"]]
            },
        )
        
        history_after = client.get("/tags/merge/history").json()
        assert history_after["total"] == 1
        assert len(history_after["items"]) == 1
        
        history_item = history_after["items"][0]
        assert history_item["target_tag_id"] == target["id"]
        assert history_item["target_tag_name"] == "Bug"
        assert history_item["target_tag_color"] == "#ef4444"
        assert history_item["migrated_ticket_count"] == 2
        assert history_item["deleted_tag_count"] == 2
        assert "created_at" in history_item
        
        source_names = {s["name"] for s in history_item["source_tags"]}
        assert source_names == {"bug", "BUG"}
        
        for s in history_item["source_tags"]:
            if s["name"] == "bug":
                assert s["current_ticket_count"] == 1
            elif s["name"] == "BUG":
                assert s["current_ticket_count"] == 1

    def test_list_history_pagination(self, client):
        for i in range(3):
            target = client.post("/tags", json={"name": f"Target{i}"}).json()
            source = client.post("/tags", json={"name": f"Source{i}"}).json()
            client.post(
                "/tags/merge",
                json={
                    "target_tag_id": target["id"],
                    "source_tag_ids": [source["id"]]
                },
            )
        
        response = client.get("/tags/merge/history?limit=2&offset=0")
        assert response.status_code == 200
        assert response.json()["total"] == 3
        assert len(response.json()["items"]) == 2
        assert response.json()["limit"] == 2
        assert response.json()["offset"] == 0

    def test_list_history_sorted_by_created_at_desc(self, client):
        target1 = client.post("/tags", json={"name": "Target1"}).json()
        source1 = client.post("/tags", json={"name": "Source1"}).json()
        client.post(
            "/tags/merge",
            json={
                "target_tag_id": target1["id"],
                "source_tag_ids": [source1["id"]]
            },
        )
        
        target2 = client.post("/tags", json={"name": "Target2"}).json()
        source2 = client.post("/tags", json={"name": "Source2"}).json()
        client.post(
            "/tags/merge",
            json={
                "target_tag_id": target2["id"],
                "source_tag_ids": [source2["id"]]
            },
        )
        
        response = client.get("/tags/merge/history")
        assert response.status_code == 200
        assert len(response.json()["items"]) == 2
        
        first_created = response.json()["items"][0]["created_at"]
        second_created = response.json()["items"][1]["created_at"]
        assert first_created >= second_created

    def test_list_history_filter_by_target_tag_id(self, client):
        target1 = client.post("/tags", json={"name": "Bug"}).json()
        source1 = client.post("/tags", json={"name": "bug"}).json()
        
        target2 = client.post("/tags", json={"name": "Feature"}).json()
        source2 = client.post("/tags", json={"name": "feature"}).json()
        
        client.post(
            "/tags/merge",
            json={
                "target_tag_id": target1["id"],
                "source_tag_ids": [source1["id"]]
            },
        )
        client.post(
            "/tags/merge",
            json={
                "target_tag_id": target2["id"],
                "source_tag_ids": [source2["id"]]
            },
        )
        
        response = client.get(f"/tags/merge/history?target_tag_id={target1['id']}")
        assert response.status_code == 200
        assert response.json()["total"] == 1
        assert response.json()["items"][0]["target_tag_name"] == "Bug"

    def test_get_history_by_id(self, client):
        target = client.post("/tags", json={"name": "Bug", "color": "#ef4444"}).json()
        source = client.post("/tags", json={"name": "bug", "color": "#ff0000"}).json()
        
        client.post("/tickets", json={"title": "T1", "status": "open", "tag_ids": [source["id"]]})
        
        client.post(
            "/tags/merge",
            json={
                "target_tag_id": target["id"],
                "source_tag_ids": [source["id"]]
            },
        )
        
        history_list = client.get("/tags/merge/history").json()
        history_id = history_list["items"][0]["id"]
        
        response = client.get(f"/tags/merge/history/{history_id}")
        assert response.status_code == 200
        
        history_item = response.json()
        assert history_item["target_tag_id"] == target["id"]
        assert history_item["target_tag_name"] == "Bug"
        assert history_item["migrated_ticket_count"] == 1
        assert len(history_item["source_tags"]) == 1
        assert history_item["source_tags"][0]["name"] == "bug"
        assert history_item["source_tags"][0]["current_ticket_count"] == 1

    def test_get_history_not_found_returns_404(self, client):
        response = client.get("/tags/merge/history/99999")
        assert response.status_code == 404
        assert response.json()["detail"] == "Merge history not found"

    def test_history_snapshot_preserved_after_source_deleted(self, client):
        target = client.post("/tags", json={"name": "Bug", "color": "#ef4444"}).json()
        source = client.post("/tags", json={"name": "bug", "color": "#ff0000"}).json()
        
        client.post("/tickets", json={"title": "T1", "status": "open", "tag_ids": [source["id"]]})
        
        client.post(
            "/tags/merge",
            json={
                "target_tag_id": target["id"],
                "source_tag_ids": [source["id"]]
            },
        )
        
        assert client.get(f"/tags/{source['id']}").status_code == 404
        
        history_list = client.get("/tags/merge/history").json()
        history_item = history_list["items"][0]
        
        assert history_item["source_tags"][0]["id"] == source["id"]
        assert history_item["source_tags"][0]["name"] == "bug"
        assert history_item["source_tags"][0]["color"] == "#ff0000"
