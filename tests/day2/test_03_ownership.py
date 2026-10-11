"""
Day 2 - Lesson 3: cross-employee access, both directions.

Where ownership is enforced: get_ticket() in app/main.py asks
rules.employee_owns_ticket() whether the ticket's employee_id equals the
caller's. If not, the API answers 403 and stops before returning the ticket.

What a failure looks like: if that check is broken (try it with
--day2-fault=ownership), the API returns 200 and hands over someone
else's ticket, and these tests fail on the status code.

Owners come from data/tickets.json: TCK-1001 -> EMP001, TCK-1002 -> EMP002.
"""

import pytest

FORBIDDEN_DETAIL = "You may not view another employee's ticket."

CROSS_ACCESS = [
    pytest.param("EMP001", "TCK-1002", id="emp001_requests_emp002_ticket"),
    pytest.param("EMP002", "TCK-1001", id="emp002_requests_emp001_ticket"),
]


@pytest.mark.parametrize("employee_id, ticket_id", CROSS_ACCESS)
def test_cross_employee_access_is_denied(client, auth_headers, employee_id, ticket_id):
    # Arrange: caller does not own the requested ticket (see data/tickets.json)

    # Act
    response = client.get(f"/tickets/{ticket_id}", headers=auth_headers(employee_id))

    # Assert: documented denial, and nothing about the ticket leaks
    assert response.status_code == 403
    assert response.json() == {"detail": FORBIDDEN_DETAIL}
    for protected_field in ("subject", "description", "status", "ticket_id"):
        assert protected_field not in response.text
