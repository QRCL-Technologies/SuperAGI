from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from superagi.controllers import vector_dbs as vector_dbs_controller


def _vector_db(organisation_id=1):
    vector_db = MagicMock()
    vector_db.id = 10
    vector_db.name = "db"
    vector_db.db_type = "Pinecone"
    vector_db.organisation_id = organisation_id
    return vector_db


def _organisation(organisation_id=1):
    organisation = MagicMock()
    organisation.id = organisation_id
    return organisation


@patch("superagi.controllers.vector_dbs.db")
@patch("superagi.controllers.vector_dbs.VectordbConfigs.get_vector_db_config_from_db_id")
@patch("superagi.controllers.vector_dbs.Vectordbs.get_vector_db_from_id")
def test_get_vector_db_details_masks_api_key(mock_get_db, mock_get_config, mock_db):
    mock_get_db.return_value = _vector_db()
    mock_get_config.return_value = {"api_key": "secret-api-key-1234", "environment": "us-east"}
    mock_db.session.query.return_value.filter.return_value.all.return_value = []

    response = vector_dbs_controller.get_vector_db_details(10, organisation=_organisation())

    assert response["api_key"] != "secret-api-key-1234"
    assert "secret-api-key" not in response["api_key"]
    assert response["environment"] == "us-east"


@pytest.mark.parametrize("vector_db", [None, _vector_db(organisation_id=2)])
@pytest.mark.parametrize("handler,args", [
    (vector_dbs_controller.get_vector_db_details, (10,)),
    (vector_dbs_controller.delete_vector_db, (10,)),
    (vector_dbs_controller.update_vector_db, (["index"], 10)),
])
@patch("superagi.controllers.vector_dbs.VectordbConfigs")
@patch("superagi.controllers.vector_dbs.VectordbIndices")
@patch("superagi.controllers.vector_dbs.db")
@patch("superagi.controllers.vector_dbs.Vectordbs")
def test_vector_db_routes_reject_other_organisation(mock_vectordbs, mock_db, mock_indices, mock_configs,
                                                    handler, args, vector_db):
    mock_vectordbs.get_vector_db_from_id.return_value = vector_db

    with pytest.raises(HTTPException) as exc:
        handler(*args, organisation=_organisation(organisation_id=1))

    assert exc.value.status_code == 404
    mock_vectordbs.delete_vector_db.assert_not_called()
    mock_configs.get_vector_db_config_from_db_id.assert_not_called()
    mock_indices.delete_vector_db_index.assert_not_called()
