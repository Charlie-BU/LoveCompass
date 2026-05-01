# todo：没法连接远程
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
from langgraph.checkpoint.serde.jsonplus import JsonPlusSerializer
import asyncio
import os
from threading import Lock
from typing import Any
from src.database.enums import (
    FigureRole,
    Gender,
    MBTI,
    FineGrainedFeedDimension,
    FineGrainedFeedConfidence,
    ConflictStatus,
)

_sync_checkpointer_instance: PostgresSaver | None = None
_sync_checkpointer_lock = Lock()
_sync_checkpointer_ctx: Any = None
_sync_checkpointer_setup_done = False

_async_checkpointer_instance: AsyncPostgresSaver | None = None
_async_checkpointer_lock = asyncio.Lock()
_async_checkpointer_ctx: Any = None
_async_checkpointer_setup_done = False
_checkpoint_serde = JsonPlusSerializer(
    allowed_msgpack_modules=[
        FigureRole,
        Gender,
        MBTI,
        FineGrainedFeedDimension,
        FineGrainedFeedConfidence,
        ConflictStatus,
    ]
)


def _requireCheckpointerURI() -> str:
    uri = (os.getenv("CHECKPOINT_DATABASE_URI") or "").strip()
    if uri == "":
        raise RuntimeError("CHECKPOINT_DATABASE_URI is empty")
    return uri


def getCheckpointer() -> PostgresSaver:
    global _sync_checkpointer_instance, _sync_checkpointer_ctx, _sync_checkpointer_setup_done
    if _sync_checkpointer_instance is not None and _sync_checkpointer_setup_done:
        return _sync_checkpointer_instance
    with _sync_checkpointer_lock:
        if _sync_checkpointer_instance is not None and _sync_checkpointer_setup_done:
            return _sync_checkpointer_instance
        if _sync_checkpointer_instance is None:
            _sync_checkpointer_ctx = PostgresSaver.from_conn_string(
                _requireCheckpointerURI()
            )
            _sync_checkpointer_instance = _sync_checkpointer_ctx.__enter__()

        # 自愈：即使历史实例已创建但表缺失，也会补跑 setup
        _sync_checkpointer_instance.setup()
        _sync_checkpointer_setup_done = True

        checkpointer = _sync_checkpointer_instance
        _sync_checkpointer_instance = checkpointer
        return _sync_checkpointer_instance


# 全局单例 checkpointer，并在首次创建时 setup() ，后续复用同一个连接池，避免被提前关闭
async def agetCheckpointer() -> AsyncPostgresSaver:
    global _async_checkpointer_instance, _async_checkpointer_ctx, _async_checkpointer_setup_done
    if _async_checkpointer_instance is not None and _async_checkpointer_setup_done:
        return _async_checkpointer_instance
    async with _async_checkpointer_lock:
        if _async_checkpointer_instance is not None and _async_checkpointer_setup_done:
            return _async_checkpointer_instance

        if _async_checkpointer_instance is None:
            _async_checkpointer_ctx = AsyncPostgresSaver.from_conn_string(
                _requireCheckpointerURI(),
                serde=_checkpoint_serde,
            )
            _async_checkpointer_instance = await _async_checkpointer_ctx.__aenter__()

        # 自愈：即使历史实例已创建但表缺失，也会补跑 setup
        await _async_checkpointer_instance.setup()
        _async_checkpointer_setup_done = True

        checkpointer = _async_checkpointer_instance
        _async_checkpointer_instance = checkpointer
        return _async_checkpointer_instance


def closeCheckpointer() -> None:
    """
    关闭同步 checkpointer（可在应用退出时调用）
    """
    global _sync_checkpointer_instance, _sync_checkpointer_ctx, _sync_checkpointer_setup_done
    with _sync_checkpointer_lock:
        if _sync_checkpointer_ctx is not None:
            _sync_checkpointer_ctx.__exit__(None, None, None)
        _sync_checkpointer_instance = None
        _sync_checkpointer_ctx = None
        _sync_checkpointer_setup_done = False


async def acloseCheckpointer() -> None:
    """
    关闭异步 checkpointer（可在应用退出时调用）
    """
    global _async_checkpointer_instance, _async_checkpointer_ctx, _async_checkpointer_setup_done
    async with _async_checkpointer_lock:
        if _async_checkpointer_ctx is not None:
            await _async_checkpointer_ctx.__aexit__(None, None, None)
        _async_checkpointer_instance = None
        _async_checkpointer_ctx = None
        _async_checkpointer_setup_done = False
