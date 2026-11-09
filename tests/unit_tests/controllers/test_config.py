from datetime import datetime
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from superagi.controllers.config import MASKED_SECRET, _config_to_out, _validate_organisation_access
from superagi.models.configuration import Configuration


def test_validate_organisation_access_rejects_other_organisation():
    organisation = MagicMock(id=1)
    with pytest.raises(HTTPException) as exc_info:
        _validate_organisation_access(2, organisation)
    assert exc_info.value.status_code == 403


def test_validate_organisation_access_rejects_missing_organisation():
    with pytest.raises(HTTPException) as exc_info:
        _validate_organisation_access(1, None)
    assert exc_info.value.status_code == 403


def test_validate_organisation_access_allows_own_organisation():
    _validate_organisation_access(1, MagicMock(id=1))


def test_config_to_out_masks_model_api_key():
    config = Configuration(id=1, organisation_id=1, key="model_api_key", value="encrypted",
                           created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    assert _config_to_out(config).value == MASKED_SECRET


def test_config_to_out_keeps_other_values():
    config = Configuration(id=1, organisation_id=1, key="model_source", value="OpenAi",
                           created_at=datetime.utcnow(), updated_at=datetime.utcnow())
    assert _config_to_out(config).value == "OpenAi"
