import pytest

from superagi.config.config import validate_jwt_secret_key

STRONG_KEY = "a" * 16 + "B3x9Zq7Lm2Pw4Rt8"


@pytest.mark.parametrize("secret_key", [None, "", "secret", "YOUR_JWT_SECRET_KEY", "short-key"])
def test_prod_rejects_weak_jwt_secret_key(secret_key):
    with pytest.raises(RuntimeError):
        validate_jwt_secret_key(secret_key, "PROD")


def test_prod_accepts_strong_jwt_secret_key():
    validate_jwt_secret_key(STRONG_KEY, "PROD")


def test_dev_does_not_enforce_jwt_secret_key():
    validate_jwt_secret_key("secret", "DEV")
