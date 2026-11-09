from unittest.mock import patch
from unittest import mock
import pytest
from fastapi.testclient import TestClient

from main import app
from superagi.models.agent_schedule import AgentSchedule
from datetime import datetime

client = TestClient(app)

@pytest.fixture
def mock_patch_schedule_input():
    return {
        "agent_id": 1,
        "start_time": "2023-02-02 01:00:00",
        "recurrence_interval": "2 Hours",
        "expiry_date": "2023-12-30 01:00:00",
        "expiry_runs": -1
    }

@pytest.fixture
def mock_schedule():
    # Mock schedule data for testing
    return AgentSchedule(id=1, agent_id=1, status="SCHEDULED")

# An agent is already scheduled and is simply being updated, we assert for the updated values here
def test_schedule_existing_agent_already_scheduled(mock_patch_schedule_input, mock_schedule):
    with patch('superagi.controllers.agent_execution.db') as mock_db,             patch('superagi.helper.auth.db'):
        mock_db.session.query.return_value.filter.return_value.first.return_value = mock_schedule 

        response = client.post("agentexecutions/schedule", json=mock_patch_schedule_input)

        assert response.status_code == 201
        assert mock_schedule.start_time == datetime.strptime(mock_patch_schedule_input['start_time'], '%Y-%m-%d %H:%M:%S')
        assert mock_schedule.recurrence_interval == mock_patch_schedule_input['recurrence_interval']
        assert mock_schedule.expiry_date == datetime.strptime(mock_patch_schedule_input['expiry_date'], '%Y-%m-%d %H:%M:%S')
        assert mock_schedule.expiry_runs == mock_patch_schedule_input['expiry_runs']

# The agent isn't scheduled yet and we are scheduling it, we simply assert for a 201 status code and non-null schedule id.
def test_schedule_existing_agent_new_schedule(mock_patch_schedule_input, mock_schedule):
    with patch('superagi.controllers.agent_execution.db') as mock_db,             patch('superagi.helper.auth.db'):
        mock_db.session.query.return_value.filter.return_value.first.return_value = mock_schedule

        response = client.post("agentexecutions/schedule", json=mock_patch_schedule_input)

        assert response.status_code == 201
        assert response.json()["schedule_id"] is not None


@pytest.fixture
def mock_agent_run_input():
    return {
        "agent_id": 1,
        "name": "run",
        "goal": ["goal"],
        "instruction": [],
        "agent_workflow": "Goal Based Workflow",
        "constraints": [],
        "toolkits": [],
        "tools": [],
        "exit": "No exit criterion",
        "iteration_interval": 500,
        "model": "gpt-4",
        "permission_type": "God Mode",
        "LTM_DB": "Pinecone",
        "max_iterations": 25,
        "user_timezone": None,
        "knowledge": None
    }


def _no_org_agent(mock_db):
    query = mock_db.session.query.return_value.join.return_value
    query.filter.return_value.first.return_value = None
    query.filter.return_value.filter.return_value.first.return_value = None
    query.join.return_value.filter.return_value.first.return_value = None


def test_add_run_rejects_agent_from_other_organisation(mock_agent_run_input):
    with patch('superagi.controllers.agent_execution.db') as mock_db,             patch('superagi.helper.auth.db'),             patch('superagi.controllers.agent_execution.AgentConfiguration') as mock_agent_config,             patch('superagi.controllers.agent_execution.execute_agent') as mock_execute_agent:
        _no_org_agent(mock_db)

        response = client.post("agentexecutions/add_run", json=mock_agent_run_input)

        assert response.status_code == 404
        mock_agent_config.update_agent_configurations_table.assert_not_called()
        mock_execute_agent.delay.assert_not_called()


def test_add_rejects_agent_from_other_organisation():
    with patch('superagi.controllers.agent_execution.db') as mock_db,             patch('superagi.helper.auth.db'),             patch('superagi.controllers.agent_execution.execute_agent') as mock_execute_agent:
        _no_org_agent(mock_db)

        response = client.post("agentexecutions/add", json={"agent_id": 1, "name": "run", "goal": [], "instruction": []})

        assert response.status_code == 404
        mock_execute_agent.delay.assert_not_called()


def test_schedule_rejects_agent_from_other_organisation(mock_patch_schedule_input):
    with patch('superagi.controllers.agent_execution.db') as mock_db,             patch('superagi.helper.auth.db'):
        _no_org_agent(mock_db)

        response = client.post("agentexecutions/schedule", json=mock_patch_schedule_input)

        assert response.status_code == 404
        mock_db.session.add.assert_not_called()


def test_get_execution_from_other_organisation_returns_404():
    with patch('superagi.controllers.agent_execution.db') as mock_db,             patch('superagi.helper.auth.db'):
        _no_org_agent(mock_db)

        response = client.get("agentexecutions/get/1")

        assert response.status_code == 404


def test_update_execution_from_other_organisation_returns_404():
    with patch('superagi.controllers.agent_execution.db') as mock_db,             patch('superagi.helper.auth.db'),             patch('superagi.controllers.agent_execution.execute_agent') as mock_execute_agent:
        _no_org_agent(mock_db)

        response = client.put("agentexecutions/update/1", json={"status": "RUNNING"})

        assert response.status_code == 404
        mock_db.session.commit.assert_not_called()
        mock_execute_agent.delay.assert_not_called()


def test_list_runs_of_agent_from_other_organisation_returns_404():
    with patch('superagi.controllers.agent_execution.db') as mock_db,             patch('superagi.helper.auth.db'):
        _no_org_agent(mock_db)

        response = client.get("agentexecutions/get/agent/1")

        assert response.status_code == 404


def test_latest_agent_of_project_from_other_organisation_returns_404():
    with patch('superagi.controllers.agent_execution.db'),             patch('superagi.helper.auth.db') as mock_auth_db,             patch('superagi.controllers.agent_execution.Project') as mock_project:
        mock_auth_db.session.query.return_value.filter.return_value.first.return_value.id = 1
        mock_project.find_by_id.return_value.organisation_id = 2

        response = client.get("agentexecutions/get/latest/agent/project/1")

        assert response.status_code == 404
