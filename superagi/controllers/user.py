from datetime import datetime
from typing import Optional

from fastapi_sqlalchemy import db
from fastapi import HTTPException, Depends, Request
from fastapi_jwt_auth import AuthJWT
from pydantic import BaseModel

from superagi.models.organisation import Organisation
from superagi.models.project import Project
from superagi.models.user import User
from fastapi import APIRouter

from superagi.helper.auth import check_auth, get_current_user
from superagi.lib.logger import logger

from superagi.models.models_config import ModelsConfig

# from superagi.types.db import UserBase, UserIn, UserOut

router = APIRouter()


class UserBase(BaseModel):
    name: str
    email: str
    password: str

    class Config:
        orm_mode = True


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    organisation_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class UserIn(UserBase):
    organisation_id: Optional[int]

    class Config:
        orm_mode = True


def _get_authorized_user(user_id: int, Authorize: AuthJWT):
    current_user = get_current_user(Authorize)
    if current_user is None:
        raise HTTPException(status_code=401, detail="Unauthenticated")
    if current_user.id != user_id:
        raise HTTPException(status_code=403, detail="Not authorized to access this user")
    return current_user


# CRUD Operations
@router.post("/add", response_model=UserOut, status_code=201)
def create_user(user: UserIn, Authorize: AuthJWT = Depends(check_auth)):
    """
    Create a new user.

    Args:
        user (UserIn): User data.

    Returns:
        User: The created user.

    Raises:
        HTTPException (status_code=400): If there is an issue creating the user.
        HTTPException (status_code=422): If required fields are missing or incorrectly formatted.
    """
    logger.info("Received user data: name=%s, email=%s", user.name, user.email)
    
    # Validate incoming request data
    if not user.name or not user.email or not user.password:
        logger.error("Missing required fields: name, email, or password")
        raise HTTPException(status_code=422, detail="Missing required fields: name, email, or password")
    
    db_user = db.session.query(User).filter(User.email == user.email).first()
    if db_user:
        current_user = get_current_user(Authorize)
        if current_user is not None and current_user.id == db_user.id:
            return db_user
        raise HTTPException(status_code=409, detail="User already exists")
    
    db_user = User(name=user.name, email=user.email, password=user.password)
    db.session.add(db_user)
    db.session.commit()
    db.session.flush()
    
    organisation = Organisation.find_or_create_organisation(db.session, db_user)
    Project.find_or_create_default_project(db.session, organisation.id)
    logger.info("User created: %s", db_user)
    
    # Adding local LLM configuration
    ModelsConfig.add_llm_config(db.session, organisation.id)
    
    return db_user


@router.get("/get/{user_id}", response_model=UserOut)
def get_user(user_id: int,
             Authorize: AuthJWT = Depends(check_auth)):
    """
    Get a particular user details.

    Args:
        user_id (int): ID of the user.

    Returns:
        User: The user details.

    Raises:
        HTTPException (status_code=403): If the user is not the authenticated user.

    """

    return _get_authorized_user(user_id, Authorize)


@router.put("/update/{user_id}", response_model=UserOut)
def update_user(user_id: int,
                user: UserBase,
                Authorize: AuthJWT = Depends(check_auth)):
    """
    Update a particular user.

    Args:
        user_id (int): ID of the user.
        user (UserIn): Updated user data.

    Returns:
        User: The updated user details.

    Raises:
        HTTPException (status_code=403): If the user is not the authenticated user.
        HTTPException (status_code=409): If the email is already used by another user.

    """

    db_user = _get_authorized_user(user_id, Authorize)

    if user.email != db_user.email:
        existing_user = db.session.query(User).filter(User.email == user.email).first()
        if existing_user is not None and existing_user.id != db_user.id:
            raise HTTPException(status_code=409, detail="Email already in use")

    db_user.name = user.name
    db_user.email = user.email
    db_user.password = user.password

    db.session.commit()
    return db_user


@router.post("/first_login_source/{source}")
def update_first_login_source(source: str, Authorize: AuthJWT = Depends(check_auth)):
    """ Update first login source of the user """
    user = get_current_user(Authorize)
    # valid_sources = ['google', 'github', 'email']
    if user.first_login_source is None or user.first_login_source == '':
        user.first_login_source = source
    db.session.commit()
    db.session.flush()
    logger.info("User : %s", user.id)
    return user
