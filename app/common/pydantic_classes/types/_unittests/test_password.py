"""PyTest unit tests for the Pydantic ``RawPassword`` type and its helpers."""

from typing import Annotated

import pytest
from fastapi import FastAPI, Form, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, Secret, ValidationError

from app.common.pydantic_classes.types.config import STANDARD_VARCHAR_LENGTH
from app.common.pydantic_classes.types.password import (
    RawPassword,
    pattern_validator,
)

# A password satisfying every rule: >= 10 chars, lower, upper, digit, special.
VALID_PASSWORD = "Abcdefgh1!"  # noqa: S105 -> This is a test password, not a real one.


class PasswordModel(BaseModel):
    """Pydantic model for testing the ``RawPassword`` type."""

    password: RawPassword
    """A password stored as a Pydantic ``Secret``."""


def build_app() -> FastAPI:
    app = FastAPI()

    @app.post("/form")
    async def read_form(password: Annotated[PasswordModel, Form()]) -> dict:
        # Prove FastAPI produced a Secret wrapping the validated password.
        return {
            "password": password.password.get_secret_value(),
            "is_secret": isinstance(password.password, Secret),
        }

    @app.get("/query")
    async def read_query(model: Annotated[PasswordModel, Query()]) -> dict:
        return {
            "password": model.password.get_secret_value(),
            "is_secret": isinstance(model.password, Secret),
        }

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(build_app())


# ============================================================================
# pattern_validator - unit tests
# ============================================================================


@pytest.mark.parametrize(
    "value",
    [
        "Abcdefgh1!",
        "P@ssw0rd12",
        "Str0ng#Pass",
        "aA1!aaaaaa",
        "Zz9$Zz9$Zz",
        "Has Space1A!",  # a space counts as a special character
        "Únìcödé1A!x",  # non-ASCII letters plus required classes
    ],
)
def test_pattern_validator_accepts_valid(value: str) -> None:
    """A password matching every rule is returned unchanged."""
    assert pattern_validator(value) == value


@pytest.mark.parametrize(
    "value",
    [
        "abcdefgh1!",  # no uppercase
        "ABCDEFGH1!",  # no lowercase
        "Abcdefghi!",  # no digit
        "Abcdefgh12",  # no special character
        "Aa1!",  # too short (< 10)
        "Aa1!aa1!a",  # exactly 9 characters
        "",  # empty
    ],
)
def test_pattern_validator_rejects_invalid(value: str) -> None:
    """A password missing any rule raises a ``ValueError``."""
    with pytest.raises(ValueError, match="does not match the required pattern"):
        pattern_validator(value)


def test_pattern_validator_accepts_exact_min_length() -> None:
    """A password of exactly 10 characters is accepted."""
    assert len(VALID_PASSWORD) == 10
    assert pattern_validator(VALID_PASSWORD) == VALID_PASSWORD


# ============================================================================
# RawPassword type - model tests
# ============================================================================


@pytest.mark.parametrize(
    "value",
    [
        "Abcdefgh1!",
        "P@ssw0rd12",
        "Str0ng#Pass",
        "aA1!aaaaaa",
        "Zz9$Zz9$Zz",
    ],
)
def test_password_model_valid(value: str) -> None:
    """A valid password is wrapped in a ``Secret`` exposing the original value."""
    model = PasswordModel(password=Secret(value))

    assert isinstance(model.password, Secret)
    assert model.password.get_secret_value() == value


@pytest.mark.parametrize(
    "value",
    [
        "abcdefgh1!",  # no uppercase
        "ABCDEFGH1!",  # no lowercase
        "Abcdefghi!",  # no digit
        "Abcdefgh12",  # no special character
    ],
)
def test_password_model_rejects_missing_char_class(value: str) -> None:
    """Passwords missing a required character class fail validation."""
    with pytest.raises(ValidationError):
        PasswordModel(password=Secret(value))


@pytest.mark.parametrize("value", ["Aa1!", "Aa1!aa1!a", "Short1!Aa"])
def test_password_model_rejects_too_short(value: str) -> None:
    """Passwords shorter than 10 characters fail validation."""
    assert len(value) < 10
    with pytest.raises(ValidationError):
        PasswordModel(password=Secret(value))


@pytest.mark.parametrize("value", [1, 1.0, True, None, (), [], {}])
def test_password_model_rejects_non_string(value: object) -> None:
    """Non-string inputs raise a ``ValidationError``."""
    with pytest.raises(ValidationError):
        PasswordModel(password=Secret(value))  # type: ignore[arg-type]


def test_password_model_accepts_min_length_boundary() -> None:
    """A password of exactly 10 characters is accepted."""
    value = VALID_PASSWORD
    assert len(value) == 10

    model = PasswordModel(password=Secret(value))

    assert model.password.get_secret_value() == value


def test_password_model_accepts_max_length_boundary() -> None:
    """A password exactly ``MAX_INPUT_LENGTH`` characters long is accepted."""
    # "A1!" satisfies upper/digit/special, padded with lowercase to the limit.
    value = "A1!" + "a" * (STANDARD_VARCHAR_LENGTH - 3)

    assert len(value) == STANDARD_VARCHAR_LENGTH
    model = PasswordModel(password=Secret(value))

    assert model.password.get_secret_value() == value


def test_password_model_rejects_over_max_length() -> None:
    """A password longer than ``MAX_INPUT_LENGTH`` raises a ``ValidationError``."""
    value = "A1!" + "a" * (STANDARD_VARCHAR_LENGTH - 3 + 1)

    assert len(value) > STANDARD_VARCHAR_LENGTH
    with pytest.raises(ValidationError):
        PasswordModel(password=Secret(value))


def test_password_model_missing_field() -> None:
    """Omitting the mandatory password field raises a ``ValidationError``."""
    with pytest.raises(ValidationError):
        PasswordModel()  # type: ignore[call-arg]


# ============================================================================
# RawPassword type - Secret behavior
# ============================================================================


def test_password_masks_in_repr_and_str() -> None:
    """The secret value must never leak through ``repr``/``str``."""
    model = PasswordModel(password=Secret(VALID_PASSWORD))

    assert VALID_PASSWORD not in repr(model.password)
    assert VALID_PASSWORD not in str(model.password)
    assert VALID_PASSWORD not in repr(model)


def test_password_masks_on_model_dump() -> None:
    """Serializing the model must not expose the raw password."""
    model = PasswordModel(password=Secret(VALID_PASSWORD))

    assert model.model_dump()["password"].get_secret_value() == VALID_PASSWORD
    assert VALID_PASSWORD not in model.model_dump_json()


# ============================================================================
# Endpoint tests - Form parameters
# ============================================================================


def test_form_valid(client: TestClient) -> None:
    """A valid password submitted as form data is wrapped in a Secret."""
    response = client.post("/form", data={"password": VALID_PASSWORD})

    assert response.status_code == 200
    data = response.json()
    assert data["password"] == VALID_PASSWORD
    assert data["is_secret"] is True


@pytest.mark.parametrize(
    "value",
    ["abcdefgh1!", "ABCDEFGH1!", "Abcdefghi!", "Abcdefgh12", "Aa1!", ""],
)
def test_form_invalid(client: TestClient, value: str) -> None:
    """Invalid form passwords are rejected with HTTP 422."""
    response = client.post("/form", data={"password": value})

    assert response.status_code == 422


def test_form_missing(client: TestClient) -> None:
    """Omitting the password form field is rejected with HTTP 422."""
    response = client.post("/form", data={})

    assert response.status_code == 422


# ============================================================================
# Endpoint tests - Query parameters
# ============================================================================


def test_query_valid(client: TestClient) -> None:
    """A valid password query parameter is wrapped in a Secret."""
    response = client.get("/query", params={"password": VALID_PASSWORD})

    assert response.status_code == 200
    data = response.json()
    assert data["password"] == VALID_PASSWORD
    assert data["is_secret"] is True


@pytest.mark.parametrize("value", ["abcdefgh1!", "Abcdefgh12", "Aa1!", ""])
def test_query_invalid(client: TestClient, value: str) -> None:
    """Invalid password query parameters are rejected with HTTP 422."""
    response = client.get("/query", params={"password": value})

    assert response.status_code == 422


def test_query_missing(client: TestClient) -> None:
    """Omitting the password query parameter is rejected with HTTP 422."""
    response = client.get("/query")

    assert response.status_code == 422
