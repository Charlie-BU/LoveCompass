import os
from typing import List

from .ark import arkClient

# 全局单例
_ark_client = arkClient()


# 注意⚠️：多模态向量化能力模型不支持 OpenAI API，使用Ark SDK调用
# 向量化文本
async def vectorizeText(text: str) -> list[float]:
    resp = await _ark_client.multimodal_embeddings.create(
        model=os.getenv("EMBEDDING_ENDPOINT_ID", ""),
        input=[
            {"type": "text", "text": text},
        ],
        dimensions=1024,
    )
    return resp.data.embedding


# 向量化图片
async def vectorizeImage(image_url: str) -> list[float]:
    resp = await _ark_client.multimodal_embeddings.create(
        model=os.getenv("EMBEDDING_ENDPOINT_ID", ""),
        input=[
            {
                "type": "image_url",
                "image_url": {"url": image_url},
            },
        ],
        dimensions=1024,
    )
    return resp.data.embedding


# 向量化混合输入
async def vectorizeMixed(text: List[str], image_url: List[str]) -> list[float]:
    input_list = [{"type": "text", "text": t} for t in text] + [
        {"type": "image_url", "image_url": {"url": u}} for u in image_url
    ]
    resp = await _ark_client.multimodal_embeddings.create(
        model=os.getenv("EMBEDDING_ENDPOINT_ID", ""),
        input=input_list,
        dimensions=1024,
    )
    return resp.data.embedding
