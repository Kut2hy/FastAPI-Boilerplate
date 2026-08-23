from piccolo.apps.migrations.auto.migration_manager import MigrationManager
from piccolo.columns.base import OnDelete, OnUpdate
from piccolo.columns.column_types import UUID, Array, BigInt, Boolean, ForeignKey, Integer, Secret, Timestamptz, Varchar
from piccolo.columns.defaults.timestamptz import TimestamptzNow
from piccolo.columns.defaults.uuid import UUID7
from piccolo.columns.indexes import IndexMethod
from piccolo.constraints import Check, Unique
from piccolo.table import Table


class UserAccount(Table, tablename="user_account", schema=None):
    id = UUID(
        default=UUID7(),
        null=False,
        primary_key=True,
        unique=False,
        index=False,
        index_method=IndexMethod.btree,
        choices=None,
        db_column_name=None,
        secret=False,
    )


ID = "2026-08-16T16:19:58:269494"
VERSION = "1.36.0"
DESCRIPTION = ""


async def forwards():
    manager = MigrationManager(
        migration_id=ID, app_name="app", description=DESCRIPTION
    )

    manager.add_table(
        class_name="UserAccount",
        tablename="user_account",
        schema=None,
        columns=None,
    )

    manager.add_table(
        class_name="LoginAttempt",
        tablename="login_attempt",
        schema=None,
        columns=None,
    )

    manager.add_table(
        class_name="RefreshToken",
        tablename="refresh_token",
        schema=None,
        columns=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="was_reviewed",
        db_column_name="was_reviewed",
        column_class_name="Boolean",
        column_class=Boolean,
        params={
            "default": False,
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="updated_by",
        db_column_name="updated_by",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": UserAccount,
            "on_delete": OnDelete.set_null,
            "on_update": OnUpdate.cascade,
            "target_column": "id",
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": True,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="updated_at",
        db_column_name="updated_at",
        column_class_name="Timestamptz",
        column_class=Timestamptz,
        params={
            "default": TimestamptzNow(),
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="created_by",
        db_column_name="created_by",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": UserAccount,
            "on_delete": OnDelete.set_null,
            "on_update": OnUpdate.cascade,
            "target_column": "id",
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": True,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="created_at",
        db_column_name="created_at",
        column_class_name="Timestamptz",
        column_class=Timestamptz,
        params={
            "default": TimestamptzNow(),
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="id",
        db_column_name="id",
        column_class_name="UUID",
        column_class=UUID,
        params={
            "default": UUID7(),
            "null": False,
            "primary_key": True,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="email",
        db_column_name="email",
        column_class_name="Secret",
        column_class=Secret,
        params={
            "length": 255,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": True,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": True,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="user_alias",
        db_column_name="user_alias",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 50,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": True,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="receive_notifications",
        db_column_name="receive_notifications",
        column_class_name="Boolean",
        column_class=Boolean,
        params={
            "default": True,
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="password_hash",
        db_column_name="password_hash",
        column_class_name="Secret",
        column_class=Secret,
        params={
            "length": 255,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": True,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="granted_roles",
        db_column_name="granted_roles",
        column_class_name="Array",
        column_class=Array,
        params={
            "default": list,
            "base_column": Varchar(
                length=50,
                default="",
                null=False,
                primary_key=False,
                unique=False,
                index=False,
                index_method=IndexMethod.btree,
                choices=None,
                db_column_name=None,
                secret=False,
            ),
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="is_locked",
        db_column_name="is_locked",
        column_class_name="Boolean",
        column_class=Boolean,
        params={
            "default": False,
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="was_email_verified",
        db_column_name="was_email_verified",
        column_class_name="Boolean",
        column_class=Boolean,
        params={
            "default": False,
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="first_name",
        db_column_name="first_name",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 50,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="middle_name",
        db_column_name="middle_name",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 50,
            "default": None,
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="last_name",
        db_column_name="last_name",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 50,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="titles_before",
        db_column_name="titles_before",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 50,
            "default": None,
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="titles_after",
        db_column_name="titles_after",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 50,
            "default": None,
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="phone_number",
        db_column_name="phone_number",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 50,
            "default": None,
            "null": True,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="street",
        db_column_name="street",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 255,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="city",
        db_column_name="city",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 50,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="postal_code",
        db_column_name="postal_code",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 5,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="UserAccount",
        tablename="user_account",
        column_name="country",
        db_column_name="country",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 2,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="LoginAttempt",
        tablename="login_attempt",
        column_name="id",
        db_column_name="id",
        column_class_name="UUID",
        column_class=UUID,
        params={
            "default": UUID7(),
            "null": False,
            "primary_key": True,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="LoginAttempt",
        tablename="login_attempt",
        column_name="created_at",
        db_column_name="created_at",
        column_class_name="Timestamptz",
        column_class=Timestamptz,
        params={
            "default": TimestamptzNow(),
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="LoginAttempt",
        tablename="login_attempt",
        column_name="user_email",
        db_column_name="user_email",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 255,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": True,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="LoginAttempt",
        tablename="login_attempt",
        column_name="user_ip_address",
        db_column_name="user_ip_address",
        column_class_name="Varchar",
        column_class=Varchar,
        params={
            "length": 45,
            "default": "",
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="LoginAttempt",
        tablename="login_attempt",
        column_name="was_successful",
        db_column_name="was_successful",
        column_class_name="Boolean",
        column_class=Boolean,
        params={
            "default": False,
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": True,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="LoginAttempt",
        tablename="login_attempt",
        column_name="status_code",
        db_column_name="status_code",
        column_class_name="Integer",
        column_class=Integer,
        params={
            "default": 0,
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="RefreshToken",
        tablename="refresh_token",
        column_name="id",
        db_column_name="id",
        column_class_name="UUID",
        column_class=UUID,
        params={
            "default": UUID7(),
            "null": False,
            "primary_key": True,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="RefreshToken",
        tablename="refresh_token",
        column_name="created_at",
        db_column_name="created_at",
        column_class_name="Timestamptz",
        column_class=Timestamptz,
        params={
            "default": TimestamptzNow(),
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="RefreshToken",
        tablename="refresh_token",
        column_name="user_id",
        db_column_name="user_id",
        column_class_name="ForeignKey",
        column_class=ForeignKey,
        params={
            "references": UserAccount,
            "on_delete": OnDelete.cascade,
            "on_update": OnUpdate.cascade,
            "target_column": None,
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": True,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="RefreshToken",
        tablename="refresh_token",
        column_name="issued_at",
        db_column_name="issued_at",
        column_class_name="BigInt",
        column_class=BigInt,
        params={
            "default": 0,
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="RefreshToken",
        tablename="refresh_token",
        column_name="expires_at",
        db_column_name="expires_at",
        column_class_name="BigInt",
        column_class=BigInt,
        params={
            "default": 0,
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_column(
        table_class_name="RefreshToken",
        tablename="refresh_token",
        column_name="was_revoked",
        db_column_name="was_revoked",
        column_class_name="Boolean",
        column_class=Boolean,
        params={
            "default": False,
            "null": False,
            "primary_key": False,
            "unique": False,
            "index": False,
            "index_method": IndexMethod.btree,
            "choices": None,
            "db_column_name": None,
            "secret": False,
        },
        schema=None,
    )

    manager.add_constraint(
        table_class_name="UserAccount",
        tablename="user_account",
        constraint_name="unique_email_user_alias",
        constraint_class=Unique,
        params={"columns": ["email", "user_alias"], "nulls_distinct": True},
        schema=None,
    )

    manager.add_constraint(
        table_class_name="RefreshToken",
        tablename="refresh_token",
        constraint_name="unique_id_user_id",
        constraint_class=Unique,
        params={"columns": ["id", "user_id"], "nulls_distinct": True},
        schema=None,
    )

    manager.add_constraint(
        table_class_name="RefreshToken",
        tablename="refresh_token",
        constraint_name="check_positive_issued_at",
        constraint_class=Check,
        params={"condition": "issued_at > 0"},
        schema=None,
    )

    manager.add_constraint(
        table_class_name="RefreshToken",
        tablename="refresh_token",
        constraint_name="check_positive_expires_at",
        constraint_class=Check,
        params={"condition": "expires_at > 0"},
        schema=None,
    )

    manager.add_constraint(
        table_class_name="RefreshToken",
        tablename="refresh_token",
        constraint_name="check_expiration",
        constraint_class=Check,
        params={"condition": "expires_at > issued_at"},
        schema=None,
    )

    return manager
