import numpy as np
from typing import List
import asyncio
from sentence_transformers import SentenceTransformer

# 1. 全局加载模型（只加载一次，避免重复下载）
model = SentenceTransformer("BAAI/bge-small-zh-v1.5")


async def embed_text(texts: List[str]) -> np.ndarray:
    """
    异步生成文本向量，使用 BAAI/bge-small-zh-v1.5 模型。

    Args:
        texts: 文本列表

    Returns:
        shape (len(texts), 384) 的 float32 数组
    """
    # 2. 使用 asyncio.to_thread 执行同步的 encode 方法
    embeddings = await asyncio.to_thread(
        model.encode,
        inputs=texts,
        normalize_embeddings=False,  # 不归一化，与 OpenAI 默认行为一致
        show_progress_bar=False,  # 静默运行
        convert_to_numpy=True,  # 返回 numpy 数组
    )
    # 3. 确保返回 float32 类型
    return np.array(embeddings, dtype="float32")
