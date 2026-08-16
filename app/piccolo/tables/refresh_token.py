"""Piccolo table for persisting JWT refresh tokens."""

from time import time
from uuid import UUID

from piccolo.columns import (
    BigInt,
    Boolean,
    ForeignKey,
    OnDelete,
    OnUpdate,
)
from piccolo.columns.reference import LazyTableReference
from piccolo.constraints import Check, Unique
from piccolo.table import Table

from app.piccolo.mixins import CreatedAtMixin, PKMixin
from app.core.jwt.refresh_token import RefreshToken as JWTRefreshToken
from app.core.jwt.access_token import AccessToken as JWTAccessToken
from app.piccolo.tables.user_account import UserAccount


class RefreshToken(CreatedAtMixin, PKMixin, Table):
    """SQL table for storing JWT refresh tokens."""

    user_id = ForeignKey(
        references=LazyTableReference("UserAccount", module_path="app.piccolo.tables.user_account"),
        on_delete=OnDelete.cascade,
        on_update=OnUpdate.cascade,
        null=False,
        index=True,
    )
    """User ID associated with the token. This is a foreign key to the User table."""

    issued_at = BigInt(null=False)
    """Epoch time indicating when the token was generated. Matches value from JWT `iat` claim."""

    expires_at = BigInt(null=False)
    """Epoch time indicating when the token will expire. Matches value from JWT `exp` claim."""

    was_revoked = Boolean(null=False, default=False)
    """Indicates whether the token was revoked. Defaults to False."""

    # ==================================================================================================================
    # Constraints
    # ==================================================================================================================

    unique_id_user_id = Unique(columns=["id", "user_id"], name="unique_id_user_id")
    """Unique constraint to ensure that the combination of token ID and user ID is unique."""

    check_positive_issued_at = Check(condition="issued_at > 0", name="check_positive_issued_at")
    """Check constraint to ensure that the issued time is a positive value."""

    check_positive_expires_at = Check(condition="expires_at > 0", name="check_positive_expires_at")
    """Check constraint to ensure that the expiration time is a positive value."""

    check_expiration = Check(condition="expires_at > issued_at", name="check_expiration")
    """Check constraint to ensure that the expiration time is greater than the issued time."""


async def add_refresh_token(
    token: JWTRefreshToken,
) -> bool:
    async with RefreshToken._meta.db.transaction():  # noqa: SLF001
        result = (
            await RefreshToken(
                {
                    RefreshToken.id: token.token_id,
                    RefreshToken.user_id: token.subject,
                    RefreshToken.issued_at: token.issued_at,
                    RefreshToken.expires_at: token.expiration,
                }
            )
            .save()
            .returning(RefreshToken.id)
        )

        return bool(result)


async def delete_refresh_token(token: JWTRefreshToken) -> bool:
    async with RefreshToken._meta.db.transaction():  # noqa: SLF001
        result = (
            await RefreshToken.delete()
            .where(RefreshToken.id == token.token_id)
            .returning(RefreshToken.id)
        )

        return bool(result)


async def regenerate_access_token(token: JWTRefreshToken) -> JWTAccessToken | None:

    async with RefreshToken._meta.db.transaction():  # noqa: SLF001
        existing_token = (
            await RefreshToken.objects(RefreshToken.user_id)
            .where(
                (RefreshToken.id == token.token_id)
                & (RefreshToken.user_id == token.subject)
                & (RefreshToken.was_revoked == False)  # noqa: E712
                & (RefreshToken.expires_at > int(time()))
            )
            .lock_rows(of=(RefreshToken,))
            .first()
        )

        if not existing_token:
            return None

        # Generate new access and refresh tokens
        return JWTAccessToken.generate_token(
            subject=token.subject,
            alias=existing_token.user_id.user_alias,
            roles=",".join(existing_token.user_id.granted_roles),
        )
