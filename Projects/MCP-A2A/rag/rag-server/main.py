from typing import List
import faiss

# from openai import OpenAI
from fastmcp import FastMCP
from embeding import embed_text

# ============================================================
# 初始化 MCP Server（基于 FastMCP 框架）
# 这里将index_docs 和 retrieve_docs 注册为 MCP 工具，供客户端调用
# ============================================================
mcp = FastMCP("rag")

# ============================================================
# 向量索引（内存版 FAISS）
# _index: 512 维的 L2 距离（欧氏距离）暴力检索索引
#     - IndexFlatL2 是最基础的精确检索方式，无近似优化
#     - 512: embedding 向量的维度（与 BAAI/bge-small-zh-v1.5 模型对齐）
# _docs: 与索引中向量一一对应的原始文档文本列表
#     - _docs[i] 对应索引中第 i 条向量的原始文本
# ============================================================
_index: faiss.IndexFlatL2 = faiss.IndexFlatL2(512)
_docs: List[str] = []


@mcp.tool()
async def index_docs(docs: List[str]) -> str:
    """将一批文档加入索引。
    Args:
        docs: 文本列表
    """
    global _index, _docs

    # 1. 将文本批量转为 embedding 向量（调用外部 API）
    embeddings = await embed_text(docs)

    # 2. 将向量加入 FAISS 索引（必须转为 float32 类型）
    _index.add(embeddings.astype("float32"))

    # 3. 保存原始文本，供后续检索时返回
    _docs.extend(docs)

    return f"已索引 {len(docs)} 篇文档，总文档数：{len(_docs)}"


@mcp.tool()
async def retrieve_docs(query: str, top_k: int = 3) -> str:
    """检索最相关文档片段。
    Args:
        query: 用户查询
        top_k: 返回的文档数
    """
    # 1. 将用户查询转为 embedding 向量
    q_emb = await embed_text([query])

    # 2. 在 FAISS 索引中进行最近邻搜索
    #    D: 距离值数组（越小表示与查询越相似）
    #    I: 匹配到的文档在 _docs 中的索引位置
    D, I = _index.search(q_emb.astype("float32"), top_k)

    # 3. 将索引位置映射回原始文档文本，组装结果
    #    I[0] 是二维结果的第一行（因为 query 只有一条）
    #    if i < len(_docs) 做边界检查，防止 FAISS 返回无效索引
    results = [f"[{i}] {_docs[i]}" for i in I[0] if i < len(_docs)]

    # 4. 返回结果：多条文档用空行分隔，无结果时返回提示
    return "\n\n".join(results) if results else "未检索到相关文档。"


def main():
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
