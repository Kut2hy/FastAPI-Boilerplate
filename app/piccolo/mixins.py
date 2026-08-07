"""Module containing mixin classes that can be used to add common columns to Piccolo Tables."""

from datetime import datetime

from piccolo.columns import OnDelete, OnUpdate
from piccolo.columns.column_types import UUID, Boolean, ForeignKey, Timestamptz
from piccolo.columns.defaults import UUID4, TimestamptzNow
from piccolo.columns.reference import LazyTableReference

USER_ACCOUNT_CLASS_NAME = "UserAccount"
"""Class name of the UserAccount table, used for foreign key references in mixins."""

USER_ACCOUNT_MODULE_PATH = "app.piccolo.tables.user_account"
"""Module path of the UserAccount table, used for foreign key references in mixins."""


class PKMixin:
    """Mixin utility class to add a UUID primary key column to a Table.

    Has a default value of a new UUID.
    """

    id = UUID(
        primary_key=True,
        default=UUID4(),
        null=False,
    )
    """Primary key column with a UUID value."""


class UpdatedAtMixin:
    """Mixin utility class to add an updated_at column to a Table.

    Has a default value of the current timestamp.
    """

    updated_at = Timestamptz(
        default=TimestamptzNow(),
        auto_update=datetime.now,
        null=True,
    )
    """Column to store the timestamp of the last update."""


class UpdatedByMixin:
    """Mixin utility class to add an updated_by column to a Table.

    This column is a foreign key referencing the UserAccount table.
    It is intended to store the ID of the user who last updated the record.
    """

    updated_by = ForeignKey(
        references=LazyTableReference(
            USER_ACCOUNT_CLASS_NAME,
            module_path=USER_ACCOUNT_MODULE_PATH,
        ),
        target_column="id",
        null=True,
        index=True,
        on_delete=OnDelete.set_null,
        on_update=OnUpdate.cascade,
    )
    """Foreign key column referencing the UserAccount table, indicating who last updated the record."""


class CreatedAtMixin:
    """Mixin utility class to add a created_at column to a Table.

    Has a default value of the current timestamp.
    No auto_update, so the value won't change after the record is created.
    """

    created_at = Timestamptz(
        default=TimestamptzNow(),
        null=False,
    )
    """Column to store the timestamp of when the record was created. Set on record creation and does not change."""


class CreatedByMixin:
    """Mixin utility class to add a created_by column to a Table.

    This column is a foreign key referencing the UserAccount table.
    It is intended to store the ID of the user who created the record.
    """

    created_by = ForeignKey(
        references=LazyTableReference(
            USER_ACCOUNT_CLASS_NAME,
            module_path=USER_ACCOUNT_MODULE_PATH,
        ),
        target_column="id",
        null=True,
        index=True,
        on_delete=OnDelete.set_null,
        on_update=OnUpdate.cascade,
    )
    """Foreign key column referencing the UserAccount table, indicating who created the record."""


class IsPublicMixin:
    """Mixin utility class to add an is_public column to a Table.

    This column is a boolean indicating whether the record is public.
    """

    is_public = Boolean(
        default=False,
        null=False,
    )
    """Boolean column indicating whether the record is public."""


class PublishAtMixin:
    """Mixin utility class to add a publish_at column to a Table.

    This column is a timestamp indicating when the record was published.
    """

    publish_at = Timestamptz(
        default=TimestamptzNow(),
        null=False,
    )
    """
    Timestamp column indicating when the record was published or will be published.
    Set on record creation and does not change unless explicitly updated.
    """


class WasReviewedMixin:
    """Mixin utility class to add a was_reviewed column to a Table.

    This column is a boolean indicating whether the record has been validated.
    """

    was_reviewed = Boolean(
        default=False,
        null=False,
    )
    """Boolean column indicating whether the record has been reviewed."""
