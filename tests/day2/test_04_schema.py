"""
Day 2 - Lesson 4: JSON Schema validation of real API responses.

A schema file (schemas/*.schema.json) describes the SHAPE of a JSON body.
The words you need:

- "type": "object"  - the whole body must be a JSON object, i.e. {...}.
- "properties"      - lists each field we know about and what it must be.
- "type": "string"  - that field must be text. A number like 1 fails.
- "required"        - fields that MUST be present. A body missing one fails,
                      even if every field it does have is correct.

(Extra: "enum" limits a string to listed values, and
"additionalProperties": false rejects unexpected extra fields.)

Every test checks the HTTP status first (inside assert_matches_schema),
then applies the matching schema. Run with --day2-fault=missing-status or
--day2-fault=wrong-status-type to see the schema catch a broken response.
"""


def test_employee_profile_matches_schema(client, auth_headers, assert_matches_schema):
    # Arrange: EMP001 exists in data/employees.json

    # Act
    response = client.get("/employees/me", headers=auth_headers("EMP001"))

    # Assert: 200, then the employee schema
    assert_matches_schema(response, 200, "employee")


def test_ticket_matches_schema(client, auth_headers, assert_matches_schema):
    # Arrange: EMP001 owns TCK-1001 in data/tickets.json

    # Act
    response = client.get("/tickets/TCK-1001", headers=auth_headers("EMP001"))

    # Assert: 200, then the ticket schema (requires string "status")
    assert_matches_schema(response, 200, "ticket")


def test_service_status_matches_schema(client, assert_matches_schema):
    # Arrange: no identity needed for this endpoint

    # Act
    response = client.get("/services/vpn/status")

    # Assert: 200, then the service status schema (requires string "status")
    assert_matches_schema(response, 200, "service_status")


def test_error_response_matches_schema(client, auth_headers, assert_matches_schema):
    # Arrange: TCK-9999 does not exist

    # Act
    response = client.get("/tickets/TCK-9999", headers=auth_headers("EMP001"))

    # Assert: 404, then the error schema (exactly one string field, "detail")
    assert_matches_schema(response, 404, "error")
