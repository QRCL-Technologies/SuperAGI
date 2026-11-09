from unittest.mock import patch, MagicMock

import pytest
from fastapi import HTTPException

from superagi.controllers.project import (ProjectIn, create_project, get_project, get_projects_organisation,
                                          update_project)
from superagi.models.project import Project


@patch('superagi.controllers.project.db')
def test_update_project_of_other_organisation_returns_404(mock_db):
    mock_db.session.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        update_project(5, ProjectIn(name="x", organisation_id=1, description="d"), organisation=MagicMock(id=1))
    assert exc.value.status_code == 404
    mock_db.session.commit.assert_not_called()


@patch('superagi.controllers.project.db')
def test_update_project_ignores_client_organisation_id(mock_db):
    db_project = Project(id=5, name="old", organisation_id=1, description="old")
    mock_db.session.query.return_value.filter.return_value.first.return_value = db_project
    result = update_project(5, ProjectIn(name="new", organisation_id=2, description="new"),
                            organisation=MagicMock(id=1))
    assert result.organisation_id == 1
    assert result.name == "new"


@patch('superagi.controllers.project.db')
def test_get_project_of_other_organisation_returns_404(mock_db):
    mock_db.session.query.return_value.filter.return_value.first.return_value = None
    with pytest.raises(HTTPException) as exc:
        get_project(5, organisation=MagicMock(id=1))
    assert exc.value.status_code == 404


@patch('superagi.controllers.project.db')
def test_create_project_uses_caller_organisation(mock_db):
    result = create_project(ProjectIn(name="p", organisation_id=2, description="d"), organisation=MagicMock(id=1))
    assert result.organisation_id == 1


@patch('superagi.controllers.project.db')
def test_get_projects_of_other_organisation_returns_404(mock_db):
    with pytest.raises(HTTPException) as exc:
        get_projects_organisation(2, organisation=MagicMock(id=1))
    assert exc.value.status_code == 404
