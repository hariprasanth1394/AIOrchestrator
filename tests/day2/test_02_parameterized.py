"""
Day 2 - Lesson 2: @pytest.mark.parametrize.

How the syntax works:

    @pytest.mark.parametrize("a, b", [row1, row2, ...])

- The first argument is a string of parameter names, separated by commas.
- The second argument is a list of rows. Each row supplies one value per
  name, in the same order.
- pytest runs the test function once per row, passing the row's values in
  as the named arguments. Five rows = five separate test results.
- pytest.param(..., id="...") wraps a row and gives it a readable name,
  so the output reads "...[employee_a_own_ticket]" instead of "[EMP001-...]".

Employees and owners come from data/tickets.json:
    Employee A = EMP001 (Dana Whitfield), owns TCK-1001
    Employee B = EMP002 (Marcus Lee),     owns TCK-1002
Expected values are written out here, never read from the response.
"""

import pytest

EMPLOYEE_A = "EMP001"
EMPLOYEE_B = "EMP002"
TICKET_OF_A = "TCK-1001"
TICKET_OF_B = "TCK-1002"
MISSING_TICKET = "TCK-9999"  # well-formed id, not in data/tickets.json

FORBIDDEN_DETAIL = "You may not view another employee's ticket."

TICKET_CASES = [
    pytest.param(
        EMPLOYEE_A, TICKET_OF_A, 200,
        {"ticket_id": TICKET_OF_A, "employee_id": EMPLOYEE_A},
        id="employee_a_own_ticket",
    ),
    pytest.param(
        EMPLOYEE_B, TICKET_OF_B, 200,
        {"ticket_id": TICKET_OF_B, "employee_id": EMPLOYEE_B},
        id="employee_b_own_ticket",
    ),
    pytest.param(
        EMPLOYEE_A, TICKET_OF_B, 403,
        {"detail": FORBIDDEN_DETAIL},
        id="employee_a_denied_employee_b_ticket",
    ),
    pytest.param(
        EMPLOYEE_B, TICKET_OF_A, 403,
        {"detail": FORBIDDEN_DETAIL},
        id="employee_b_denied_employee_a_ticket",
    ),
    pytest.param(
        EMPLOYEE_A, MISSING_TICKET, 404,
        {"detail": f"Ticket not found: {MISSING_TICKET}"},
        id="valid_employee_missing_ticket",
    ),
]


@pytest.mark.parametrize("employee_id, ticket_id, expected_status, expected_fields", TICKET_CASES)
def test_ticket_access(client, auth_headers, employee_id, ticket_id, expected_status, expected_fields):
    # Arrange: the row gives the caller, the ticket, and what we expect back

    # Act
    response = client.get(f"/tickets/{ticket_id}", headers=auth_headers(employee_id))

    # Assert: exact status, no alternatives accepted
    assert response.status_code == expected_status
    body = response.json()
    for field, expected_value in expected_fields.items():
        assert body[field] == expected_value

    if expected_status != 200:
        # Error responses must be exactly {"detail": ...}: no ticket data leaks
        assert body == expected_fields
