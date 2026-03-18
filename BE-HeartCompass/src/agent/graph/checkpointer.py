import asyncio
import os
from threading import Lock
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

_sync_checkpointer_instance: PostgresSaver | None = None
_sync_checkpointer_lock = Lock()
_sync_checkpointer_ctx = None

_async_checkpointer_instance: AsyncPostgresSaver | None = None
_async_checkpointer_lock = asyncio.Lock()
_async_checkpointer_ctx = None


def _getCheckpointerURI() -> str:
    return os.getenv("CHECKPOINT_DATABASE_URI") or ""


def getCheckpointer() -> PostgresSaver:
    global _sync_checkpointer_instance, _sync_checkpointer_ctx
    if _sync_checkpointer_instance is not None:
        return _sync_checkpointer_instance
    with _sync_checkpointer_lock:
        if _sync_checkpointer_instance is not None:
            return _sync_checkpointer_instance
        _sync_checkpointer_ctx = PostgresSaver.from_conn_string(_getCheckpointerURI())
        checkpointer = _sync_checkpointer_ctx.__enter__()
        checkpointer.setup()
        _sync_checkpointer_instance = checkpointer
        return _sync_checkpointer_instance


# 全局单例 checkpointer，并在首次创建时 setup() ，后续复用同一个连接池，避免被提前关闭
async def agetCheckpointer() -> AsyncPostgresSaver:
    global _async_checkpointer_instance, _async_checkpointer_ctx
    if _async_checkpointer_instance is not None:
        return _async_checkpointer_instance
    async with _async_checkpointer_lock:
        if _async_checkpointer_instance is not None:
            return _async_checkpointer_instance
        _async_checkpointer_ctx = AsyncPostgresSaver.from_conn_string(
            _getCheckpointerURI()
        )
        checkpointer = await _async_checkpointer_ctx.__aenter__()
        await checkpointer.setup()
        _async_checkpointer_instance = checkpointer
        return _async_checkpointer_instance
