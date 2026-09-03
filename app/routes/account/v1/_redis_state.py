"""Module for validating Redis state against Pydantic models."""

from pydantic import ValidationError

from ._shared_models import (
    AfterAccountInfoState,
    AfterAliasState,
    AfterClickThroughState,
    AfterCreationState,
)

CompositeStateModels = AfterCreationState | AfterClickThroughState | AfterAliasState | AfterAccountInfoState


def validate_redis_state[T: CompositeStateModels](
    redis_state: dict | None,
    model_class: type[T],
) -> T | None:
    """Validate the Redis state against the given Pydantic model class.

    Args:
        redis_state (dict | None): The Redis state to validate.
        model_class (type[T]): The Pydantic model class to validate against.

    Returns:
        T | None: The validated model instance if the Redis state is valid according to the model class,
            or None if the Redis state is None or invalid.

    """
    if redis_state is None:
        return None

    try:
        return model_class.model_validate(redis_state)

    except ValidationError:
        return None
