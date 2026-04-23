import pytest


@pytest.fixture
def create_ticket(client):
    def _create_ticket(title, status="open"):
        response = client.post(
            "/tickets",
            json={"title": title, "status": status},
        )
        assert response.status_code == 201
        return response.json()
    return _create_ticket


@pytest.fixture
def create_comment(client):
    def _create_comment(ticket_id, content, author=None):
        payload = {"content": content}
        if author:
            payload["author"] = author
        response = client.post(
            f"/tickets/{ticket_id}/comments",
            json=payload,
        )
        assert response.status_code == 201
        return response.json()
    return _create_comment


class TestCommentCRUD:
    def test_create_comment_success(self, client, create_ticket):
        ticket = create_ticket("Test Ticket")
        ticket_id = ticket["id"]

        response = client.post(
            f"/tickets/{ticket_id}/comments",
            json={"content": "This is a test comment", "author": "Tester"},
        )

        assert response.status_code == 201
        data = response.json()
        assert "id" in data
        assert data["ticket_id"] == ticket_id
        assert data["original_ticket_id"] == ticket_id
        assert data["content"] == "This is a test comment"
        assert data["author"] == "Tester"
        assert "created_at" in data
        assert "updated_at" in data

    def test_create_comment_without_author(self, client, create_ticket):
        ticket = create_ticket("Test Ticket")
        ticket_id = ticket["id"]

        response = client.post(
            f"/tickets/{ticket_id}/comments",
            json={"content": "Comment without author"},
        )

        assert response.status_code == 201
        data = response.json()
        assert data["author"] is None

    def test_create_comment_missing_content_returns_422(self, client, create_ticket):
        ticket = create_ticket("Test Ticket")
        ticket_id = ticket["id"]

        response = client.post(
            f"/tickets/{ticket_id}/comments",
            json={},
        )

        assert response.status_code == 422

    def test_create_comment_empty_content_returns_422(self, client, create_ticket):
        ticket = create_ticket("Test Ticket")
        ticket_id = ticket["id"]

        response = client.post(
            f"/tickets/{ticket_id}/comments",
            json={"content": ""},
        )

        assert response.status_code == 422

    def test_create_comment_for_nonexistent_ticket_returns_404(self, client):
        response = client.post(
            "/tickets/999999/comments",
            json={"content": "Test comment"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Ticket not found"

    def test_get_comment_success(self, client, create_ticket, create_comment):
        ticket = create_ticket("Test Ticket")
        comment = create_comment(ticket["id"], "Test comment")

        response = client.get(f"/comments/{comment['id']}")

        assert response.status_code == 200
        data = response.json()
        assert data["id"] == comment["id"]
        assert data["content"] == "Test comment"

    def test_get_comment_not_found_returns_404(self, client):
        response = client.get("/comments/999999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Comment not found"

    def test_update_comment_success(self, client, create_ticket, create_comment):
        ticket = create_ticket("Test Ticket")
        comment = create_comment(ticket["id"], "Original content")

        response = client.patch(
            f"/comments/{comment['id']}",
            json={"content": "Updated content"},
        )

        assert response.status_code == 200
        data = response.json()
        assert data["content"] == "Updated content"
        assert data["updated_at"] != data["created_at"]

    def test_update_comment_not_found_returns_404(self, client):
        response = client.patch(
            "/comments/999999",
            json={"content": "Updated"},
        )

        assert response.status_code == 404
        assert response.json()["detail"] == "Comment not found"

    def test_delete_comment_success(self, client, create_ticket, create_comment):
        ticket = create_ticket("Test Ticket")
        comment = create_comment(ticket["id"], "To delete")

        delete_response = client.delete(f"/comments/{comment['id']}")
        assert delete_response.status_code == 204

        get_response = client.get(f"/comments/{comment['id']}")
        assert get_response.status_code == 404

    def test_delete_comment_not_found_returns_404(self, client):
        response = client.delete("/comments/999999")

        assert response.status_code == 404
        assert response.json()["detail"] == "Comment not found"

    def test_list_comments_returns_metadata(self, client, create_ticket, create_comment):
        ticket = create_ticket("Test Ticket")
        ticket_id = ticket["id"]

        create_comment(ticket_id, "Comment 1")
        create_comment(ticket_id, "Comment 2")

        response = client.get(f"/tickets/{ticket_id}/comments?limit=1&offset=0")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["limit"] == 1
        assert data["offset"] == 0
        assert len(data["items"]) == 1


class TestCommentMergeAggregation:
    def test_merge_ticket_comments_accessible_via_include_merged(self, client, create_ticket, create_comment):
        ticket1 = create_ticket("Main Ticket")
        ticket2 = create_ticket("Duplicate Ticket")

        create_comment(ticket1["id"], "Main ticket comment")
        create_comment(ticket2["id"], "Duplicate ticket comment")

        response = client.post(
            f"/tickets/{ticket2['id']}/merge",
            json={"target_ticket_id": ticket1["id"], "reason": "Duplicate"},
        )
        assert response.status_code == 200

        main_without = client.get(f"/tickets/{ticket1['id']}/comments?include_merged=false")
        assert main_without.status_code == 200
        assert main_without.json()["total"] == 1
        assert main_without.json()["items"][0]["content"] == "Main ticket comment"

        main_with = client.get(f"/tickets/{ticket1['id']}/comments?include_merged=true")
        assert main_with.status_code == 200
        assert main_with.json()["total"] == 2

        merged_comments = client.get(f"/tickets/{ticket2['id']}/comments")
        assert merged_comments.status_code == 200
        assert merged_comments.json()["total"] == 1
        assert merged_comments.json()["items"][0]["content"] == "Duplicate ticket comment"

    def test_include_merged_param_shows_all_comments(self, client, create_ticket, create_comment):
        ticket1 = create_ticket("Main Ticket")
        ticket2 = create_ticket("Duplicate Ticket")

        create_comment(ticket1["id"], "Main comment")
        create_comment(ticket2["id"], "Duplicate comment")

        client.post(
            f"/tickets/{ticket2['id']}/merge",
            json={"target_ticket_id": ticket1["id"], "reason": "Duplicate"},
        )

        response_with = client.get(f"/tickets/{ticket1['id']}/comments?include_merged=true")
        assert response_with.status_code == 200
        data_with = response_with.json()
        assert data_with["total"] == 2

        response_without = client.get(f"/tickets/{ticket1['id']}/comments?include_merged=false")
        assert response_without.status_code == 200
        data_without = response_without.json()
        assert data_without["total"] == 1
        assert data_without["items"][0]["content"] == "Main comment"

    def test_with_ticket_info_shows_original_ticket_title(self, client, create_ticket, create_comment):
        ticket1 = create_ticket("Login Error - Main")
        ticket2 = create_ticket("Cannot Login - Duplicate")

        create_comment(ticket1["id"], "This is the main ticket comment")
        create_comment(ticket2["id"], "This is from the duplicate ticket")

        client.post(
            f"/tickets/{ticket2['id']}/merge",
            json={"target_ticket_id": ticket1["id"], "reason": "Duplicate"},
        )

        response = client.get(f"/tickets/{ticket1['id']}/comments/with-ticket-info")
        assert response.status_code == 200
        data = response.json()

        assert data["total"] == 2

        for item in data["items"]:
            if item["content"] == "This is the main ticket comment":
                assert item["original_ticket_title"] == "Login Error - Main"
            elif item["content"] == "This is from the duplicate ticket":
                assert item["original_ticket_title"] == "Cannot Login - Duplicate"
            else:
                pytest.fail(f"Unexpected comment: {item['content']}")

    def test_unmerge_removes_merged_relation_comments_no_longer_aggregated(self, client, create_ticket, create_comment):
        ticket1 = create_ticket("Main Ticket")
        ticket2 = create_ticket("Duplicate Ticket")

        create_comment(ticket1["id"], "Main comment")
        create_comment(ticket2["id"], "Duplicate comment")

        client.post(
            f"/tickets/{ticket2['id']}/merge",
            json={"target_ticket_id": ticket1["id"], "reason": "Duplicate"},
        )

        main_after_merge = client.get(f"/tickets/{ticket1['id']}/comments?include_merged=true")
        assert main_after_merge.json()["total"] == 2

        client.post(f"/tickets/{ticket2['id']}/unmerge")

        main_after_unmerge = client.get(f"/tickets/{ticket1['id']}/comments?include_merged=true")
        assert main_after_unmerge.status_code == 200
        assert main_after_unmerge.json()["total"] == 1
        assert main_after_unmerge.json()["items"][0]["content"] == "Main comment"

        duplicate_after_unmerge = client.get(f"/tickets/{ticket2['id']}/comments")
        assert duplicate_after_unmerge.status_code == 200
        assert duplicate_after_unmerge.json()["total"] == 1
        assert duplicate_after_unmerge.json()["items"][0]["content"] == "Duplicate comment"

    def test_merge_multiple_tickets_comments_all_in_main(self, client, create_ticket, create_comment):
        main = create_ticket("Main Ticket")
        dup1 = create_ticket("Duplicate 1")
        dup2 = create_ticket("Duplicate 2")

        create_comment(main["id"], "Main comment")
        create_comment(dup1["id"], "Dup1 comment")
        create_comment(dup2["id"], "Dup2 comment")

        client.post(
            f"/tickets/{dup1['id']}/merge",
            json={"target_ticket_id": main["id"], "reason": "Dup1"},
        )
        client.post(
            f"/tickets/{dup2['id']}/merge",
            json={"target_ticket_id": main["id"], "reason": "Dup2"},
        )

        response = client.get(f"/tickets/{main['id']}/comments?include_merged=true")
        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3

        contents = {item["content"] for item in data["items"]}
        assert "Main comment" in contents
        assert "Dup1 comment" in contents
        assert "Dup2 comment" in contents

    def test_comment_ticket_id_unchanged_after_merge(self, client, create_ticket, create_comment):
        main = create_ticket("Main Ticket")
        dup = create_ticket("Duplicate Ticket")

        comment = create_comment(dup["id"], "From duplicate")

        client.post(
            f"/tickets/{dup['id']}/merge",
            json={"target_ticket_id": main["id"], "reason": "Duplicate"},
        )

        response = client.get(f"/comments/{comment['id']}")
        assert response.status_code == 200
        data = response.json()

        assert data["ticket_id"] == dup["id"]
        assert data["original_ticket_id"] == dup["id"]


class TestCommentListPagination:
    def test_list_comments_offset_beyond_total_returns_empty(self, client, create_ticket, create_comment):
        ticket = create_ticket("Test Ticket")
        create_comment(ticket["id"], "Comment 1")
        create_comment(ticket["id"], "Comment 2")

        response = client.get(f"/tickets/{ticket['id']}/comments?limit=10&offset=999")

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 2
        assert data["items"] == []

    def test_list_comments_limit_constraints(self, client, create_ticket):
        ticket = create_ticket("Test Ticket")
        ticket_id = ticket["id"]

        res = client.get(f"/tickets/{ticket_id}/comments?limit=0&offset=0")
        assert res.status_code == 422

        res = client.get(f"/tickets/{ticket_id}/comments?limit=101&offset=0")
        assert res.status_code == 422

        res = client.get(f"/tickets/{ticket_id}/comments?limit=1&offset=-1")
        assert res.status_code == 422
