"""
Day 2 - Lesson 1: fixtures.

Both tests ask pytest for two fixtures by naming them as parameters:
- client        (tests/conftest.py)       - talks to the app in-process
- auth_headers  (tests/day2/conftest.py)  - builds the identity header

Expected owners are written out from data/tickets.json, never read from
the response we are testing.
"""


def test_employee_a_retrieves_own_ticket(client, auth_headers):
    # Arrange: EMP001 (Dana Whitfield) owns TCK-1001 in data/tickets.json
    employee_id = "EMP001"
    ticket_id = "TCK-1001"

    # Act
    response = client.get(f"/tickets/{ticket_id}", headers=auth_headers(employee_id))

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["ticket_id"] == ticket_id
    assert body["employee_id"] == employee_id


def test_employee_b_retrieves_own_ticket(client, auth_headers):
    # Arrange: EMP002 (Marcus Lee) owns TCK-1002 in data/tickets.json
    employee_id = "EMP002"
    ticket_id = "TCK-1002"

    # Act
    response = client.get(f"/tickets/{ticket_id}", headers=auth_headers(employee_id))

    # Assert
    assert response.status_code == 200
    body = response.json()
    assert body["ticket_id"] == ticket_id
    assert body["employee_id"] == employee_id
