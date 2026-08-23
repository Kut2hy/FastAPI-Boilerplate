"""PyTest unit tests for the Pydantic ``Email`` type and its helpers."""

from typing import Annotated

import pytest
from fastapi import FastAPI, Form, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, Secret, ValidationError

from app.common.pydantic_classes.types.config import NULLISH_STRINGS, STANDARD_VARCHAR_LENGTH
from app.common.pydantic_classes.types.email import (
    Email,
    prepare_email_value,
)


class EmailModel(BaseModel):
    """Pydantic model for testing the ``Email`` type."""

    email: Email
    """An email address stored as a Pydantic ``Secret``."""


def build_app() -> FastAPI:
    app = FastAPI()

    @app.post("/form")
    async def read_form(email: Annotated[EmailModel, Form()]) -> dict:
        # Prove FastAPI produced a Secret wrapping the normalized email.
        return {
            "email": email.email.get_secret_value(),
            "is_secret": isinstance(email.email, Secret),
        }

    @app.get("/query")
    async def read_query(model: Annotated[EmailModel, Query()]) -> dict:
        return {
            "email": model.email.get_secret_value(),
            "is_secret": isinstance(model.email, Secret),
        }

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(build_app())


# ============================================================================
# prepare_email_value - unit tests
# ============================================================================


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("user@example.com", "user@example.com"),
        ("  user@example.com  ", "user@example.com"),
        ("USER@EXAMPLE.COM", "user@example.com"),
        ("\tFoo.Bar@Example.Com\n", "foo.bar@example.com"),
        ("MiXeD@Case.IO", "mixed@case.io"),
    ],
)
def test_prepare_email_value_normalizes(raw: str, expected: str) -> None:
    """Whitespace is trimmed and the value is lower-cased."""
    assert prepare_email_value(raw) == expected


@pytest.mark.parametrize("nullish", sorted(NULLISH_STRINGS))
def test_prepare_email_value_rejects_nullish(nullish: str) -> None:
    """Nullish strings raise a ``ValueError``."""
    with pytest.raises(ValueError, match="must not be nullish"):
        prepare_email_value(nullish)


@pytest.mark.parametrize("nullish", sorted(NULLISH_STRINGS))
def test_prepare_email_value_rejects_nullish_after_strip(nullish: str) -> None:
    """Strings that become nullish only after trimming are still rejected."""
    with pytest.raises(ValueError, match="must not be nullish"):
        prepare_email_value(f"   {nullish}   ")


@pytest.mark.parametrize("value", [1, 1.0, True, None, (), [], {}, b"user@example.com"])
def test_prepare_email_value_rejects_non_string(value: object) -> None:
    """Non-string inputs raise a ``ValueError`` mentioning the offending type."""
    with pytest.raises(ValueError, match="must be a string"):
        prepare_email_value(value)  # type: ignore[arg-type]


def test_prepare_email_value_does_not_validate_pattern() -> None:
    """The helper normalizes but does not enforce the email pattern itself."""
    # A non-nullish, non-email string passes through untouched (lower-cased).
    assert prepare_email_value("Not An Email") == "not an email"


# ============================================================================
# Email type - model tests
# ============================================================================


@pytest.mark.parametrize(
    "value",
    [
        "user@example.com",
        "user.name@example.com",
        "user+tag@sub.example.co.uk",
        "u@e.io",
    ],
)
def test_email_model_valid(value: str) -> None:
    """A valid email is wrapped in a ``Secret`` exposing the original value."""
    model = EmailModel(email=Secret(value))

    assert isinstance(model.email, Secret)
    assert model.email.get_secret_value() == value


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("  User@Example.COM  ", "user@example.com"),
        ("\tFoo.Bar@Example.Com\n", "foo.bar@example.com"),
    ],
)
def test_email_model_normalizes(raw: str, normalized: str) -> None:
    """The ``BeforeValidator`` trims and lower-cases before storage."""
    model = EmailModel(email=Secret(raw))

    assert model.email.get_secret_value() == normalized


@pytest.mark.parametrize("nullish", sorted(NULLISH_STRINGS))
def test_email_model_rejects_nullish(nullish: str) -> None:
    """Nullish strings fail validation."""
    with pytest.raises(ValidationError):
        EmailModel(email=Secret(nullish))


@pytest.mark.parametrize(
    "value",
    [
        "user@example.com",
        "user.name@example.com",
        "user+tag@sub.example.co.uk",
        "u@e.io",
        "a.!#$%&'*+/=?^_`~-@example.com",
    ],
)
def test_email_model_accepts_valid_pattern(value: str) -> None:
    """The ``Email`` type accepts every address matching the email pattern."""
    model = EmailModel(email=Secret(value))

    assert model.email.get_secret_value() == value


@pytest.mark.parametrize(
    "value",
    [
        "not-an-email",
        "user@",
        "@example.com",
        "user@@example.com",
        "user @example.com",
        "user example@example.com",
        "user@exam ple.com",
        "user@.com",
    ],
)
def test_email_model_rejects_invalid_pattern(value: str) -> None:
    """The ``Email`` type refuses anything that does not match the email pattern."""
    with pytest.raises(ValidationError):
        EmailModel(email=Secret(value))


@pytest.mark.parametrize("value", [1, 1.0, True, None, (), [], {}])
def test_email_model_rejects_non_string(value: object) -> None:
    """Non-string inputs raise a ``ValidationError``."""
    with pytest.raises(ValidationError):
        EmailModel(email=Secret(value))  # type: ignore[arg-type]


def test_email_model_accepts_max_length_boundary() -> None:
    """An email exactly ``MAX_INPUT_LENGTH`` characters long is accepted."""
    value = "a" * (STANDARD_VARCHAR_LENGTH - len("@x.com")) + "@x.com"

    assert len(value) == STANDARD_VARCHAR_LENGTH
    model = EmailModel(email=Secret(value))

    assert model.email.get_secret_value() == value


def test_email_model_rejects_over_max_length() -> None:
    """An email longer than ``MAX_INPUT_LENGTH`` raises a ``ValidationError``."""
    value = "a" * (STANDARD_VARCHAR_LENGTH - len("@x.com") + 1) + "@x.com"

    assert len(value) > STANDARD_VARCHAR_LENGTH
    with pytest.raises(ValidationError):
        EmailModel(email=Secret(value))


def test_email_model_missing_field() -> None:
    """Omitting the mandatory email field raises a ``ValidationError``."""
    with pytest.raises(ValidationError):
        EmailModel()  # type: ignore[call-arg]


# ============================================================================
# Email type - Secret behavior
# ============================================================================


def test_email_masks_in_repr_and_str() -> None:
    """The secret value must never leak through ``repr``/``str``."""
    model = EmailModel(email=Secret("user@example.com"))

    assert "user@example.com" not in repr(model.email)
    assert "user@example.com" not in str(model.email)
    assert "user@example.com" not in repr(model)


def test_email_masks_on_model_dump() -> None:
    """Serializing the model must not expose the raw email."""
    model = EmailModel(email=Secret("user@example.com"))

    assert model.model_dump()["email"].get_secret_value() == "user@example.com"
    assert "user@example.com" not in model.model_dump_json()


# ============================================================================
# Endpoint tests - Form parameters
# ============================================================================


@pytest.mark.parametrize(
    ("raw", "normalized"),
    [
        ("user@example.com", "user@example.com"),
        ("  User@Example.COM  ", "user@example.com"),
    ],
)
def test_form_valid(client: TestClient, raw: str, normalized: str) -> None:
    """A valid email submitted as form data is normalized and wrapped in a Secret."""
    response = client.post("/form", data={"email": raw})

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == normalized
    assert data["is_secret"] is True


@pytest.mark.parametrize("value", ["not-an-email", "user@", "@example.com", ""])
def test_form_invalid(client: TestClient, value: str) -> None:
    """Invalid form emails are rejected with HTTP 422."""
    response = client.post("/form", data={"email": value})

    assert response.status_code == 422


def test_form_missing(client: TestClient) -> None:
    """Omitting the email form field is rejected with HTTP 422."""
    response = client.post("/form", data={})

    assert response.status_code == 422


# ============================================================================
# Endpoint tests - Query parameters
# ============================================================================


def test_query_valid(client: TestClient) -> None:
    """A valid email query parameter is normalized and wrapped in a Secret."""
    response = client.get("/query", params={"email": "  User@Example.COM  "})

    assert response.status_code == 200
    data = response.json()
    assert data["email"] == "user@example.com"
    assert data["is_secret"] is True


@pytest.mark.parametrize("value", ["not-an-email", "user@", ""])
def test_query_invalid(client: TestClient, value: str) -> None:
    """Invalid email query parameters are rejected with HTTP 422."""
    response = client.get("/query", params={"email": value})

    assert response.status_code == 422


def test_query_missing(client: TestClient) -> None:
    """Omitting the email query parameter is rejected with HTTP 422."""
    response = client.get("/query")

    assert response.status_code == 422
