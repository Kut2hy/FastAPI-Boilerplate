"""PyTest unit tests for redis_funcs.py."""

import asyncio
import os

import pytest
import pytest_asyncio
from redis.asyncio import Redis
from redis.asyncio.retry import Retry
from redis.backoff import NoBackoff

from app.core.redis.functions import (
    create_hash_object,
    delete_object,
    get_hash_object,
    hash_object_exists,
    increment_hash_field,
    update_hash_object,
)

pytestmark = pytest.mark.asyncio

MOCK_HASH_KEY = "test_hash"
MOCK_HASH = {"field1": "value1", "field2": "value2"}
MOCK_EXPIRE_SECONDS = 10


@pytest_asyncio.fixture
async def redis_client():  # noqa: ANN202
    """Create a Redis client for testing."""
    client = Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=int(os.getenv("REDIS_PORT", "6379")),
        db=15,  # Use separate DB for tests
        decode_responses=True,
    )

    # Verify connection
    await client.ping()

    yield client

    # Cleanup after all tests
    await client.flushdb()
    await client.aclose()


@pytest_asyncio.fixture(autouse=True)
async def clean_redis(redis_client: Redis) -> None:
    """Clean Redis before each test."""
    await redis_client.flushdb()


async def test_can_connect(redis_client: Redis) -> None:
    await redis_client.set("ping", "pong")
    assert await redis_client.get("ping") == "pong"


async def test_hash_exists(redis_client: Redis) -> None:
    """Test validates that the hash_exists function correctly identifies the existence of a hash in Redis."""
    await redis_client.hset(MOCK_HASH_KEY, mapping=MOCK_HASH)  # type: ignore

    # Verify that the hash exists
    assert await hash_object_exists(redis_client, MOCK_HASH_KEY) is True

    # Verify that a non-existent hash does not exist
    assert await hash_object_exists(redis_client, "non_existent_hash") is False


async def test_hash_exists_ttl(redis_client: Redis) -> None:
    """Test validates that the hash_exists function correctly identifies the existence of a hash in Redis with TTL."""
    await redis_client.hset(MOCK_HASH_KEY, mapping=MOCK_HASH)  # type: ignore
    await redis_client.expire(MOCK_HASH_KEY, 1)  # Set TTL to 1 second

    # Verify that the hash exists
    assert await hash_object_exists(redis_client, MOCK_HASH_KEY) is True

    # Wait for the TTL to expire
    await asyncio.sleep(1.1)

    # Verify that the hash no longer exists
    assert await hash_object_exists(redis_client, MOCK_HASH_KEY) is False


async def test_create_hash_object(redis_client: Redis) -> None:
    """Test that create_hash_object sets a hash in Redis with an expiration time."""
    # Call the function to set the hash
    if not await create_hash_object(redis_client, MOCK_HASH_KEY, MOCK_HASH, MOCK_EXPIRE_SECONDS):
        pytest.fail("Failed to set hash in Redis")

    # Verify that the hash was set correctly
    stored_mapping = await redis_client.hgetall(MOCK_HASH_KEY)
    assert stored_mapping == MOCK_HASH

    # Verify that the expiration time is set
    ttl = await redis_client.ttl(MOCK_HASH_KEY)
    assert 0 < ttl <= MOCK_EXPIRE_SECONDS


async def test_create_hash_object_failure() -> None:
    """Test that create_hash_object returns False when Redis is unreachable."""
    # Point at a port where nothing is listening so the connection genuinely fails.
    unreachable_client = Redis(
        host="localhost",
        port=6390,
        db=15,
        decode_responses=True,
        socket_connect_timeout=1,
        retry=Retry(NoBackoff(), retries=0),
    )

    try:
        # Call the function to set the hash, expecting it to fail
        result = await create_hash_object(unreachable_client, MOCK_HASH_KEY, MOCK_HASH, MOCK_EXPIRE_SECONDS)

        # Verify that the function returned False due to the failure
        assert result is False

    finally:
        await unreachable_client.aclose()


async def test_update_hash_object(redis_client: Redis) -> None:
    # Call the function to set the hash
    if not await create_hash_object(redis_client, MOCK_HASH_KEY, MOCK_HASH, MOCK_EXPIRE_SECONDS):
        pytest.fail("Failed to set hash in Redis")

    # Update the hash with new values
    updated_mapping = {"field1": "new_value1", "field3": "value3"}

    if not await update_hash_object(redis_client, MOCK_HASH_KEY, updated_mapping, MOCK_EXPIRE_SECONDS * 10):
        pytest.fail("Failed to update hash in Redis")

    # Verify that the hash was updated correctly
    stored_mapping = await redis_client.hgetall(MOCK_HASH_KEY)

    expected_mapping = {"field1": "new_value1", "field2": "value2", "field3": "value3"}
    assert stored_mapping == expected_mapping

    await asyncio.sleep(1.1)  # Allow some time for the expiration to be set

    # Verify that the expiration time was updated correctly
    ttl = await redis_client.ttl(MOCK_HASH_KEY)
    assert MOCK_EXPIRE_SECONDS < ttl <= MOCK_EXPIRE_SECONDS * 10


async def test_add_hash_field(redis_client: Redis) -> None:
    # Call the function to set the hash
    if not await create_hash_object(redis_client, MOCK_HASH_KEY, MOCK_HASH, MOCK_EXPIRE_SECONDS):
        pytest.fail("Failed to set hash in Redis")

    # Add a new field to the hash
    new_field = "field3"
    new_value = "value3"

    if not await update_hash_object(redis_client, MOCK_HASH_KEY, {new_field: new_value}, MOCK_EXPIRE_SECONDS * 10):
        pytest.fail("Failed to add new field to hash in Redis")

    # Verify that the new field was added correctly
    stored_mapping = await redis_client.hgetall(MOCK_HASH_KEY)

    expected_mapping = {"field1": "value1", "field2": "value2", "field3": "value3"}
    assert stored_mapping == expected_mapping

    await asyncio.sleep(1.1)  # Allow some time for the expiration to be set

    # Verify that the expiration time was updated correctly
    ttl = await redis_client.ttl(MOCK_HASH_KEY)
    assert MOCK_EXPIRE_SECONDS < ttl <= MOCK_EXPIRE_SECONDS * 10


async def test_add_to_counter(redis_client: Redis) -> None:
    # Increment a field in the hash
    field_to_increment = "field1"
    increment_amount = 2

    # Call the function to set the hash
    if not await create_hash_object(redis_client, MOCK_HASH_KEY, {field_to_increment: 1}, MOCK_EXPIRE_SECONDS):
        pytest.fail("Failed to set hash in Redis")

    # Increment the field in the hash by amount, no expiration update
    if not await increment_hash_field(redis_client, MOCK_HASH_KEY, field_to_increment, increment_amount):
        pytest.fail("Failed to increment hash field in Redis")

    # Verify that the field was incremented correctly
    stored_mapping = await redis_client.hgetall(MOCK_HASH_KEY)
    expected_value = str(1 + increment_amount)

    assert stored_mapping[field_to_increment] == expected_value

    # Verify that the expiration time was updated correctly
    ttl = await redis_client.ttl(MOCK_HASH_KEY)
    assert 0 < ttl <= MOCK_EXPIRE_SECONDS

    # Increment the field in the hash by amount, with expiration update
    if not await increment_hash_field(
        redis_client, MOCK_HASH_KEY, field_to_increment, increment_amount, MOCK_EXPIRE_SECONDS * 10
    ):
        pytest.fail("Failed to increment hash field in Redis")

    # Verify that the field was incremented correctly
    stored_mapping = await redis_client.hgetall(MOCK_HASH_KEY)
    expected_value = str(int(expected_value) + increment_amount)

    assert stored_mapping[field_to_increment] == expected_value

    # Verify that the expiration time was updated correctly
    ttl = await redis_client.ttl(MOCK_HASH_KEY)
    assert MOCK_EXPIRE_SECONDS < ttl <= MOCK_EXPIRE_SECONDS * 10


async def test_get_hash_object(redis_client: Redis) -> None:
    # Call the function to set the hash
    if not await create_hash_object(redis_client, MOCK_HASH_KEY, MOCK_HASH, MOCK_EXPIRE_SECONDS):
        pytest.fail("Failed to set hash in Redis")

    # Retrieve the hash using the get_hash_object function
    retrieved_mapping = await get_hash_object(redis_client, MOCK_HASH_KEY)

    # Verify that the retrieved mapping matches the original mapping
    assert retrieved_mapping == MOCK_HASH

    # Test retrieving a non-existent hash
    non_existent_key = "non_existent_hash"
    retrieved_non_existent = await get_hash_object(redis_client, non_existent_key)

    # Verify that the result is None for a non-existent hash
    assert retrieved_non_existent is None


async def test_delete_object(redis_client: Redis) -> None:
    # Call the function to set the hash
    if not await create_hash_object(redis_client, MOCK_HASH_KEY, MOCK_HASH, MOCK_EXPIRE_SECONDS):
        pytest.fail("Failed to set hash in Redis")

    assert await hash_object_exists(redis_client, MOCK_HASH_KEY) is True

    # Delete the hash using the delete_object function
    delete_result = await delete_object(redis_client, MOCK_HASH_KEY)

    # Verify that the delete operation was successful
    assert delete_result is True

    # Verify that the hash no longer exists in Redis
    exists_after_delete = await hash_object_exists(redis_client, MOCK_HASH_KEY)
    assert exists_after_delete is False

    # Test deleting a non-existent hash
    non_existent_key = "non_existent_hash"
    delete_non_existent_result = await delete_object(redis_client, non_existent_key)

    # Verify that the delete operation returns False for a non-existent hash
    assert delete_non_existent_result is False
