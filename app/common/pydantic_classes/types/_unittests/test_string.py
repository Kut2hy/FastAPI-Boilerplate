"""PyTest unit tests for the Pydantic string types and their helpers."""

from typing import Annotated

import pytest
from fastapi import FastAPI, Form, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from app.common.pydantic_classes.types.config import NULLISH_STRINGS
from app.common.pydantic_classes.types.string import (
    LONG_STRING_MAX_LENGTH,
    SHORT_STRING_MAX_LENGTH,
    STRING_MAX_LENGTH,
    LongString,
    OptionalLongString,
    OptionalShortString,
    OptionalString,
    ShortString,
    String,
    nullish_string_to_none,
)


class ShortStringModel(BaseModel):
    value: ShortString


class OptionalShortStringModel(BaseModel):
    value: OptionalShortString = None


class StringModel(BaseModel):
    value: String


class OptionalStringModel(BaseModel):
    value: OptionalString = None


class LongStringModel(BaseModel):
    value: LongString


class OptionalLongStringModel(BaseModel):
    value: OptionalLongString = None


def build_app() -> FastAPI:
    app = FastAPI()

    @app.post("/form")
    async def read_form(model: Annotated[StringModel, Form()]) -> dict:
        return {"value": model.value}

    @app.get("/query")
    async def read_query(model: Annotated[OptionalStringModel, Query()]) -> dict:
        return {"value": model.value}

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(build_app())


# ============================================================================
# nullish_string_to_none - unit tests
# ============================================================================


@pytest.mark.parametrize("nullish", sorted(NULLISH_STRINGS))
def test_nullish_string_to_none_returns_none(nullish: str) -> None:
    """Nullish strings are converted to None."""
    assert nullish_string_to_none(nullish) is None


@pytest.mark.parametrize("value", ["hello", "  spaced  ", "0", None])
def test_nullish_string_to_none_passes_through(value: str | None) -> None:
    """Non-nullish values are returned unchanged."""
    assert nullish_string_to_none(value) == value


# ============================================================================
# ShortString / String / LongString - required types
# ============================================================================


@pytest.mark.parametrize(
    ("model_cls", "max_length"),
    [
        (ShortStringModel, SHORT_STRING_MAX_LENGTH),
        (StringModel, STRING_MAX_LENGTH),
        (LongStringModel, LONG_STRING_MAX_LENGTH),
    ],
)
def test_required_string_valid(model_cls: type[BaseModel], max_length: int) -> None:
    """A single character and a max-length string are both accepted."""
    assert model_cls(value="x").model_dump().get("value") == "x"

    boundary = "a" * max_length
    assert model_cls(value=boundary).model_dump().get("value") == boundary


@pytest.mark.parametrize(
    "model_cls",
    [ShortStringModel, StringModel, LongStringModel],
)
def test_required_string_rejects_empty(model_cls: type[BaseModel]) -> None:
    """An empty string violates the ``min_length=1`` constraint."""
    with pytest.raises(ValidationError):
        model_cls(value="")


@pytest.mark.parametrize(
    ("model_cls", "max_length"),
    [
        (ShortStringModel, SHORT_STRING_MAX_LENGTH),
        (StringModel, STRING_MAX_LENGTH),
        (LongStringModel, LONG_STRING_MAX_LENGTH),
    ],
)
def test_required_string_rejects_over_max(model_cls: type[BaseModel], max_length: int) -> None:
    """A string longer than the maximum fails validation."""
    with pytest.raises(ValidationError):
        model_cls(value="a" * (max_length + 1))


@pytest.mark.parametrize(
    "model_cls",
    [ShortStringModel, StringModel, LongStringModel],
)
def test_required_string_missing_field(model_cls: type[BaseModel]) -> None:
    """Omitting the mandatory field raises a ``ValidationError``."""
    with pytest.raises(ValidationError):
        model_cls()


# ============================================================================
# Optional string variants
# ============================================================================


@pytest.mark.parametrize(
    ("model_cls", "max_length"),
    [
        (OptionalShortStringModel, SHORT_STRING_MAX_LENGTH),
        (OptionalStringModel, STRING_MAX_LENGTH),
        (OptionalLongStringModel, LONG_STRING_MAX_LENGTH),
    ],
)
def test_optional_string_valid(model_cls: type[BaseModel], max_length: int) -> None:
    """A regular and a max-length string are both accepted."""
    assert model_cls(value="hello").model_dump().get("value") == "hello"

    boundary = "a" * max_length
    assert model_cls(value=boundary).model_dump().get("value") == boundary


@pytest.mark.parametrize(
    "model_cls",
    [OptionalShortStringModel, OptionalStringModel, OptionalLongStringModel],
)
@pytest.mark.parametrize("nullish", sorted(NULLISH_STRINGS))
def test_optional_string_nullish_becomes_none(model_cls: type[BaseModel], nullish: str) -> None:
    """Nullish strings are ported to None."""
    assert model_cls(value=nullish).model_dump().get("value") is None


@pytest.mark.parametrize(
    "model_cls",
    [OptionalShortStringModel, OptionalStringModel, OptionalLongStringModel],
)
def test_optional_string_accepts_explicit_none(model_cls: type[BaseModel]) -> None:
    """An explicit None is accepted."""
    assert model_cls(value=None).model_dump().get("value") is None


@pytest.mark.parametrize(
    "model_cls",
    [OptionalShortStringModel, OptionalStringModel, OptionalLongStringModel],
)
def test_optional_string_defaults_to_none(model_cls: type[BaseModel]) -> None:
    """Omitting the optional field defaults to None."""
    assert model_cls().model_dump().get("value") is None


@pytest.mark.parametrize(
    ("model_cls", "max_length"),
    [
        (OptionalShortStringModel, SHORT_STRING_MAX_LENGTH),
        (OptionalStringModel, STRING_MAX_LENGTH),
        (OptionalLongStringModel, LONG_STRING_MAX_LENGTH),
    ],
)
def test_optional_string_rejects_over_max(model_cls: type[BaseModel], max_length: int) -> None:
    """A non-nullish string longer than the maximum fails validation."""
    with pytest.raises(ValidationError):
        model_cls(value="a" * (max_length + 1))


# ============================================================================
# Endpoint tests - Form parameters
# ============================================================================


def test_form_valid(client: TestClient) -> None:
    """A valid string submitted as form data is accepted."""
    response = client.post("/form", data={"value": "hello"})

    assert response.status_code == 200
    assert response.json()["value"] == "hello"


@pytest.mark.parametrize("value", ["", "a" * (STRING_MAX_LENGTH + 1)])
def test_form_invalid(client: TestClient, value: str) -> None:
    """Empty and over-long form strings are rejected with HTTP 422."""
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
    """A valid optional string query parameter is accepted."""
    response = client.get("/query", params={"value": "hello"})

    assert response.status_code == 200
    assert response.json()["value"] == "hello"


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
