"""IRN method handlers.

Each handler is a factory that closes over a `MessageRouter` and returns
the actual async handler. `register_all` wires them all into a dispatcher.
"""
from relay.protocol.dispatcher import Dispatcher
from relay.service import MessageRouter

from .acknowledge import make_acknowledge_handler
from .batch_fetch import make_batch_fetch_handler
from .batch_publish import make_batch_publish_handler
from .batch_subscribe import make_batch_subscribe_handler
from .publish import make_publish_handler
from .subscribe import make_subscribe_handler
from .unsubscribe import make_unsubscribe_handler

__all__ = ["register_all"]


def register_all(dispatcher: Dispatcher, router: MessageRouter) -> None:
    dispatcher.register("irn_publish", make_publish_handler(router))
    dispatcher.register("irn_subscribe", make_subscribe_handler(router))
    dispatcher.register("irn_unsubscribe", make_unsubscribe_handler(router))
    dispatcher.register("irn_batchPublish", make_batch_publish_handler(router))
    dispatcher.register("irn_batchSubscribe", make_batch_subscribe_handler(router))
    dispatcher.register("irn_batchFetch", make_batch_fetch_handler(router))
    dispatcher.register("irn_acknowledge", make_acknowledge_handler(router))
