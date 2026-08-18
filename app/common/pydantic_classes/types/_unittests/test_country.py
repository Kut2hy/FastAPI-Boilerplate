"""PyTest unit tests for the Pydantic ``CountryCode`` type and its helpers."""

from typing import Annotated

import pytest
from fastapi import FastAPI, Form, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from app.common.pydantic_classes.types.config import NULLISH_STRINGS
from app.common.pydantic_classes.types.country import (
    CountryCode,
    CountryCodeEnum,
    nullish_country_code_to_none,
)


class CountryModel(BaseModel):
    """Pydantic model for testing the ``CountryCode`` type."""

    country: CountryCode
    """A country code stored as a ``CountryCodeEnum``."""


def build_app() -> FastAPI:
    app = FastAPI()

    @app.post("/form")
    async def read_form(country: Annotated[CountryModel, Form()]) -> dict:
        return {"country": str(country.country)}

    @app.get("/query")
    async def read_query(model: Annotated[CountryModel, Query()]) -> dict:
        return {"country": str(model.country)}

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(build_app())


# ============================================================================
# nullish_country_code_to_none - unit tests
# ============================================================================


@pytest.mark.parametrize("nullish", sorted(NULLISH_STRINGS))
def test_nullish_country_code_to_none_returns_none(nullish: str) -> None:
    """Nullish strings are converted to None."""
    assert nullish_country_code_to_none(nullish) is None


@pytest.mark.parametrize("value", ["CZ", "sk", " CH ", "de", None])
def test_nullish_country_code_to_none_passes_through(value: str | None) -> None:
    """Non-nullish values are returned unchanged."""
    if value is not None:
        assert nullish_country_code_to_none(value) == value.strip().upper()

    else:
        assert nullish_country_code_to_none(value) is None


# ============================================================================
# CountryCode type - model tests
# ============================================================================


@pytest.mark.parametrize(
    "value",
    ["CZ", "SK", "CH", "PL", "DE", "AT", "HU"],
)
def test_country_model_valid(value: str) -> None:
    """Every enum member is accepted and stored as its two-letter code."""
    model = CountryModel(country=value)  # type: ignore[arg-type]

    assert model.country == CountryCodeEnum(value)
    assert str(model.country) == value


@pytest.mark.parametrize(
    ("given", "expected"),
    [("cz", "CZ"), ("  sk  ", "SK"), ("\tch\n", "CH"), ("De", "DE")],
)
def test_country_model_does_not_normalize(given: str, expected: str) -> None:
    assert CountryModel(country=given).country == expected  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["US", "XX", "GB", "FR", "ES"])
def test_country_model_rejects_unknown(value: str) -> None:
    """Country codes outside the enum fail validation."""
    with pytest.raises(ValidationError):
        CountryModel(country=value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["C", "CZE", "1", "123"])
def test_country_model_rejects_bad_length(value: str) -> None:
    """Values that are not exactly two characters fail validation."""
    with pytest.raises(ValidationError):
        CountryModel(country=value)  # type: ignore[arg-type]


@pytest.mark.parametrize("nullish", sorted(NULLISH_STRINGS))
def test_country_model_rejects_nullish(nullish: str) -> None:
    """Nullish strings become None, which is invalid for the required field."""
    with pytest.raises(ValidationError):
        CountryModel(country=nullish)  # type: ignore[arg-type]


def test_country_model_missing_field() -> None:
    """Omitting the mandatory country field raises a ``ValidationError``."""
    with pytest.raises(ValidationError):
        CountryModel()  # type: ignore[call-arg]


# ============================================================================
# Endpoint tests - Form parameters
# ============================================================================


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("CZ", "CZ"),
        ("SK", "SK"),
        ("DE", "DE"),
    ],
)
def test_form_valid(client: TestClient, raw: str, expected: str) -> None:
    """A valid (exact-case) country code submitted as form data is accepted."""
    response = client.post("/form", data={"country": raw})

    assert response.status_code == 200
    assert response.json()["country"] == expected


@pytest.mark.parametrize("value", ["US", "XX", "CZE", ""])
def test_form_invalid(client: TestClient, value: str) -> None:
    """Invalid form country codes are rejected with HTTP 422."""
    response = client.post("/form", data={"country": value})

    assert response.status_code == 422


def test_form_missing(client: TestClient) -> None:
    """Omitting the country form field is rejected with HTTP 422."""
    response = client.post("/form", data={})

    assert response.status_code == 422


# ============================================================================
# Endpoint tests - Query parameters
# ============================================================================


def test_query_valid(client: TestClient) -> None:
    """A valid (exact-case) country code query parameter is accepted."""
    response = client.get("/query", params={"country": "CH"})

    assert response.status_code == 200
    assert response.json()["country"] == "CH"


@pytest.mark.parametrize("value", ["US", "XX", ""])
def test_query_invalid(client: TestClient, value: str) -> None:
    """Invalid country query parameters are rejected with HTTP 422."""
    response = client.get("/query", params={"country": value})

    assert response.status_code == 422


def test_query_missing(client: TestClient) -> None:
    """Omitting the country query parameter is rejected with HTTP 422."""
    response = client.get("/query")

    assert response.status_code == 422
