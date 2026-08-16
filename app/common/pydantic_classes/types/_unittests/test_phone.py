"""PyTest unit tests for the Pydantic ``PhoneNumber`` type and its helpers."""

from typing import Annotated

import pytest
from fastapi import FastAPI, Form, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from app.common.pydantic_classes.types.config import NULLISH_STRINGS
from app.common.pydantic_classes.types.phone import (
    PhoneNumber,
    nullish_phone_number_to_none,
)


class PhoneModel(BaseModel):
    """Pydantic model for testing the ``PhoneNumber`` type."""

    phone: PhoneNumber
    """A phone number string."""


def build_app() -> FastAPI:
    app = FastAPI()

    @app.post("/form")
    async def read_form(model: Annotated[PhoneModel, Form()]) -> dict:
        return {"phone": model.phone}

    @app.get("/query")
    async def read_query(model: Annotated[PhoneModel, Query()]) -> dict:
        return {"phone": model.phone}

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(build_app())


# ============================================================================
# nullish_phone_number_to_none - unit tests
# ============================================================================


@pytest.mark.parametrize("nullish", sorted(NULLISH_STRINGS))
def test_nullish_phone_number_to_none_returns_none(nullish: str) -> None:
    """Nullish strings are converted to None."""
    assert nullish_phone_number_to_none(nullish) is None


@pytest.mark.parametrize("value", ["+420123456789", "+49123456789", None])
def test_nullish_phone_number_to_none_passes_through(value: str | None) -> None:
    """Non-nullish values are returned unchanged."""
    assert nullish_phone_number_to_none(value) == value


# ============================================================================
# PhoneNumber type - model tests
# ============================================================================


@pytest.mark.parametrize(
    "value",
    [
        "+41123456789",  # Swiss: +41 + 9 digits
        "+48123456789",  # Polish: +48 + 9 digits
        "+420123456789",  # Czech: +420 + 9 digits
        "+421123456789",  # Slovak: +421 + 9 digits
        "+491234567890",  # German: +49 + 10 digits
        "+4912345678901",  # German: +49 + 11 digits
        "+431234567890",  # Austrian: +43 + 10 digits
        "+431234567890123",  # Austrian: +43 + 13 digits
        "+3612345678",  # Hungarian: +36 + 8 digits
        "+36123456789",  # Hungarian: +36 + 9 digits
    ],
)
def test_phone_model_valid(value: str) -> None:
    """Numbers matching one of the supported country patterns are accepted."""
    model = PhoneModel(phone=value)

    assert model.phone == value


@pytest.mark.parametrize(
    "value",
    [
        "123456789",  # no leading +
        "+1123456789",  # unsupported country code
        "+42012345678",  # Czech too short (8 digits)
        "+4201234567890",  # Czech too long (10 digits)
        "+49123456789",  # German too short (9 digits)
        "+420 123 456 789",  # contains spaces
        "+420abcdefghi",  # non-digit characters
        "not-a-phone",
    ],
)
def test_phone_model_rejects_invalid(value: str) -> None:
    """Numbers that do not match the required pattern fail validation."""
    with pytest.raises(ValidationError):
        PhoneModel(phone=value)


@pytest.mark.parametrize("nullish", sorted(NULLISH_STRINGS))
def test_phone_model_rejects_nullish(nullish: str) -> None:
    """Nullish strings become None, which is invalid for the required field."""
    with pytest.raises(ValidationError):
        PhoneModel(phone=nullish)


def test_phone_model_missing_field() -> None:
    """Omitting the mandatory phone field raises a ``ValidationError``."""
    with pytest.raises(ValidationError):
        PhoneModel()  # type: ignore[call-arg]


# ============================================================================
# Endpoint tests - Form parameters
# ============================================================================


def test_form_valid(client: TestClient) -> None:
    """A valid phone number submitted as form data is accepted."""
    response = client.post("/form", data={"phone": "+420123456789"})

    assert response.status_code == 200
    assert response.json()["phone"] == "+420123456789"


@pytest.mark.parametrize("value", ["123456789", "+1123456789", ""])
def test_form_invalid(client: TestClient, value: str) -> None:
    """Invalid form phone numbers are rejected with HTTP 422."""
    response = client.post("/form", data={"phone": value})

    assert response.status_code == 422


def test_form_missing(client: TestClient) -> None:
    """Omitting the phone form field is rejected with HTTP 422."""
    response = client.post("/form", data={})

    assert response.status_code == 422


# ============================================================================
# Endpoint tests - Query parameters
# ============================================================================


def test_query_valid(client: TestClient) -> None:
    """A valid phone number query parameter is accepted."""
    response = client.get("/query", params={"phone": "+491234567890"})

    assert response.status_code == 200
    assert response.json()["phone"] == "+491234567890"


@pytest.mark.parametrize("value", ["123456789", ""])
def test_query_invalid(client: TestClient, value: str) -> None:
    """Invalid phone query parameters are rejected with HTTP 422."""
    response = client.get("/query", params={"phone": value})

    assert response.status_code == 422


def test_query_missing(client: TestClient) -> None:
    """Omitting the phone query parameter is rejected with HTTP 422."""
    response = client.get("/query")

    assert response.status_code == 422
