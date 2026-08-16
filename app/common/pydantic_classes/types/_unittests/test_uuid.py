"""PyTest unit tests for the Pydantic ``UUID`` type and its helpers."""

from typing import Annotated
from uuid import UUID as _UUID
from uuid import uuid1, uuid4

import pytest
from fastapi import FastAPI, Form, Query
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from app.common.pydantic_classes.types.uuid4 import (
    NULLISH_STRINGS,
    UUID4,
    OptionalUUID4,
    str2uuid,
)

VALID_UUID4 = "f47ac10b-58cc-4372-a567-0e02b2c3d479"


class UUIDModel(BaseModel):
    """Pydantic model for testing the ``UUID`` type."""

    value: UUID4
    """A required UUID4."""


class OptionalUUIDModel(BaseModel):
    """Pydantic model for testing the ``OptionalUUID`` type."""

    value: OptionalUUID4 = None
    """An optional UUID4."""


def build_app() -> FastAPI:
    app = FastAPI()

    @app.post("/form")
    async def read_form(model: Annotated[UUIDModel, Form()]) -> dict:
        return {"value": str(model.value), "is_uuid": isinstance(model.value, _UUID)}

    @app.get("/query")
    async def read_query(model: Annotated[OptionalUUIDModel, Query()]) -> dict:
        return {
            "value": str(model.value) if model.value is not None else None,
            "is_uuid": isinstance(model.value, _UUID) if model.value is not None else None,
        }

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(build_app())


# ============================================================================
# str2uuid - unit tests
# ============================================================================


def test_str2uuid_converts_string() -> None:
    """A UUID string is converted to a ``UUID`` instance."""
    result = str2uuid(VALID_UUID4)

    assert isinstance(result, _UUID)
    assert str(result) == VALID_UUID4


def test_str2uuid_strips_whitespace() -> None:
    """Surrounding whitespace is trimmed before conversion."""
    result = str2uuid(f"  {VALID_UUID4}  ")

    assert isinstance(result, _UUID)
    assert str(result) == VALID_UUID4


def test_str2uuid_passes_through_uuid_instance() -> None:
    """An existing ``UUID`` instance is returned unchanged."""
    existing = uuid4()

    assert str2uuid(existing) is existing


@pytest.mark.parametrize("nullish", sorted(NULLISH_STRINGS))
def test_str2uuid_nullish_becomes_none(nullish: str) -> None:
    """Nullish strings are ported to None."""
    assert str2uuid(nullish) is None


@pytest.mark.parametrize("value", ["not-a-uuid", "12345", "zzzzzzzz"])
def test_str2uuid_rejects_invalid_string(value: str) -> None:
    """Strings that are not valid UUIDs raise a ``ValueError``."""
    with pytest.raises(ValueError):  # noqa: PT011
        str2uuid(value)


@pytest.mark.parametrize("value", [1, 1.0, True, (), [], {}])
def test_str2uuid_rejects_non_string(value: object) -> None:
    """Non-string, non-UUID inputs raise a ``ValueError``."""
    with pytest.raises(ValueError, match="must be a string or UUID"):
        str2uuid(value)  # type: ignore[arg-type]


# ============================================================================
# UUID type - model tests
# ============================================================================


def test_uuid_model_accepts_string() -> None:
    """A valid UUID4 string is coerced to a ``UUID`` instance."""
    model = UUIDModel(value=VALID_UUID4)  # type: ignore[arg-type]

    assert isinstance(model.value, _UUID)
    assert str(model.value) == VALID_UUID4


def test_uuid_model_accepts_uuid_instance() -> None:
    """A generated UUID4 instance is accepted."""
    generated = uuid4()
    model = UUIDModel(value=generated)  # type: ignore[arg-type]

    assert model.value == generated


def test_uuid_model_rejects_non_v4() -> None:
    """A non-version-4 UUID fails the ``UUID4`` constraint."""
    with pytest.raises(ValidationError):
        UUIDModel(value=uuid1())  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["not-a-uuid", "12345"])
def test_uuid_model_rejects_invalid_string(value: str) -> None:
    """Invalid UUID strings fail validation."""
    with pytest.raises(ValidationError):
        UUIDModel(value=value)  # type: ignore[arg-type]


@pytest.mark.parametrize("nullish", sorted(NULLISH_STRINGS))
def test_uuid_model_rejects_nullish(nullish: str) -> None:
    """Nullish strings become None, which is invalid for the required field."""
    with pytest.raises(ValidationError):
        UUIDModel(value=nullish)  # type: ignore[arg-type]


def test_uuid_model_missing_field() -> None:
    """Omitting the mandatory value field raises a ``ValidationError``."""
    with pytest.raises(ValidationError):
        UUIDModel()  # type: ignore[call-arg]


# ============================================================================
# OptionalUUID type - model tests
# ============================================================================


def test_optional_uuid_model_accepts_string() -> None:
    """A valid UUID4 string is coerced to a ``UUID`` instance."""
    model = OptionalUUIDModel(value=VALID_UUID4)  # type: ignore[arg-type]

    assert isinstance(model.value, _UUID)
    assert str(model.value) == VALID_UUID4


@pytest.mark.parametrize("nullish", sorted(NULLISH_STRINGS))
def test_optional_uuid_model_nullish_becomes_none(nullish: str) -> None:
    """Nullish strings are ported to None."""
    model = OptionalUUIDModel(value=nullish)  # type: ignore[arg-type]

    assert model.value is None


def test_optional_uuid_model_accepts_explicit_none() -> None:
    """An explicit None is accepted."""
    assert OptionalUUIDModel(value=None).value is None


def test_optional_uuid_model_defaults_to_none() -> None:
    """Omitting the optional field defaults to None."""
    assert OptionalUUIDModel().value is None


@pytest.mark.parametrize("value", ["not-a-uuid", "12345"])
def test_optional_uuid_model_rejects_invalid_string(value: str) -> None:
    """Non-nullish invalid strings still fail validation."""
    with pytest.raises(ValidationError):
        OptionalUUIDModel(value=value)  # type: ignore[arg-type]


# ============================================================================
# Endpoint tests - Form parameters
# ============================================================================


def test_form_valid(client: TestClient) -> None:
    """A valid UUID submitted as form data is coerced to a UUID."""
    response = client.post("/form", data={"value": VALID_UUID4})

    assert response.status_code == 200
    data = response.json()
    assert data["value"] == VALID_UUID4
    assert data["is_uuid"] is True


@pytest.mark.parametrize("value", ["not-a-uuid", ""])
def test_form_invalid(client: TestClient, value: str) -> None:
    """Invalid form UUIDs are rejected with HTTP 422."""
    response = client.post("/form", data={"value": value})

    assert response.status_code == 422


def test_form_missing(client: TestClient) -> None:
    """Omitting the UUID form field is rejected with HTTP 422."""
    response = client.post("/form", data={})

    assert response.status_code == 422


# ============================================================================
# Endpoint tests - Query parameters
# ============================================================================


def test_query_valid(client: TestClient) -> None:
    """A valid optional UUID query parameter is coerced to a UUID."""
    response = client.get("/query", params={"value": VALID_UUID4})

    assert response.status_code == 200
    data = response.json()
    assert data["value"] == VALID_UUID4
    assert data["is_uuid"] is True


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
