from typing import Optional

from fastapi_sqlalchemy import db
from fastapi import HTTPException, Depends
from pydantic import BaseModel

from superagi.models.project import Project
from superagi.models.organisation import Organisation
from fastapi import APIRouter
from superagi.helper.auth import get_user_organisation
# from superagi.types.db import ProjectIn, ProjectOut

router = APIRouter()


class ProjectOut(BaseModel):
    id: int
    name: str
    organisation_id: int
    description: str

    class Config:
        orm_mode = True


class ProjectIn(BaseModel):
    name: str
    organisation_id: Optional[int] = None
    description: str

    class Config:
        orm_mode = True

def _get_organisation_project(project_id: int, organisation: Organisation):
    if not organisation:
        return None
    return db.session.query(Project).filter(Project.id == project_id,
                                            Project.organisation_id == organisation.id).first()


# CRUD Operations
@router.post("/add", response_model=ProjectOut, status_code=201)
def create_project(project: ProjectIn,
                   organisation: Organisation = Depends(get_user_organisation)):
    """
    Create a new project.

    Args:
        project (Project): Project data.

    Returns:
        dict: Dictionary containing the created project.

    Raises:
        HTTPException (status_code=404): If the organization with the specified ID is not found.

    """

    if not organisation:
        raise HTTPException(status_code=404, detail="Organisation not found")

    project = Project(
        name=project.name,
        organisation_id=organisation.id,
        description=project.description
    )

    db.session.add(project)
    db.session.commit()

    return project


@router.get("/get/{project_id}", response_model=ProjectOut)
def get_project(project_id: int, organisation: Organisation = Depends(get_user_organisation)):
    """
    Get project details by project_id.

    Args:
        project_id (int): ID of the project.

    Returns:
        dict: Dictionary containing the project details.

    Raises:
        HTTPException (status_code=404): If the project with the specified ID is not found.

    """

    db_project = _get_organisation_project(project_id, organisation)
    if not db_project:
        raise HTTPException(status_code=404, detail="project not found")
    return db_project


@router.put("/update/{project_id}", response_model=ProjectOut)
def update_project(project_id: int, project: ProjectIn,
                   organisation: Organisation = Depends(get_user_organisation)):
    """
    Update a project detail by project_id.

    Args:
        project_id (int): ID of the project.
        project (Project): Updated project data.

    Returns:
        dict: Dictionary containing the updated project details.

    Raises:
        HTTPException (status_code=404): If the project with the specified ID is not found.
        HTTPException (status_code=404): If the organization with the specified ID is not found.

    """

    db_project = _get_organisation_project(project_id, organisation)
    if not db_project:
        raise HTTPException(status_code=404, detail="Project not found")

    db_project.name = project.name
    db_project.description = project.description
    db.session.add(db_project)
    db.session.commit()
    return db_project


@router.get("/get/organisation/{organisation_id}")
def get_projects_organisation(organisation_id: int,
                              organisation: Organisation = Depends(get_user_organisation)):
    """
    Get all projects by organisation_id and create default if no project.

    Args:
        organisation_id (int): ID of the organisation.

    Returns:
        List[Project]: List of projects belonging to the organisation.

    Raises:
        HTTPException (status_code=404): If the organization with the specified ID is not found.

    """

    if not organisation or organisation.id != organisation_id:
        raise HTTPException(status_code=404, detail="Organisation not found")

    Project.find_or_create_default_project(db.session, organisation_id)
    projects = db.session.query(Project).filter(Project.organisation_id == organisation_id).all()
    if len(projects) <= 0:
        default_project = Project.find_or_create_default_project(db.session, organisation_id)
        projects.append(default_project)

    return projects
