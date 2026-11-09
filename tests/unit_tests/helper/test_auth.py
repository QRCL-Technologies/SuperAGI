from unittest.mock import MagicMock, patch

import pytest

from superagi.helper.auth import check_auth, get_current_user, is_dev_env


@pytest.mark.parametrize("env, expected", [(None, False), ("PROD", False), ("DEV", True), ("anything", False)])
def test_is_dev_env(env, expected):
    with patch("superagi.helper.auth.get_config", side_effect=lambda key, default=None: env if env else default):
        assert is_dev_env() is expected


@pytest.mark.parametrize("env", [None, "PROD", "STAGING"])
def test_check_auth_requires_jwt_unless_dev(env):
    authorize = MagicMock()
    with patch("superagi.helper.auth.get_config", side_effect=lambda key, default=None: env if env else default):
        check_auth(authorize)
    authorize.jwt_required.assert_called_once()


def test_check_auth_skips_jwt_in_explicit_dev():
    authorize = MagicMock()
    with patch("superagi.helper.auth.get_config", return_value="DEV"):
        check_auth(authorize)
    authorize.jwt_required.assert_not_called()


def test_get_current_user_uses_jwt_subject_when_env_unset():
    authorize = MagicMock()
    authorize.get_jwt_subject.return_value = "user@example.com"
    with patch("superagi.helper.auth.get_config", side_effect=lambda key, default=None: default), \
            patch("superagi.helper.auth.db") as mock_db:
        get_current_user(authorize)
    authorize.get_jwt_subject.assert_called_once()
    mock_db.session.query.return_value.filter.assert_called_once()
