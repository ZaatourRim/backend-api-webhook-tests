import pytest
from jsonschema import validate

from utils.json_schemas import *

def test_get_single_user_success(api_client):
    response = api_client.get("/api/users/2")

    assert response.status_code == 200, (
        f"Unexpected status code: {response.status_code}, "
        f"body: {response.text}"
    )

    body = response.json()
    user = body["data"]
    # validate schema
    validate(instance=body, schema=USER_SCHEMA)

    '''assert "data" in body
    assert "email" in user
    assert "first_name" in user
    assert "last_name" in user'''

    # focused checks beyond the schema
    assert user["id"] == 2
    assert user["email"].endswith("@reqres.in")
    
def test_create_user_success(api_client):
    """
    Positive POST test:
    - Calls POST /api/users with a simple JSON body
    - Asserts HTTP 201
    - Asserts the response contains the sent fields and an id
    """
    payload = {
        "name": "Rim",
        "job": "Senior QA Automation Engineer"
    }

    response = api_client.post("/api/users", json=payload)
    assert response.status_code == 201, (
        f"Unexpected status: {response.status_code}, "
        f"body: {response.text}"
    )
    body = response.json()
    # validate schema
    validate(instance=body, schema=CREATED_USER_SCHEMA)
    # More focused checks: values echoed correctly
    assert body.get("name") == payload["name"]
    assert body.get("job") == payload["job"]

def test_delete_user_returns_204(api_client):
    """
    DELETE test:
    - Calls DELETE /api/users/2
    - Asserts HTTP 204 (no content)
    """
    response = api_client.delete("/api/users/2")

    assert response.status_code == 204, (
        f"Unexpected status code: {response.status_code}, "
        f"body: {response.text}"
    )
    # Optional: some APIs return an empty body for 204
    assert response.text == "" or response.text is not None

@pytest.mark.parametrize("user_id", [234, 9999, 12345])
def test_get_nonexistent_user_returns_404(api_client, user_id: int):
    """
    Negative test:
    - Calls GET /api/users/{id} (nonexistent user id in Reqres)
    - Asserts HTTP 404 and empty body
    """
    response = api_client.get(f"/api/users/{user_id}")

    assert response.status_code == 404, (
        f"Unexpected status code: {response.status_code}, "
        f"body: {response.text}"
    )
    # Reqres returns an empty JSON object for this case
    assert response.text in ("{}", "")

@pytest.mark.parametrize("payload, expected_error_substring", [
    ({"email": "user@domain"}, "missing password"),
    ({"password": "secret"}, "missing email"),
    ({}, "missing")
])
def test_login_missing_password_returns_400(api_client, payload:dict, expected_error_substring: str):
    """
    Negative test on POST with invalid payload:
    - Calls POST /api/login without 'password'
    - Expects HTTP 400 and an error message in the body
    """

    response = api_client.post("/api/login", json=payload)

    # status code check
    assert response.status_code == 400, (
        f"Unexpected status code: {response.status_code}, "
        f"body: {response.text}"
    )

    body = response.json()
    # Validate error message schema
    validate(instance=body, schema=ERROR_SCHEMA)
    assert expected_error_substring in body["error"].lower()