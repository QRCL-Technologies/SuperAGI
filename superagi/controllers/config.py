from datetime import datetime
from typing import Optional

from fastapi import APIRouter
from pydantic import BaseModel

from superagi.models.models_config import ModelsConfig
from superagi.models.configuration import Configuration
from superagi.models.organisation import Organisation
from fastapi_sqlalchemy import db
from fastapi import HTTPException, Depends, Request
from superagi.config.config import get_config
from superagi.helper.auth import get_user_organisation
from superagi.helper.encyption_helper import encrypt_data
from superagi.lib.logger import logger
# from superagi.types.db import ConfigurationIn, ConfigurationOut

router = APIRouter()


class ConfigurationOut(BaseModel):
    id: int
    organisation_id: int
    key: str
    value: str
    created_at: datetime
    updated_at: datetime

    class Config:
        orm_mode = True


class ConfigurationIn(BaseModel):
    organisation_id: Optional[int]
    key: str
    value: str

    class Config:
        orm_mode = True


MASKED_SECRET = "********"


def _validate_organisation_access(organisation_id: int, organisation: Organisation):
    if organisation is None or organisation.id != organisation_id:
        raise HTTPException(status_code=403, detail="Unauthorized")


def _mask_secret(value):
    return MASKED_SECRET if value else value


def _config_to_out(config: Configuration) -> ConfigurationOut:
    config_out = ConfigurationOut.from_orm(config)
    if config_out.key == "model_api_key":
        config_out.value = _mask_secret(config_out.value)
    return config_out


# CRUD Operations
@router.post("/add/organisation/{organisation_id}", status_code=201,
             response_model=ConfigurationOut)
def create_config(config: ConfigurationIn, organisation_id: int,
                  organisation=Depends(get_user_organisation)):
    """
    Creates a new Organisation level config.

    Args:
        config (Configuration): Configuration details.
        organisation_id (int): ID of the organisation.
        organisation (Organisation): Organisation of the authenticated user.

    Returns:
        Configuration: Created configuration.

    """

    _validate_organisation_access(organisation_id, organisation)

    db_organisation = db.session.query(Organisation).filter(Organisation.id == organisation_id).first()
    if not db_organisation:
        raise HTTPException(status_code=404, detail="Organisation not found")

    existing_config = (
        db.session.query(Configuration)
        .filter(Configuration.organisation_id == organisation_id, Configuration.key == config.key)
        .first()
    )

    # Encrypt the API key
    if config.key == "model_api_key":
        encrypted_value = encrypt_data(config.value)
        config.value = encrypted_value

    if existing_config:
        existing_config.value = config.value
        db.session.commit()
        db.session.flush()
        return _config_to_out(existing_config)

    logger.info("NEW CONFIG")
    new_config = Configuration(organisation_id=organisation_id, key=config.key, value=config.value)
    logger.info(new_config)
    logger.info("ORGANISATION ID : ", organisation_id)
    db.session.add(new_config)
    db.session.commit()
    db.session.flush()
    return _config_to_out(new_config)


@router.get("/get/organisation/{organisation_id}/key/{key}", status_code=200)
def get_config_by_organisation_id_and_key(organisation_id: int, key: str,
                                          organisation=Depends(get_user_organisation)):
    """
    Get a configuration by organisation ID and key.

    Args:
        organisation_id (int): ID of the organisation.
        key (str): Key of the configuration.
        organisation (Organisation): Organisation of the authenticated user.

    Returns:
        Configuration: Retrieved configuration.

    """

    _validate_organisation_access(organisation_id, organisation)

    db_organisation = db.session.query(Organisation).filter(Organisation.id == organisation_id).first()
    if not db_organisation:
        raise HTTPException(status_code=404, detail="Organisation not found")

    config = db.session.query(ModelsConfig).filter(ModelsConfig.org_id == organisation_id, ModelsConfig.provider == 'OpenAI').first()
    if config is None:
        api_key = get_config("OPENAI_API_KEY") or get_config("PALM_API_KEY")
        if (api_key is not None and api_key != "YOUR_OPEN_API_KEY") or (
                api_key is not None and api_key != "YOUR_PALM_API_KEY"):
            encrypted_data = encrypt_data(api_key)
            new_config = Configuration(organisation_id=organisation_id, key="model_api_key",value=encrypted_data)
            db.session.add(new_config)
            db.session.commit()
            db.session.flush()
            return _config_to_out(new_config)
    if config is None:
        return None
    return {
        "id": config.id,
        "provider": config.provider,
        "org_id": config.org_id,
        "api_key": _mask_secret(config.api_key),
    }



@router.get("/get/organisation/{organisation_id}", status_code=201)
def get_config_by_organisation_id(organisation_id: int,
                                  organisation=Depends(get_user_organisation)):
    """
    Get all configurations for a given organisation ID.

    Args:
        organisation_id (int): ID of the organisation.
        organisation (Organisation): Organisation of the authenticated user.

    Returns:
        List[Configuration]: List of configurations for the organisation.

    """

    _validate_organisation_access(organisation_id, organisation)

    db_organisation = db.session.query(Organisation).filter(Organisation.id == organisation_id).first()
    if not db_organisation:
        raise HTTPException(status_code=404, detail="Organisation not found")

    configs = db.session.query(Configuration).filter(Configuration.organisation_id == organisation_id).all()

    return [_config_to_out(config) for config in configs]


@router.get("/get/env", status_code=200)
def current_env():
    """
    Get the current environment.

    Returns:
        dict: Dictionary containing the current environment.

    """

    env = get_config("ENV", "DEV")
    return {
        "env": env
    }
