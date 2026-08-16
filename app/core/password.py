"""Password security functions for hashing and verification."""

from random import choice
from string import ascii_lowercase, digits
from logging import getLogger

from argon2 import PasswordHasher
from argon2.exceptions import HashingError, InvalidHashError, VerificationError, VerifyMismatchError
from argon2.profiles import RFC_9106_LOW_MEMORY

_PASSWORD_HASHER = PasswordHasher(
    time_cost=RFC_9106_LOW_MEMORY.time_cost,
    memory_cost=RFC_9106_LOW_MEMORY.memory_cost,
    parallelism=RFC_9106_LOW_MEMORY.parallelism,
    hash_len=RFC_9106_LOW_MEMORY.hash_len,
    salt_len=RFC_9106_LOW_MEMORY.salt_len,
    type=RFC_9106_LOW_MEMORY.type,
)
"""Instance of Argon2 PasswordHasher for hashing and verifying passwords."""

_ALPHANUMERIC_CHARACTERS = ascii_lowercase + digits
"""Alphanumeric characters used for generating one-time verification codes."""


_LOGGER = getLogger(__name__)
"""Logger for the passwords module."""


def hash_password(plain_password: str | bytes) -> str:
    """Hashes a plain text password using Argon2 algorithm.

    :param plain_password: The plain text password to hash.

    :raise TypeError: If the input type is incorrect.
    :raise HashingError: If hashing fails for any reason.

    :return: The hashed password.
    """
    try:
        if not isinstance(plain_password, (str, bytes)):
            raise TypeError("Password must be a string or bytes.")

        if isinstance(plain_password, bytes):
            plain_password = plain_password.decode("utf-8")

        return _PASSWORD_HASHER.hash(plain_password)

    except TypeError:
        _LOGGER.exception("Type error during hashing")
        raise

    except HashingError:
        _LOGGER.exception("Hashing error")
        raise

    except Exception:
        _LOGGER.exception("Unexpected error during hashing")
        raise


def verify_password(plain_password: str | bytes, password_hash: str) -> bool:
    """Verify a plain password against a hashed password.

    Function does not access DB; it only verifies the provided inputs.

    :param plain_password: The plain text password to verify.
    :param password_hash: The hashed password to verify against.

    :raise TypeError: If input types are incorrect.
    :raise VerificationError: If verification fails for reasons other than mismatch.
    :raise InvalidHashError: If the provided hash is invalid.
    :raise Exception: For any other exceptions that may occur during verification.

    :return: True if the password matches, False otherwise.
    """
    try:
        if not isinstance(plain_password, (str, bytes)):
            raise TypeError("Password must be a string or bytes.")

        if isinstance(plain_password, bytes):
            plain_password = plain_password.decode("utf-8")

        if not isinstance(password_hash, str):
            raise TypeError("Password hash must be a string.")

        return _PASSWORD_HASHER.verify(hash=password_hash, password=plain_password)

    except VerifyMismatchError:
        # Password does not match
        return False

    except TypeError:
        _LOGGER.exception("Type error during verification")
        raise

    except (VerificationError, InvalidHashError):
        _LOGGER.exception("Verification error")
        raise

    except Exception:
        _LOGGER.exception("Unexpected error during verification")
        raise


def generate_one_time_verification_code() -> str:
    """Generate a one-time verification code for email validation during registration.

    Returns:
        str: A randomly generated one-time verification code.
            Example format: 'a1b2-c3d4-e5f6' (3 groups of 4 characters separated by hyphens).

    """
    def _generate_group() -> str:
        return "".join(choice(_ALPHANUMERIC_CHARACTERS) for _ in range(4))  # noqa: S311 -> Simple random is acceptable for generating non-security-critical codes.

    return "-".join([_generate_group() for _ in range(3)])


if __name__ == "__main__":
    # For testing purposes
    print(hash_password("Aa@1111111"))
