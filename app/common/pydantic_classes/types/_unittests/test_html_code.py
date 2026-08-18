"""PyTest unit tests for the Pydantic ``HTMLResponseCode`` type."""

from typing import Annotated, Any

import pytest
from fastapi import FastAPI, Form, Query, status
from fastapi.testclient import TestClient
from pydantic import BaseModel, ValidationError

from app.common.pydantic_classes.types.html_code import (
    HTMLResponseCode,
    HTMLResponseCodeEnum,
)


class HTMLCodeModel(BaseModel):
    """Pydantic model for testing the ``HTMLResponseCode`` type."""

    code: HTMLResponseCode
    """An HTTP response code stored as an ``HTMLResponseCodeEnum``."""


def build_app() -> FastAPI:
    app = FastAPI()

    @app.post("/form")
    async def read_form(model: Annotated[HTMLCodeModel, Form()]) -> dict:
        return {"code": int(model.code)}

    @app.get("/query")
    async def read_query(model: Annotated[HTMLCodeModel, Query()]) -> dict:
        return {"code": int(model.code)}

    return app


@pytest.fixture
def client() -> TestClient:
    return TestClient(build_app())


# ============================================================================
# HTMLResponseCodeEnum - enum tests
# ============================================================================


def test_enum_is_generated_from_status() -> None:
    """Every ``HTTP_`` member of ``fastapi.status`` is present in the enum."""
    expected = {k for k in status.__dict__ if k.startswith("HTTP_")}

    assert {member.name for member in HTMLResponseCodeEnum} == expected


@pytest.mark.parametrize(
    ("name", "value"),
    [
        ("HTTP_200_OK", status.HTTP_200_OK),
        ("HTTP_302_FOUND", status.HTTP_302_FOUND),
        ("HTTP_404_NOT_FOUND", status.HTTP_404_NOT_FOUND),
        ("HTTP_500_INTERNAL_SERVER_ERROR", status.HTTP_500_INTERNAL_SERVER_ERROR),
    ],
)
def test_enum_members_match_status_values(name: str, value: int) -> None:
    """Enum members carry the same integer value as ``fastapi.status``."""
    assert HTMLResponseCodeEnum[name].value == value


def test_enum_members_are_integers() -> None:
    """The enum is an ``IntEnum``, so members compare equal to their ints."""
    assert HTMLResponseCodeEnum["HTTP_200_OK"] == 200


# ============================================================================
# HTMLResponseCode type - model tests
# ============================================================================


@pytest.mark.parametrize(
    "value",
    [
        status.HTTP_200_OK,
        status.HTTP_302_FOUND,
        status.HTTP_303_SEE_OTHER,
        status.HTTP_307_TEMPORARY_REDIRECT,
        status.HTTP_401_UNAUTHORIZED,
        status.HTTP_404_NOT_FOUND,
        status.HTTP_500_INTERNAL_SERVER_ERROR,
    ],
)
def test_model_valid(value: int) -> None:
    """Any integer matching a status code is accepted and stored as the enum."""
    model = HTMLCodeModel(code=value)  # type: ignore[arg-type]

    assert model.code == HTMLResponseCodeEnum(value)
    assert int(model.code) == value


def test_model_accepts_enum_member() -> None:
    """Passing an enum member directly is accepted."""
    model = HTMLCodeModel(code=HTMLResponseCodeEnum["HTTP_200_OK"])

    assert model.code == 200


@pytest.mark.parametrize("value", [0, 1, 99, 600, 99999, -200])
def test_model_rejects_unknown_code(value: int) -> None:
    """Integers that are not valid status codes fail validation."""
    with pytest.raises(ValidationError):
        HTMLCodeModel(code=value)  # type: ignore[arg-type]


@pytest.mark.parametrize("value", ["abc", "1.5", (), [], {}, None])
def test_model_rejects_non_int(value: object) -> None:
    """Values that cannot be coerced to a valid enum member fail validation."""
    with pytest.raises(ValidationError):
        HTMLCodeModel(code=value)  # type: ignore[arg-type]


def test_model_missing_field() -> None:
    """Omitting the mandatory code field raises a ``ValidationError``."""
    with pytest.raises(ValidationError):
        HTMLCodeModel()  # type: ignore[call-arg]


# ============================================================================
# Endpoint tests - Form parameters
# ============================================================================


@pytest.mark.parametrize(
    "value",
    [status.HTTP_200_OK, status.HTTP_302_FOUND, status.HTTP_404_NOT_FOUND],
)
def test_form_valid(client: TestClient, value: Any) -> None:  # noqa: ANN401
    """A valid status code submitted as form data is accepted."""
    response = client.post("/form", data={"code": value})

    assert response.status_code == 200
    assert response.json()["code"] == value


@pytest.mark.parametrize("value", [0, 99999, "abc", ""])
def test_form_invalid(client: TestClient, value: Any) -> None:  # noqa: ANN401
    """Invalid form codes are rejected with HTTP 422."""
    response = client.post("/form", data={"code": value})

    assert response.status_code == 422


def test_form_missing(client: TestClient) -> None:
    """Omitting the required form field is rejected with HTTP 422."""
    response = client.post("/form", data={})

    assert response.status_code == 422


# ============================================================================
# Endpoint tests - Query parameters
# ============================================================================


def test_query_valid(client: TestClient) -> None:
    """A valid status code query parameter is accepted."""
    response = client.get("/query", params={"code": status.HTTP_200_OK})

    assert response.status_code == 200
    assert response.json()["code"] == status.HTTP_200_OK


@pytest.mark.parametrize("value", [0, 99999, "abc", ""])
def test_query_invalid(client: TestClient, value: Any) -> None:  # noqa: ANN401
    """Invalid code query parameters are rejected with HTTP 422."""
    response = client.get("/query", params={"code": value})

    assert response.status_code == 422


def test_query_missing(client: TestClient) -> None:
    """Omitting the code query parameter is rejected with HTTP 422."""
    response = client.get("/query")

    assert response.status_code == 422
