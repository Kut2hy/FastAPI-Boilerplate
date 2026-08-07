"""Piccolo table for persisting JWT refresh tokens."""

from piccolo.columns import (
    BigInt,
    ForeignKey,
    OnDelete,
    OnUpdate,
)
from piccolo.columns.reference import LazyTableReference
from piccolo.constraints import Check, Unique
from piccolo.table import Table

from app.piccolo.mixins import CreatedAtMixin, PKMixin


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
