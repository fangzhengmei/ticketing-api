import os
import sys
import unittest
from datetime import datetime, timedelta, timezone

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool
from fastapi import HTTPException

from app.database import Base
from app.db_models import TicketDB
from app.models import TicketCreate, TicketUpdate, TicketStatus
from app.services import tickets as tickets_service


def _utcnow():
    return datetime.now(timezone.utc).replace(tzinfo=None)


class BaseTicketTestCase(unittest.TestCase):
    def setUp(self):
        self.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(self.engine)
        Session = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        self.db = Session()

    def tearDown(self):
        self.db.close()
        Base.metadata.drop_all(self.engine)

    def _create_ticket(self, title, status=TicketStatus.open, deadline=None):
        payload = TicketCreate(title=title, status=status, deadline=deadline)
        return tickets_service.create_ticket(self.db, payload)


class TestTicketCRUD(BaseTicketTestCase):
    def test_create_ticket_basic(self):
        ticket = self._create_ticket("Test ticket")
        self.assertIsNotNone(ticket.id)
        self.assertEqual(ticket.title, "Test ticket")
        self.assertEqual(ticket.status, "open")

    def test_create_ticket_with_deadline(self):
        future_deadline = _utcnow() + timedelta(days=1)
        ticket = self._create_ticket("Ticket with deadline", deadline=future_deadline)
        self.assertIsNotNone(ticket.deadline)
        self.assertEqual(ticket.deadline, future_deadline)

    def test_create_ticket_without_deadline(self):
        ticket = self._create_ticket("Ticket without deadline")
        self.assertIsNone(ticket.deadline)

    def test_get_ticket_not_found(self):
        with self.assertRaises(HTTPException) as context:
            tickets_service.get_ticket(self.db, 999999)
        self.assertEqual(context.exception.status_code, 404)
        self.assertEqual(context.exception.detail, "Ticket not found")

    def test_get_ticket_success(self):
        created = self._create_ticket("Test ticket")
        fetched = tickets_service.get_ticket(self.db, created.id)
        self.assertEqual(fetched.id, created.id)
        self.assertEqual(fetched.title, "Test ticket")

    def test_list_tickets_returns_metadata(self):
        self._create_ticket("Ticket A")
        self._create_ticket("Ticket B")
        
        result = tickets_service.list_tickets(self.db, limit=1, offset=0)
        
        self.assertIn("total", result)
        self.assertIn("limit", result)
        self.assertIn("offset", result)
        self.assertIn("items", result)
        self.assertEqual(result["total"], 2)
        self.assertEqual(result["limit"], 1)
        self.assertEqual(result["offset"], 0)
        self.assertEqual(len(result["items"]), 1)

    def test_list_tickets_offset_beyond_total(self):
        self._create_ticket("A")
        self._create_ticket("B")
        
        result = tickets_service.list_tickets(self.db, limit=10, offset=999)
        
        self.assertEqual(result["total"], 2)
        self.assertEqual(len(result["items"]), 0)

    def test_delete_ticket_success(self):
        created = self._create_ticket("To delete")
        tickets_service.delete_ticket(self.db, created.id)
        
        with self.assertRaises(HTTPException) as context:
            tickets_service.get_ticket(self.db, created.id)
        self.assertEqual(context.exception.status_code, 404)

    def test_delete_ticket_not_found(self):
        with self.assertRaises(HTTPException) as context:
            tickets_service.delete_ticket(self.db, 999999)
        self.assertEqual(context.exception.status_code, 404)


class TestStatusTransitions(BaseTicketTestCase):
    def test_allowed_transitions(self):
        transitions = [
            (TicketStatus.open, TicketStatus.in_progress),
            (TicketStatus.open, TicketStatus.resolved),
            (TicketStatus.in_progress, TicketStatus.resolved),
        ]
        
        for start_status, new_status in transitions:
            with self.subTest(start_status=start_status, new_status=new_status):
                ticket = self._create_ticket(f"Test {start_status} -> {new_status}", status=start_status)
                payload = TicketUpdate(status=new_status)
                updated = tickets_service.update_ticket(self.db, ticket.id, payload)
                self.assertEqual(updated.status, new_status.value)

    def test_forbidden_transitions(self):
        transitions = [
            (TicketStatus.resolved, TicketStatus.open),
            (TicketStatus.resolved, TicketStatus.in_progress),
            (TicketStatus.in_progress, TicketStatus.open),
        ]
        
        for start_status, new_status in transitions:
            with self.subTest(start_status=start_status, new_status=new_status):
                ticket = self._create_ticket(f"Test {start_status} -> {new_status}", status=start_status)
                payload = TicketUpdate(status=new_status)
                
                with self.assertRaises(HTTPException) as context:
                    tickets_service.update_ticket(self.db, ticket.id, payload)
                self.assertEqual(context.exception.status_code, 409)
                self.assertEqual(context.exception.detail, "Invalid status transition")

    def test_patch_ticket_not_found(self):
        payload = TicketUpdate(status=TicketStatus.resolved)
        with self.assertRaises(HTTPException) as context:
            tickets_service.update_ticket(self.db, 999999, payload)
        self.assertEqual(context.exception.status_code, 404)

    def test_same_status_update_allowed(self):
        ticket = self._create_ticket("Test", status=TicketStatus.open)
        payload = TicketUpdate(status=TicketStatus.open)
        updated = tickets_service.update_ticket(self.db, ticket.id, payload)
        self.assertEqual(updated.status, "open")


class TestDeadlineAndIsOverdue(BaseTicketTestCase):
    def test_is_overdue_not_expired_ticket(self):
        future_deadline = _utcnow() + timedelta(days=7)
        ticket = self._create_ticket("Not expired", deadline=future_deadline)
        
        self.assertEqual(ticket.status, "open")
        self.assertFalse(tickets_service.calculate_is_overdue(ticket))

    def test_is_overdue_expired_open_ticket(self):
        past_deadline = _utcnow() - timedelta(hours=1)
        ticket = self._create_ticket("Expired open", status=TicketStatus.open, deadline=past_deadline)
        
        self.assertTrue(tickets_service.calculate_is_overdue(ticket))

    def test_is_overdue_expired_in_progress_ticket(self):
        past_deadline = _utcnow() - timedelta(hours=1)
        ticket = self._create_ticket("Expired in progress", status=TicketStatus.in_progress, deadline=past_deadline)
        
        self.assertTrue(tickets_service.calculate_is_overdue(ticket))

    def test_is_overdue_resolved_ticket_not_expired(self):
        future_deadline = _utcnow() + timedelta(days=1)
        ticket = self._create_ticket("Will be resolved", deadline=future_deadline)
        
        self.assertFalse(tickets_service.calculate_is_overdue(ticket))
        
        payload = TicketUpdate(status=TicketStatus.resolved)
        updated = tickets_service.update_ticket(self.db, ticket.id, payload)
        
        self.assertEqual(updated.status, "resolved")
        self.assertFalse(tickets_service.calculate_is_overdue(updated))

    def test_is_overdue_resolved_ticket_even_if_deadline_passed(self):
        past_deadline = _utcnow() - timedelta(hours=1)
        ticket = self._create_ticket("Resolved after deadline", deadline=past_deadline)
        
        self.assertTrue(tickets_service.calculate_is_overdue(ticket))
        
        payload = TicketUpdate(status=TicketStatus.resolved)
        updated = tickets_service.update_ticket(self.db, ticket.id, payload)
        
        self.assertEqual(updated.status, "resolved")
        self.assertFalse(tickets_service.calculate_is_overdue(updated))

    def test_is_overdue_no_deadline(self):
        ticket = self._create_ticket("No deadline")
        
        self.assertIsNone(ticket.deadline)
        self.assertFalse(tickets_service.calculate_is_overdue(ticket))


class TestUpdateDeadline(BaseTicketTestCase):
    def test_patch_update_deadline(self):
        ticket = self._create_ticket("Ticket to update deadline")
        self.assertIsNone(ticket.deadline)
        
        future_deadline = _utcnow() + timedelta(days=3)
        payload = TicketUpdate(deadline=future_deadline)
        updated = tickets_service.update_ticket(self.db, ticket.id, payload)
        
        self.assertIsNotNone(updated.deadline)
        self.assertEqual(updated.deadline, future_deadline)

    def test_patch_clear_deadline_with_null(self):
        future_deadline = _utcnow() + timedelta(days=3)
        ticket = self._create_ticket("Ticket with deadline", deadline=future_deadline)
        self.assertIsNotNone(ticket.deadline)
        
        payload = TicketUpdate(deadline=None)
        updated = tickets_service.update_ticket(self.db, ticket.id, payload)
        
        self.assertIsNone(updated.deadline)
        
        fetched = tickets_service.get_ticket(self.db, ticket.id)
        self.assertIsNone(fetched.deadline)
        self.assertFalse(tickets_service.calculate_is_overdue(fetched))

    def test_patch_empty_body_does_not_change_deadline(self):
        future_deadline = _utcnow() + timedelta(days=3)
        ticket = self._create_ticket("Ticket with deadline", deadline=future_deadline)
        original_deadline = ticket.deadline
        
        payload = TicketUpdate()
        updated = tickets_service.update_ticket(self.db, ticket.id, payload)
        
        self.assertIsNotNone(updated.deadline)
        self.assertEqual(updated.deadline, original_deadline)

    def test_patch_update_status_and_deadline_together(self):
        ticket = self._create_ticket("Test", status=TicketStatus.open)
        
        future_deadline = _utcnow() + timedelta(days=1)
        payload = TicketUpdate(status=TicketStatus.in_progress, deadline=future_deadline)
        updated = tickets_service.update_ticket(self.db, ticket.id, payload)
        
        self.assertEqual(updated.status, "in_progress")
        self.assertEqual(updated.deadline, future_deadline)


class TestFilterByIsOverdue(BaseTicketTestCase):
    def test_filter_tickets_by_is_overdue_true(self):
        past_deadline = _utcnow() - timedelta(hours=1)
        future_deadline = _utcnow() + timedelta(days=1)
        
        self._create_ticket("Expired 1", status=TicketStatus.open, deadline=past_deadline)
        self._create_ticket("Expired 2", status=TicketStatus.in_progress, deadline=past_deadline)
        self._create_ticket("Not expired", deadline=future_deadline)
        self._create_ticket("No deadline")
        
        result = tickets_service.list_tickets(self.db, limit=100, offset=0, is_overdue=True)
        
        self.assertEqual(result["total"], 2)
        self.assertEqual(len(result["items"]), 2)
        for item in result["items"]:
            self.assertTrue(tickets_service.calculate_is_overdue(item))

    def test_filter_tickets_by_is_overdue_false(self):
        past_deadline = _utcnow() - timedelta(hours=1)
        future_deadline = _utcnow() + timedelta(days=1)
        
        self._create_ticket("Expired open", status=TicketStatus.open, deadline=past_deadline)
        self._create_ticket("Not expired", deadline=future_deadline)
        self._create_ticket("No deadline")
        self._create_ticket("Resolved but expired", status=TicketStatus.resolved, deadline=past_deadline)
        
        result = tickets_service.list_tickets(self.db, limit=100, offset=0, is_overdue=False)
        
        self.assertEqual(result["total"], 3)
        for item in result["items"]:
            self.assertFalse(tickets_service.calculate_is_overdue(item))

    def test_filter_without_is_overdue_returns_all(self):
        past_deadline = _utcnow() - timedelta(hours=1)
        future_deadline = _utcnow() + timedelta(days=1)
        
        self._create_ticket("Expired", deadline=past_deadline)
        self._create_ticket("Not expired", deadline=future_deadline)
        self._create_ticket("No deadline")
        
        result = tickets_service.list_tickets(self.db, limit=100, offset=0)
        
        self.assertEqual(result["total"], 3)


if __name__ == "__main__":
    unittest.main(verbosity=2)
