"""Custom logging handlers."""

from copy import copy
from logging.handlers import QueueHandler
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from logging import LogRecord


class PreservingQueueHandler(QueueHandler):
    """QueueHandler that does not flatten record.msg/args.

    The default QueueHandler.prepare() pre-formats the message and sets
    record.args = None so the record is safe to pickle for multiprocessing
    queues. This breaks formatters like uvicorn's AccessFormatter that rely
    on unpacking record.args themselves. Since we use a plain Queue (not
    multiprocessing), pickling is not required, so we can safely preserve
    the original record.
    """

    def prepare(self, record: LogRecord) -> LogRecord:
        """Return the original record without modification."""
        return copy(record)
