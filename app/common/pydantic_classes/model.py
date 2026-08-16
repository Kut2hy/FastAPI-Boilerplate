"""Extensions for Pydantic base model."""

from typing import TYPE_CHECKING, Any, Literal

from pydantic import BaseModel, ConfigDict, Secret

if TYPE_CHECKING:
    from collections.abc import Callable

    from pydantic.main import IncEx


class InputModel(BaseModel):
    """Base model for input data."""

    model_config = ConfigDict(
        extra="forbid",
    )

    def model_dump_table(
        self,
        *,
        include: IncEx | None = None,
        exclude: IncEx | None = None,
        context: Any | None = None,  # noqa: ANN401 -> Used same as Pydantic's model_dump() method
        by_alias: bool | None = None,
        exclude_unset: bool = True,  # NOTE: Override default to True -> prevents updates on unset fields.
        exclude_defaults: bool = False,
        exclude_none: bool = True,  # NOTE: Override default to True -> avoid storing nullish values in the database.
        exclude_computed_fields: bool = False,
        round_trip: bool = False,
        warnings: bool | Literal["none", "warn", "error"] = True,
        fallback: Callable[[Any], Any] | None = None,
        serialize_as_any: bool = False,
        polymorphic_serialization: bool | None = None,
    ) -> dict[str, Any]:
        """Generate a dictionary representation of the model, optionally specifying which fields to include or exclude.

        This is a wrapper around Pydantic's `model_dump()` method, with additional Secret handling.
        Method should be only used for direct dump into write methods of the database tables.
        Logging output of this method is not recommended, as it may contain sensitive information.

        Args:
            include: A set of fields to include in the output.

            exclude: A set of fields to exclude from the output.

            context: Additional context to pass to the serializer.

            by_alias: Whether to use the field's alias in the dictionary key if defined.

            exclude_unset: Whether to exclude fields that have not been explicitly set.

            exclude_defaults: Whether to exclude fields that are set to their default value.

            exclude_none: Whether to exclude fields that have a value of `None`.

            exclude_computed_fields: Whether to exclude computed fields.
                While this can be useful for round-tripping, it is usually recommended to use the dedicated
                `round_trip` parameter instead.

            round_trip: If True, dumped values should be valid as input for non-idempotent types such as Json[T].

            warnings: How to handle serialization errors. False/"none" ignores them, True/"warn" logs errors,
                "error" raises a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError].

            fallback: A function to call when an unknown value is encountered. If not provided,
                a [`PydanticSerializationError`][pydantic_core.PydanticSerializationError] error is raised.

            serialize_as_any: Whether to serialize fields with duck-typing serialization behavior.

            polymorphic_serialization: Whether to use model and dataclass polymorphic serialization for this call.

        Returns:
            A dictionary representation of the model.

        """
        data = self.model_dump(
            mode="python",
            include=include,
            exclude=exclude,
            context=context,
            by_alias=by_alias,
            exclude_unset=exclude_unset,
            exclude_defaults=exclude_defaults,
            exclude_none=exclude_none,
            exclude_computed_fields=exclude_computed_fields,
            round_trip=round_trip,
            warnings=warnings,
            fallback=fallback,
            serialize_as_any=serialize_as_any,
            polymorphic_serialization=polymorphic_serialization,
        )

        return {key: value.get_secret_value() if isinstance(value, Secret) else value for key, value in data.items()}
