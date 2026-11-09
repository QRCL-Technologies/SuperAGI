from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from main import app
from superagi.helper.auth import get_user_organisation

client = TestClient(app)


@pytest.fixture
def organisation():
    org = MagicMock()
    org.id = 1
    org.name = "Acme"
    app.dependency_overrides[get_user_organisation] = lambda: org
    yield org
    app.dependency_overrides.pop(get_user_organisation, None)


@patch('superagi.controllers.knowledges.db')
@patch('superagi.controllers.knowledges.Knowledges.get_organisation_knowledge_from_id', return_value=None)
def test_get_user_knowledge_details_other_organisation(mock_get_knowledge, mock_db, organisation):
    response = client.get("/knowledges/user/get/details/5")
    assert response.status_code == 404
    mock_get_knowledge.assert_called_once_with(mock_db.session, 5, organisation.id)


@patch('superagi.controllers.knowledges.db')
@patch('superagi.controllers.knowledges.Knowledges.delete_knowledge', return_value=0)
def test_delete_user_knowledge_other_organisation(mock_delete_knowledge, mock_db, organisation):
    response = client.post("/knowledges/delete/5")
    assert response.status_code == 404
    mock_delete_knowledge.assert_called_once_with(mock_db.session, 5, organisation.id)


@patch('superagi.controllers.knowledges.db')
@patch('superagi.controllers.knowledges.Knowledges.delete_knowledge', return_value=1)
def test_delete_user_knowledge_own_organisation(mock_delete_knowledge, mock_db, organisation):
    response = client.post("/knowledges/delete/5")
    assert response.status_code == 200
    mock_delete_knowledge.assert_called_once_with(mock_db.session, 5, organisation.id)
