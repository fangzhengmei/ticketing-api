# Ticketing API (FastAPI + SQLite + SQLAlchemy)

A simple REST API for managing support tickets.

## Features
- CRUD endpoints for tickets
- SQLite persistence via SQLAlchemy
- Pagination with metadata (`total`, `limit`, `offset`, `items`)
- Validation via Pydantic (Enums for status)
- Automated tests with `pytest`

## Tech Stack
- FastAPI
- SQLAlchemy
- SQLite
- Pydantic
- Pytest + FastAPI TestClient

## Project Structure
ticketing-api/
├── app/
│ ├── services/
│ │ └── tickets.py
│ ├── init.py
│ ├── database.py
│ ├── db_models.py
│ ├── models.py
│ └── routes.py
├── tests/
│ ├── conftest.py
│ └── test_tickets.py
├── main.py
└── tickets.db

## Setup

### 1) Create virtual environment
```bash
python -m venv .venv
source .venv/bin/activate
2) Install dependencies
pip install fastapi uvicorn sqlalchemy pydantic
pip install pytest httpx
Run the API
uvicorn main:app --reload --port 8001
Open Swagger UI:
http://127.0.0.1:8001/docs
API Endpoints
Health
GET /health
List tickets (paginated)
GET /tickets?limit=20&offset=0
Response shape:
{
  "total": 7,
  "limit": 20,
  "offset": 0,
  "items": [{ "id": 1, "title": "...", "status": "open" }]
}
Constraints:
limit: 1..100
offset: >= 0
Create ticket
POST /tickets
Body:
{
  "title": "My ticket",
  "status": "open"
}
Returns: 201 Created
Headers: includes Location: /tickets/{id} (if enabled)
Get ticket by id
GET /tickets/{ticket_id}
Returns:
200 if found
404 if not found
Update ticket status
PATCH /tickets/{ticket_id}
Body:
{ "status": "in_progress" }
Returns:
200 if updated
404 if not found
422 for invalid status
Delete ticket
DELETE /tickets/{ticket_id}
Returns:
204 No Content if deleted
404 if not found
Ticket Status Values
Allowed values:
open
in_progress
resolved
Run Tests
Important: use the venv python.
python -m pytest
(Optional) quieter output:
python -m pytest -q
Notes
The project uses SQLite (tickets.db) for local persistence.
Tests should use an isolated database (configured in tests/conftest.py).
