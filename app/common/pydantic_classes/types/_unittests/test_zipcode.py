"""PyTest unit tests for the Pydantic ``PostalCode`` type and its helpers."""

from typing import Annotated

import pytest
from fastapi import FastAPI, Form, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from app.common.pydantic_classes.types.config import NULLISH_STRINGS
from app.common.pydantic_classes.types.zipcode import (
    PostalCode,
    nullish_postal_code_to_none,
)


class PostalCodeModel(BaseModel):
    """Pydantic model for testing the ``PostalCode`` type."""

    zipcode: PostalCode
    """A postal code string."""


def build_app() -> FastAPI:
    app = FastAPI()

    @app.post("/form")
    async def read_form(model: Annotated[PostalCodeModel, Form()]) -> dict:
        return {"zipcode": model.zipcode}

    @app.get("/query")
    async def read_query(model: Annotated[PostalCodeModel, Query()]) -> dict:
        return {"zipcode": model.zipcode}

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(build_app())


# ============================================================================
# nullish_postal_code_to_none - unit tests
# ============================================================================


@pytest.mark.parametrize("nullish", sorted(NULLISH_STRINGS))
def test_nullish_postal_code_to_none_returns_none(nullish: str) -> None:
    """Nullish strings are converted to None."""
    assert nullish_postal_code_to_none(nullish) is None


@pytest.mark.parametrize("value", ["11000", "110 00", "00-950", None])
def test_nullish_postal_code_to_none_passes_through(value: str | None) -> None:
    """Non-nullish values are returned unchanged."""
    assert nullish_postal_code_to_none(value) == value


# ============================================================================
# PostalCode type - model tests
# ============================================================================


@pytest.mark.parametrize(
    "value",
    [
        "11000",  # Czech/Slovak/German (5 digits)
        "110 00",  # Czech/Slovak with space
        "8001",  # Swiss/Austrian/Hungarian (4 digits)
        "00-950",  # Polish
        "10115",  # German
    ],
)
def test_postal_code_model_valid(value: str) -> None:
    """Postal codes matching one of the supported patterns are accepted."""
    model = PostalCodeModel(zipcode=value)

    assert model.zipcode == value


@pytest.mark.parametrize(
    "value",
    [
        "abc",  # non-numeric
        "12",  # too short
        "1234567",  # too long
        "00_950",  # wrong separator
        "110-00",  # not a valid Polish format
        "abcde",
    ],
)
def test_postal_code_model_rejects_invalid(value: str) -> None:
    """Postal codes that do not match the required pattern fail validation."""
    with pytest.raises(ValidationError):
        PostalCodeModel(zipcode=value)


@pytest.mark.parametrize("nullish", sorted(NULLISH_STRINGS))
def test_postal_code_model_rejects_nullish(nullish: str) -> None:
    """Nullish strings become None, which is invalid for the required field."""
    with pytest.raises(ValidationError):
        PostalCodeModel(zipcode=nullish)


def test_postal_code_model_missing_field() -> None:
    """Omitting the mandatory zipcode field raises a ``ValidationError``."""
    with pytest.raises(ValidationError):
        PostalCodeModel()  # type: ignore[call-arg]


# ============================================================================
# Endpoint tests - Form parameters
# ============================================================================


@pytest.mark.parametrize("value", ["11000", "110 00", "00-950", "8001"])
def test_form_valid(client: TestClient, value: str) -> None:
    """A valid postal code submitted as form data is accepted."""
    response = client.post("/form", data={"zipcode": value})

    assert response.status_code == 200
    assert response.json()["zipcode"] == value


@pytest.mark.parametrize("value", ["abc", "12", "1234567", ""])
def test_form_invalid(client: TestClient, value: str) -> None:
    """Invalid form postal codes are rejected with HTTP 422."""
    response = client.post("/form", data={"zipcode": value})

    assert response.status_code == 422


def test_form_missing(client: TestClient) -> None:
    """Omitting the zipcode form field is rejected with HTTP 422."""
    response = client.post("/form", data={})

    assert response.status_code == 422


# ============================================================================
# Endpoint tests - Query parameters
# ============================================================================


def test_query_valid(client: TestClient) -> None:
    """A valid postal code query parameter is accepted."""
    response = client.get("/query", params={"zipcode": "10115"})

    assert response.status_code == 200
    assert response.json()["zipcode"] == "10115"


@pytest.mark.parametrize("value", ["abc", ""])
def test_query_invalid(client: TestClient, value: str) -> None:
    """Invalid postal code query parameters are rejected with HTTP 422."""
    response = client.get("/query", params={"zipcode": value})

    assert response.status_code == 422


def test_query_missing(client: TestClient) -> None:
    """Omitting the zipcode query parameter is rejected with HTTP 422."""
    response = client.get("/query")

    assert response.status_code == 422
