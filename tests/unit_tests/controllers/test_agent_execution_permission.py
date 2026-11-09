from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from superagi.controllers.agent_execution_permission import (
    get_agent_execution_permission,
    update_agent_execution_permission,
    update_agent_execution_permission_status,
    AgentExecutionPermissionIn,
)
from superagi.models.agent import Agent
from superagi.models.agent_execution import AgentExecution
from superagi.models.agent_execution_permission import AgentExecutionPermission
from superagi.models.project import Project


def _setup_db(mock_db, project_org_id):
    permission = MagicMock(id=1, agent_execution_id=10, agent_id=20)
    execution = MagicMock(id=10, agent_id=20)
    agent = MagicMock(id=20, project_id=30)
    project = MagicMock(id=30, organisation_id=project_org_id)
    results = {AgentExecution: execution, Agent: agent, Project: project}

    def query(model):
        q = MagicMock()
        q.get.return_value = permission if model is AgentExecutionPermission else None
        q.filter.return_value.first.return_value = results.get(model)
        return q

    mock_db.session.query.side_effect = query
    return permission


@patch('superagi.controllers.agent_execution_permission.execute_agent')
@patch('superagi.controllers.agent_execution_permission.db')
def test_update_status_rejects_other_organisation(mock_db, mock_execute_agent):
    permission = _setup_db(mock_db, project_org_id=2)
    permission.status = "PENDING"
    with pytest.raises(HTTPException) as exc:
        update_agent_execution_permission_status(1, status=True, user_feedback="",
                                                 Authorize=MagicMock(), organisation=MagicMock(id=1))
    assert exc.value.status_code == 404
    assert permission.status == "PENDING"
    mock_execute_agent.delay.assert_not_called()
    mock_db.session.commit.assert_not_called()


@patch('superagi.controllers.agent_execution_permission.execute_agent')
@patch('superagi.controllers.agent_execution_permission.db')
def test_update_status_allows_own_organisation(mock_db, mock_execute_agent):
    permission = _setup_db(mock_db, project_org_id=1)
    result = update_agent_execution_permission_status(1, status=True, user_feedback="",
                                                      Authorize=MagicMock(), organisation=MagicMock(id=1))
    assert result == {"success": True}
    assert permission.status == "APPROVED"
    mock_execute_agent.delay.assert_called_once()


@patch('superagi.controllers.agent_execution_permission.db')
def test_get_rejects_other_organisation(mock_db):
    _setup_db(mock_db, project_org_id=2)
    with pytest.raises(HTTPException) as exc:
        get_agent_execution_permission(1, Authorize=MagicMock(), organisation=MagicMock(id=1))
    assert exc.value.status_code == 404


@patch('superagi.controllers.agent_execution_permission.db')
def test_patch_rejects_other_organisation(mock_db):
    _setup_db(mock_db, project_org_id=2)
    body = AgentExecutionPermissionIn(agent_execution_id=10, agent_id=20, status="APPROVED",
                                      tool_name="t", user_feedback="", assistant_reply="")
    with pytest.raises(HTTPException) as exc:
        update_agent_execution_permission(1, body, Authorize=MagicMock(), organisation=MagicMock(id=1))
    assert exc.value.status_code == 404
    mock_db.session.commit.assert_not_called()
