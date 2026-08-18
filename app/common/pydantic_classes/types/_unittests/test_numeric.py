"""PyTest unit tests for the Pydantic numeric types and their helpers."""

from typing import Annotated, Any

import pytest
from fastapi import FastAPI, Form, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from app.common.pydantic_classes.types.config import INTEGER_MAX_VALUE, NULLISH_STRINGS
from app.common.pydantic_classes.types.numeric import (
    OptionalPositiveInt,
    PositiveInt,
    nullish_to_none,
)


class PositiveIntModel(BaseModel):
    """Pydantic model for testing the ``PositiveInt`` type."""

    value: PositiveInt
    """A required positive integer."""


class OptionalPositiveIntModel(BaseModel):
    """Pydantic model for testing the ``OptionalPositiveInt`` type."""

    value: OptionalPositiveInt = None
    """An optional positive integer."""


def build_app() -> FastAPI:
    app = FastAPI()

    @app.post("/form")
    async def read_form(model: Annotated[PositiveIntModel, Form()]) -> dict:
        return {"value": model.value}

    @app.get("/query")
    async def read_query(model: Annotated[OptionalPositiveIntModel, Query()]) -> dict:
        return {"value": model.value}

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(build_app())


# ============================================================================
# nullish_to_none - unit tests
# ============================================================================


@pytest.mark.parametrize("nullish", sorted(NULLISH_STRINGS))
def test_nullish_to_none_returns_none(nullish: str) -> None:
    """Nullish strings are converted to None."""
    assert nullish_to_none(nullish) is None


@pytest.mark.parametrize("value", [0, 1, 42, INTEGER_MAX_VALUE, "5", None])
def test_nullish_to_none_passes_through(value: int | str | None) -> None:
    """Non-nullish values are returned unchanged."""
    assert nullish_to_none(value) == value


# ============================================================================
# PositiveInt type - model tests
# ============================================================================


@pytest.mark.parametrize("value", [0, 1, 42, 999, INTEGER_MAX_VALUE])
def test_positive_int_model_valid(value: int) -> None:
    """Integers within the inclusive [0, MAX_INPUT_LENGTH] range are accepted."""
    model = PositiveIntModel(value=value)

    assert model.value == value


def test_positive_int_model_accepts_lower_boundary() -> None:
    """Exactly 0 is accepted."""
    assert PositiveIntModel(value=0).value == 0


def test_positive_int_model_accepts_upper_boundary() -> None:
    """Exactly ``MAX_INPUT_LENGTH`` is accepted."""
    assert PositiveIntModel(value=INTEGER_MAX_VALUE).value == INTEGER_MAX_VALUE


@pytest.mark.parametrize("value", [-1, -100, INTEGER_MAX_VALUE + 1])
def test_positive_int_model_rejects_out_of_range(value: int) -> None:
    """Integers outside the allowed range fail validation."""
    with pytest.raises(ValidationError):
        PositiveIntModel(value=value)


@pytest.mark.parametrize("value", ["abc", "1.5", (), [], {}])
def test_positive_int_model_rejects_non_int(value: object) -> None:
    """Values that cannot be coerced to an integer fail validation."""
    with pytest.raises(ValidationError):
        PositiveIntModel(value=value)  # type: ignore[arg-type]


def test_positive_int_model_missing_field() -> None:
    """Omitting the mandatory value field raises a ``ValidationError``."""
    with pytest.raises(ValidationError):
        PositiveIntModel()  # type: ignore[call-arg]


# ============================================================================
# OptionalPositiveInt type - model tests
# ============================================================================


@pytest.mark.parametrize("value", [0, 1, 42, INTEGER_MAX_VALUE])
def test_optional_positive_int_model_valid(value: int) -> None:
    """Valid integers pass through unchanged."""
    model = OptionalPositiveIntModel(value=value)

    assert model.value == value


@pytest.mark.parametrize("nullish", sorted(NULLISH_STRINGS))
def test_optional_positive_int_model_nullish_becomes_none(nullish: str) -> None:
    """Nullish strings are ported to None."""
    model = OptionalPositiveIntModel(value=nullish)  # type: ignore[arg-type]

    assert model.value is None


def test_optional_positive_int_model_accepts_explicit_none() -> None:
    """An explicit None is accepted."""
    assert OptionalPositiveIntModel(value=None).value is None


def test_optional_positive_int_model_defaults_to_none() -> None:
    """Omitting the optional field defaults to None."""
    assert OptionalPositiveIntModel().value is None


@pytest.mark.parametrize("value", [-1, INTEGER_MAX_VALUE + 1])
def test_optional_positive_int_model_rejects_out_of_range(value: int) -> None:
    """Non-nullish integers outside the range still fail validation."""
    with pytest.raises(ValidationError):
        OptionalPositiveIntModel(value=value)


# ============================================================================
# Endpoint tests - Form parameters
# ============================================================================


@pytest.mark.parametrize("value", [0, 1, INTEGER_MAX_VALUE])
def test_form_valid(client: TestClient, value: Any) -> None:  # noqa: ANN401
    """A valid positive integer submitted as form data is accepted."""
    response = client.post("/form", data={"value": value})

    assert response.status_code == 200
    assert response.json()["value"] == value


@pytest.mark.parametrize("value", [-1, INTEGER_MAX_VALUE + 1, "abc", ""])
def test_form_invalid(client: TestClient, value: Any) -> None:  # noqa: ANN401
    """Invalid form values are rejected with HTTP 422."""
    response = client.post("/form", data={"value": value})

    assert response.status_code == 422


def test_form_missing(client: TestClient) -> None:
    """Omitting the required form field is rejected with HTTP 422."""
    response = client.post("/form", data={})

    assert response.status_code == 422


# ============================================================================
# Endpoint tests - Query parameters
# ============================================================================


def test_query_valid(client: TestClient) -> None:
    """A valid optional integer query parameter is accepted."""
    response = client.get("/query", params={"value": 42})

    assert response.status_code == 200
    assert response.json()["value"] == 42


@pytest.mark.parametrize("nullish", sorted(NULLISH_STRINGS))
def test_query_nullish_becomes_none(client: TestClient, nullish: str) -> None:
    """Nullish query values are ported to None."""
    response = client.get("/query", params={"value": nullish})

    assert response.status_code == 200
    assert response.json()["value"] is None


def test_query_missing_defaults_to_none(client: TestClient) -> None:
    """Omitting the optional query parameter defaults to None."""
    response = client.get("/query")

    assert response.status_code == 200
    assert response.json()["value"] is None
