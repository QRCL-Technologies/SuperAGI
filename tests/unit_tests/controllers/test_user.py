from datetime import datetime
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from main import app
from superagi.models.user import User

client = TestClient(app)

# Define a fixture for an authenticated user
@pytest.fixture
def authenticated_user():
    # Create a mock user object with necessary attributes
    user = User()

    # Set user attributes
    user.id = 1  # User ID
    user.username = "testuser"  # User's username
    user.email = "super6@agi.com"  # User's email
    user.first_login_source = None  # User's first login source
    user.token = "mock-jwt-token"

    return user

# Test case for updating first login source when it's not set
def test_update_first_login_source(authenticated_user):
    with patch('superagi.helper.auth.db') as mock_auth_db:
        source = "github"  # Specify the source you want to set

        mock_auth_db.session.query.return_value.filter.return_value.first.return_value = authenticated_user
        response = client.post(f"users/first_login_source/{source}", headers={"Authorization": f"Bearer {authenticated_user.token}"})

        # Verify the HTTP response
        assert response.status_code == 200
        assert "first_login_source" in response.json()  # Check if the "first_login_source" field is in the response
        assert response.json()["first_login_source"] == "github"  # Check if the "source" field equals "github"

def _make_user(user_id, email):
    user = User()
    user.id = user_id
    user.name = "user" + str(user_id)
    user.email = email
    user.password = "secret-password"
    user.organisation_id = user_id
    user.created_at = datetime.now()
    user.updated_at = datetime.now()
    return user


def test_get_other_user_forbidden():
    current = _make_user(1, "super6@agi.com")
    with patch('superagi.controllers.user.get_current_user', return_value=current):
        response = client.get("users/get/2")
        assert response.status_code == 403


def test_get_self_does_not_return_password():
    current = _make_user(1, "super6@agi.com")
    with patch('superagi.controllers.user.get_current_user', return_value=current):
        response = client.get("users/get/1")
        assert response.status_code == 200
        assert response.json()["id"] == 1
        assert "password" not in response.json()


def test_update_other_user_forbidden():
    current = _make_user(1, "super6@agi.com")
    with patch('superagi.controllers.user.get_current_user', return_value=current), \
            patch('superagi.controllers.user.db') as mock_db:
        response = client.put("users/update/2",
                              json={"name": "x", "email": "attacker@x.com", "password": "pwned"})
        assert response.status_code == 403
        mock_db.session.commit.assert_not_called()
        assert current.password == "secret-password"


def test_update_self_does_not_return_password():
    current = _make_user(1, "super6@agi.com")
    with patch('superagi.controllers.user.get_current_user', return_value=current), \
            patch('superagi.controllers.user.db') as mock_db:
        mock_db.session.query.return_value.filter.return_value.first.return_value = None
        response = client.put("users/update/1",
                              json={"name": "new", "email": "new@agi.com", "password": "newpass"})
        assert response.status_code == 200
        assert response.json()["email"] == "new@agi.com"
        assert "password" not in response.json()


def test_add_existing_other_user_conflict():
    current = _make_user(1, "super6@agi.com")
    victim = _make_user(2, "victim@agi.com")
    with patch('superagi.controllers.user.get_current_user', return_value=current), \
            patch('superagi.controllers.user.db') as mock_db:
        mock_db.session.query.return_value.filter.return_value.first.return_value = victim
        response = client.post("users/add",
                               json={"name": "x", "email": "victim@agi.com", "password": "x"})
        assert response.status_code == 409
        assert "secret-password" not in response.text


def test_add_existing_self_does_not_return_password():
    current = _make_user(1, "super6@agi.com")
    with patch('superagi.controllers.user.get_current_user', return_value=current), \
            patch('superagi.controllers.user.db') as mock_db:
        mock_db.session.query.return_value.filter.return_value.first.return_value = current
        response = client.post("users/add",
                               json={"name": "x", "email": "super6@agi.com", "password": "x"})
        assert response.status_code == 201
        assert response.json()["id"] == 1
        assert "password" not in response.json()
