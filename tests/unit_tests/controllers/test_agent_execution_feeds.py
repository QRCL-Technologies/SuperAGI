from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from superagi.controllers.agent_execution_feed import (
    get_agent_execution_feed,
    get_agent_execution_for_organisation,
    get_agent_execution_feed_for_organisation,
    get_execution_tasks,
)


def _scoped_query(mock_db):
    return mock_db.session.query.return_value.join.return_value.join.return_value.filter.return_value


@patch('superagi.controllers.agent_execution_feed.db')
def test_get_agent_execution_feed(mock_db):
    organisation = MagicMock(id=1)
    agent_execution = MagicMock(status="PAUSED", last_shown_error_id=None)
    _scoped_query(mock_db).first.return_value = agent_execution
    mock_db.session.query.return_value.filter_by.return_value.order_by.return_value.all.return_value = []

    response = get_agent_execution_feed(1, organisation=organisation)

    assert response["status"] == "PAUSED"
    assert response["feeds"] == []


@patch('superagi.controllers.agent_execution_feed.db')
def test_get_agent_execution_feed_other_organisation(mock_db):
    _scoped_query(mock_db).first.return_value = None

    with pytest.raises(HTTPException) as exc:
        get_agent_execution_feed(1, organisation=MagicMock(id=2))
    assert exc.value.status_code == 404


@patch('superagi.controllers.agent_execution_feed.TaskQueue')
@patch('superagi.controllers.agent_execution_feed.db')
def test_get_execution_tasks_other_organisation(mock_db, mock_task_queue):
    _scoped_query(mock_db).first.return_value = None

    with pytest.raises(HTTPException) as exc:
        get_execution_tasks(1, organisation=MagicMock(id=2))
    assert exc.value.status_code == 404
    mock_task_queue.assert_not_called()


@patch('superagi.controllers.agent_execution_feed.db')
def test_get_agent_execution_for_organisation_without_organisation(mock_db):
    with pytest.raises(HTTPException) as exc:
        get_agent_execution_for_organisation(1, None)
    assert exc.value.status_code == 404


@patch('superagi.controllers.agent_execution_feed.db')
def test_get_agent_execution_feed_for_organisation_other_organisation(mock_db):
    mock_db.session.query.return_value.filter.return_value.first.return_value = MagicMock(agent_execution_id=5)
    _scoped_query(mock_db).first.return_value = None

    with pytest.raises(HTTPException) as exc:
        get_agent_execution_feed_for_organisation(10, MagicMock(id=2))
    assert exc.value.status_code == 404
