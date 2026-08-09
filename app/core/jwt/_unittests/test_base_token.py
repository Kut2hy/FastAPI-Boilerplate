"""Unit tests for the BaseToken class."""

import logging
from time import time
from uuid import UUID, uuid7

import pytest
from jwt import InvalidTokenError

from app.core.jwt import _base_token

logging.basicConfig(level=logging.DEBUG)

_LOGGER = logging.getLogger(__name__)


@pytest.fixture(autouse=True)
def _configure_base_token(monkeypatch):
    """Apply the common BaseToken configuration used by most tests."""
    monkeypatch.setattr(_base_token, "_HOSTNAME", "test_host")
    monkeypatch.setattr(_base_token.BaseToken, "algorithm", "HS256")
    monkeypatch.setattr(_base_token.BaseToken, "_secret_key", "test_secret_key")
    monkeypatch.setattr(_base_token.BaseToken, "_issuer", "test_issuer")


def test_basic_token_generation():
    """Test that a token can be generated with valid claims."""
    user_id = uuid7()
    token = _base_token.BaseToken.generate_token(subject=user_id)

    _LOGGER.debug(f"Generated token: {token}")

    # Assert correct types
    assert isinstance(token.token_id, UUID)
    assert isinstance(token.issuer, str)
    assert isinstance(token.audience, str)
    assert isinstance(token.subject, UUID)
    assert isinstance(token.issued_at, int)
    assert isinstance(token.not_before, int)
    assert isinstance(token.expiration, int)

    # Assert correct values
    assert token.issuer == "test_issuer"
    assert token.audience == "test_host"
    assert token.subject == user_id
    assert token.issued_at == token.not_before
    assert token.expiration == token.issued_at + _base_token.BaseToken.time_to_live


def test_token_generation_with_extra_claims(monkeypatch):
    """Test that a token can be generated with valid extra claims."""
    monkeypatch.setattr(_base_token.BaseToken, "allowed_extra_claims", {"role"})

    user_id = uuid7()
    extra_claims = {"role": "admin"}
    token = _base_token.BaseToken.generate_token(subject=user_id, **extra_claims)

    _LOGGER.debug(f"Generated token with extra claims: {token}")

    # Assert correct types
    assert isinstance(token.token_id, UUID)
    assert isinstance(token.issuer, str)
    assert isinstance(token.audience, str)
    assert isinstance(token.subject, UUID)
    assert isinstance(token.issued_at, int)
    assert isinstance(token.not_before, int)
    assert isinstance(token.expiration, int)
    assert isinstance(token.extra_claims["role"], str)

    # Assert correct values
    assert token.issuer == "test_issuer"
    assert token.audience == "test_host"
    assert token.subject == user_id
    assert token.issued_at == token.not_before
    assert token.expiration == token.issued_at + _base_token.BaseToken.time_to_live
    assert token.extra_claims["role"] == "admin"


def test_token_generation_withoutallowed_extra_claims(monkeypatch):
    """Test that a token cannot be generated with extra claims that are not allowed."""
    monkeypatch.setattr(_base_token.BaseToken, "allowed_extra_claims", set())

    user_id = uuid7()
    extra_claims = {"role": "admin"}

    with pytest.raises(ValueError):
        _base_token.BaseToken.generate_token(subject=user_id, **extra_claims)


def test_token_generation_withallowed_extra_claims_but_not_provided(monkeypatch):
    """Test that a token can be generated when allowed extra claims are defined but not provided."""
    monkeypatch.setattr(_base_token.BaseToken, "allowed_extra_claims", {"role"})

    user_id = uuid7()
    token = _base_token.BaseToken.generate_token(subject=user_id)

    _LOGGER.debug(f"Generated token without extra claims: {token}")

    # Assert correct types
    assert isinstance(token.token_id, UUID)
    assert isinstance(token.issuer, str)
    assert isinstance(token.audience, str)
    assert isinstance(token.subject, UUID)
    assert isinstance(token.issued_at, int)
    assert isinstance(token.not_before, int)
    assert isinstance(token.expiration, int)

    # Assert correct values
    assert token.issuer == "test_issuer"
    assert token.audience == "test_host"
    assert token.subject == user_id
    assert token.issued_at == token.not_before
    assert token.expiration == token.issued_at + _base_token.BaseToken.time_to_live


def test_token_generation_differentallowed_extra_claims(monkeypatch):
    """Test that a token cannot be generated with extra claims that are not in the allowed set."""
    monkeypatch.setattr(_base_token.BaseToken, "allowed_extra_claims", {"role"})

    user_id = uuid7()
    extra_claims = {"scope": "read"}

    with pytest.raises(ValueError):
        _base_token.BaseToken.generate_token(subject=user_id, **extra_claims)


def test_token_generation_with_invalid_user_type():
    """Test that a token cannot be generated with an invalid user type."""
    invalid_user = "not-a-uuid"

    with pytest.raises(TypeError):
        _base_token.BaseToken.generate_token(subject=invalid_user)  # type: ignore


def test_token_generation_with_invalid_extra_claims_type(monkeypatch):
    """Test that a token cannot be generated with extra claims that are not strings or ints."""
    monkeypatch.setattr(_base_token.BaseToken, "allowed_extra_claims", {"role"})

    user_id = uuid7()
    invalid_extra_claims = {"role": ["admin"]}  # List instead of str or int

    with pytest.raises(TypeError):
        _base_token.BaseToken.generate_token(subject=user_id, **invalid_extra_claims)  # type: ignore


def test_token_loading():
    """Test that a token can be loaded from a JWT string."""
    user_id = uuid7()
    token = _base_token.BaseToken.generate_token(subject=user_id)
    token_str = str(token)

    loaded_token = _base_token.BaseToken.from_string(token_str)

    _LOGGER.debug(f"Loaded token: {loaded_token}")

    assert isinstance(loaded_token, _base_token.BaseToken)
    assert loaded_token.token_id == token.token_id
    assert loaded_token.issuer == token.issuer
    assert loaded_token.audience == token.audience
    assert loaded_token.subject == token.subject
    assert loaded_token.issued_at == token.issued_at
    assert loaded_token.not_before == token.not_before
    assert loaded_token.expiration == token.expiration
    assert loaded_token.extra_claims == token.extra_claims


def test_token_equality():
    """Test that two tokens with the same claims are equal."""
    user_id = uuid7()
    token1 = _base_token.BaseToken.generate_token(subject=user_id)
    token2 = _base_token.BaseToken.from_string(str(token1))

    assert token1 == token2


def test_token_inequality():
    """Test that two tokens with different claims are not equal."""
    user_id1 = uuid7()
    user_id2 = uuid7()
    token1 = _base_token.BaseToken.generate_token(subject=user_id1)
    token2 = _base_token.BaseToken.generate_token(subject=user_id2)

    assert token1 != token2


def test_token_equality_with_different_types():
    """Test that a token is not equal to an object of a different type."""
    user_id = uuid7()
    token = _base_token.BaseToken.generate_token(subject=user_id)

    assert token != "not-a-token"


def test_loading_token_with_invalid_string():
    """Test that loading a token from an invalid string raises an error."""
    invalid_token_str = "not-a-valid-token"

    with pytest.raises(InvalidTokenError):
        _base_token.BaseToken.from_string(invalid_token_str)


def test_loading_token_with_invalid_signature():
    """Test that loading a token with an invalid signature raises an error."""
    user_id = uuid7()
    token = _base_token.BaseToken.generate_token(subject=user_id)
    token_str = str(token)

    # Tamper with the token string to invalidate the signature
    tampered_token_str = token_str[:-2] + ("aa" if token_str[-2:] != "aa" else "bb")

    with pytest.raises(InvalidTokenError):
        _base_token.BaseToken.from_string(tampered_token_str)


def test_loading_token_with_wrong_issuer():
    """Test that loading a token with the wrong issuer raises an error."""
    token = _base_token.BaseToken(
        token_id=uuid7(),
        issuer="wrong_issuer",
        audience="test_host",
        subject=uuid7(),
        issued_at=int(time()),
        not_before=int(time()),
        expiration=int(time()) + _base_token.BaseToken.time_to_live,
    )
    token_str = str(token)

    with pytest.raises(InvalidTokenError):
        _base_token.BaseToken.from_string(token_str)


def test_loading_token_with_wrong_audience():
    """Test that loading a token with the wrong audience raises an error."""
    token = _base_token.BaseToken(
        token_id=uuid7(),
        issuer="test_issuer",
        audience="wrong_audience",
        subject=uuid7(),
        issued_at=int(time()),
        not_before=int(time()),
        expiration=int(time()) + _base_token.BaseToken.time_to_live,
    )
    token_str = str(token)

    with pytest.raises(InvalidTokenError):
        _base_token.BaseToken.from_string(token_str)


def test_loading_token_with_expired_token():
    """Test that loading an expired token raises an error."""
    token = _base_token.BaseToken(
        token_id=uuid7(),
        issuer="test_issuer",
        audience="test_host",
        subject=uuid7(),
        issued_at=int(time()) - 3600,  # Issued 1 hour ago
        not_before=int(time()) - 3600,  # Valid from 1 hour ago
        expiration=int(time()) - 1800,  # Expired 30 minutes ago
    )
    token_str = str(token)

    with pytest.raises(InvalidTokenError):
        _base_token.BaseToken.from_string(token_str)


def test_loading_token_with_not_yet_valid_token():
    """Test that loading a token that is not yet valid raises an error."""
    token = _base_token.BaseToken(
        token_id=uuid7(),
        issuer="test_issuer",
        audience="test_host",
        subject=uuid7(),
        issued_at=int(time()) + 3600,  # Issued 1 hour in the future
        not_before=int(time()) + 3600,  # Valid from 1 hour in the future
        expiration=int(time()) + 7200,  # Expires in 2 hours
    )
    token_str = str(token)

    with pytest.raises(InvalidTokenError):
        _base_token.BaseToken.from_string(token_str)


def test_loading_token_with_invalid_signature_due_to_wrong_secret_key(monkeypatch):
    """Test that loading a token with an invalid signature due to a wrong secret key raises an error."""
    user_id = uuid7()
    token = _base_token.BaseToken.generate_token(subject=user_id)
    token_str = str(token)

    # Temporarily change the secret key to invalidate the signature
    monkeypatch.setattr(_base_token.BaseToken, "_secret_key", "wrong_secret_key")

    with pytest.raises(InvalidTokenError):
        _base_token.BaseToken.from_string(token_str)


def test_loading_token_with_changed_issuer(monkeypatch):
    """Test that loading a token with a changed issuer claim raises an error."""
    user_id = uuid7()
    token = _base_token.BaseToken.generate_token(subject=user_id)
    token_str = str(token)

    # Temporarily change the issuer claim to invalidate the token
    monkeypatch.setattr(_base_token.BaseToken, "_issuer", "changed_issuer")

    with pytest.raises(InvalidTokenError):
        _base_token.BaseToken.from_string(token_str)


def test_init_with_invalid_token_id_type():
    """Test that __init__ raises TypeError when token_id is not a UUID."""
    with pytest.raises(TypeError):
        _base_token.BaseToken(
            token_id="not-a-uuid",  # type: ignore
            issuer="test_issuer",
            audience="test_host",
            subject=uuid7(),
            issued_at=int(time()),
            not_before=int(time()),
            expiration=int(time()) + 3600,
        )


def test_init_with_invalid_issuer_type():
    """Test that __init__ raises TypeError when issuer is not a string."""
    with pytest.raises(TypeError):
        _base_token.BaseToken(
            token_id=uuid7(),
            issuer=123,  # type: ignore
            audience="test_host",
            subject=uuid7(),
            issued_at=int(time()),
            not_before=int(time()),
            expiration=int(time()) + 3600,
        )


def test_init_with_invalid_audience_type():
    """Test that __init__ raises TypeError when audience is not a string."""
    with pytest.raises(TypeError):
        _base_token.BaseToken(
            token_id=uuid7(),
            issuer="test_issuer",
            audience=123,  # type: ignore
            subject=uuid7(),
            issued_at=int(time()),
            not_before=int(time()),
            expiration=int(time()) + 3600,
        )


def test_init_with_invalid_subject_type():
    """Test that __init__ raises TypeError when subject is not a UUID."""
    with pytest.raises(TypeError):
        _base_token.BaseToken(
            token_id=uuid7(),
            issuer="test_issuer",
            audience="test_host",
            subject="not-a-uuid",  # type: ignore
            issued_at=int(time()),
            not_before=int(time()),
            expiration=int(time()) + 3600,
        )


def test_init_with_negative_issued_at():
    """Test that __init__ raises TypeError when issued_at is negative."""
    with pytest.raises(TypeError):
        _base_token.BaseToken(
            token_id=uuid7(),
            issuer="test_issuer",
            audience="test_host",
            subject=uuid7(),
            issued_at=-1,
            not_before=int(time()),
            expiration=int(time()) + 3600,
        )


def test_init_with_invalid_issued_at_type():
    """Test that __init__ raises TypeError when issued_at is not an integer."""
    with pytest.raises(TypeError):
        _base_token.BaseToken(
            token_id=uuid7(),
            issuer="test_issuer",
            audience="test_host",
            subject=uuid7(),
            issued_at="not-an-int",  # type: ignore
            not_before=int(time()),
            expiration=int(time()) + 3600,
        )


def test_init_with_negative_not_before():
    """Test that __init__ raises TypeError when not_before is negative."""
    with pytest.raises(TypeError):
        _base_token.BaseToken(
            token_id=uuid7(),
            issuer="test_issuer",
            audience="test_host",
            subject=uuid7(),
            issued_at=int(time()),
            not_before=-1,
            expiration=int(time()) + 3600,
        )


def test_init_with_negative_expiration():
    """Test that __init__ raises TypeError when expiration is negative."""
    with pytest.raises(TypeError):
        _base_token.BaseToken(
            token_id=uuid7(),
            issuer="test_issuer",
            audience="test_host",
            subject=uuid7(),
            issued_at=int(time()),
            not_before=int(time()),
            expiration=-1,
        )


def test_init_with_extra_claims_not_in_allowed_set(monkeypatch):
    """Test that __init__ raises ValueError when extra claims contain disallowed keys."""
    monkeypatch.setattr(_base_token.BaseToken, "allowed_extra_claims", {"role"})

    with pytest.raises(ValueError):
        _base_token.BaseToken(
            token_id=uuid7(),
            issuer="test_issuer",
            audience="test_host",
            subject=uuid7(),
            issued_at=int(time()),
            not_before=int(time()),
            expiration=int(time()) + 3600,
            scope="read",  # type: ignore
        )


def test_init_with_invalid_extra_claim_value_type(monkeypatch):
    """Test that __init__ raises TypeError when extra claim values are not strings or ints."""
    monkeypatch.setattr(_base_token.BaseToken, "allowed_extra_claims", {"role"})

    with pytest.raises(TypeError):
        _base_token.BaseToken(
            token_id=uuid7(),
            issuer="test_issuer",
            audience="test_host",
            subject=uuid7(),
            issued_at=int(time()),
            not_before=int(time()),
            expiration=int(time()) + 3600,
            role=["admin"],  # type: ignore
        )


def test_from_string_with_invalid_type():
    """Test that from_string raises TypeError when given a non-string/bytes value."""
    with pytest.raises(TypeError):
        _base_token.BaseToken.from_string(12345)  # type: ignore


def test_from_string_with_negative_leeway():
    """Test that from_string raises ValueError when leeway is negative."""
    with pytest.raises(ValueError):
        _base_token.BaseToken.from_string("some.token.string", leeway=-1)


def test_from_string_with_bytes_input():
    """Test that from_string accepts bytes as well as str."""
    user_id = uuid7()
    token = _base_token.BaseToken.generate_token(subject=user_id)
    token_bytes = str(token).encode()

    loaded_token = _base_token.BaseToken.from_string(token_bytes)

    assert loaded_token == token


def test_from_string_with_leeway_allows_recently_expired_token():
    """Test that a recently expired token is accepted when a sufficient leeway is provided."""
    token = _base_token.BaseToken(
        token_id=uuid7(),
        issuer="test_issuer",
        audience="test_host",
        subject=uuid7(),
        issued_at=int(time()) - 120,
        not_before=int(time()) - 120,
        expiration=int(time()) - 30,  # Expired 30 seconds ago
    )
    token_str = str(token)

    # 60-second leeway should allow a token that expired 30 seconds ago
    loaded_token = _base_token.BaseToken.from_string(token_str, leeway=60)

    assert isinstance(loaded_token, _base_token.BaseToken)


def test_generate_token_produces_unique_token_ids():
    """Test that each generated token has a unique token_id."""
    user_id = uuid7()
    token1 = _base_token.BaseToken.generate_token(subject=user_id)
    token2 = _base_token.BaseToken.generate_token(subject=user_id)

    assert token1.token_id != token2.token_id


def test_str_returns_non_empty_string():
    """Test that str(token) returns a non-empty JWT string."""
    token = _base_token.BaseToken.generate_token(subject=uuid7())
    token_str = str(token)

    assert isinstance(token_str, str)
    assert len(token_str) > 0
