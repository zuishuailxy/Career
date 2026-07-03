from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_community.document_loaders import PyPDFLoader, Docx2txtLoader, TextLoader
import os
from dotenv import load_dotenv
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client.models import Distance, VectorParams
from langchain_qdrant import QdrantVectorStore
import logging

# try to use SemanticChunker
from langchain_experimental.text_splitter import SemanticChunker

load_dotenv()
api_key = os.getenv("API_KEY")
print(api_key)

# 1. load documents
base_dir = "./data"
documents = []

for file in os.listdir(base_dir):
    # 构建完整的文件路径
    file_path = os.path.join(base_dir, file)
    if file.endswith(".pdf"):
        loader = PyPDFLoader(file_path)
        documents.extend(loader.load())
    elif file.endswith(".docx"):
        loader = Docx2txtLoader(file_path)
        documents.extend(loader.load())
    elif file.endswith(".txt"):
        loader = TextLoader(file_path)
        documents.extend(loader.load())

# embedding model
local_model_path = "./models"
# 初始化嵌入模型
embeddings = HuggingFaceEmbeddings(
    model_name=local_model_path,  # 1. 指定模型ID
    model_kwargs={"device": "cpu"},  # 2. 指定设备 (cpu/cuda)
    encode_kwargs={"normalize_embeddings": True},  # 3. 是否归一化向量
)

# 2. Split 将Documents切分成块以便后续进行嵌入和向量存储
# 2. 创建语义分块器
#    breakpoint_threshold_type: 决定切分阈值的方法，可选：
#    - 'percentile'：基于百分位数（默认）
#    - 'standard_deviation'：基于标准差
#    - 'interquartile'：基于四分位距
# text_splitter = SemanticChunker(
#     embeddings=embeddings, breakpoint_threshold_type="percentile"  # 或其他
# )
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=500,  # chunk size (characters)
    chunk_overlap=50,  # chunk overlap (characters)
    add_start_index=True,  # track index in original document
)
chunked_documents = text_splitter.split_documents(documents)


# 3.Store 将分割嵌入并存储在矢量数据库Qdrant中
vectorstore = QdrantVectorStore.from_documents(
    documents=chunked_documents,  # 以分块的文档
    embedding=embeddings,  # 用OpenAI的Embedding Model做嵌入
    location=":memory:",  # in-memory 存储
    collection_name="my_documents",
)  # 指定collection_name

# 4. Retrieval 准备模型和Retrieval链
from langchain_classic.retrievers import (
    MultiQueryRetriever,
)  # MultiQueryRetriever工具
from langchain_classic.chains import RetrievalQA  # RetrievalQA链
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

# 设置Logging
logging.basicConfig()
logging.getLogger("langchain_community.retrievers").setLevel(logging.INFO)

# 推荐使用 deepseek-chat 模型，它功能最完整[reference:9]
llm = ChatDeepSeek(
    model="deepseek-chat",
    temperature=0.7,  # 控制随机性，范围 0-1[reference:10]
    max_tokens=None,  # 最大生成 token 数[reference:11]
    timeout=None,  # 请求超时时间[reference:12]
    max_retries=2,  # 最大重试次数[reference:13]
    api_key=api_key,
)

"""
虽然 similarity 是最常用的默认选项，但在当下的生产环境中，单纯靠相似度已经不够用了。现在的主流做法是：

相似度检索作为“粗排”：先用 search_type="similarity" 快速筛出 Top 20 或 Top 50 个候选块。

重排序（Rerank）作为“精排”：用一个更强大的交叉编码器（Cross-Encoder）模型（如 Cohere Rerank、BGE-reranker-v2）对这 20 个候选块重新打分排序，最后只取前 3-5 个喂给 LLM。
"""

retriever = vectorstore.as_retriever(
    search_type="similarity",  # 指定使用标准相似度检索
    search_kwargs={"k": 4},  # 只取最相似的 4 个块
)
# 2. 定义提示词模板
system_prompt = """基于以下内容回答问题。如果你不知道答案，就回答不知道。
    
    内容: {context}
    
    问题: {question}
    """

# prompt = ChatPromptTemplate.from_messages(
#     [
#         ("system", system_prompt),
#         ("human", "{input}"),
#     ]
# )

prompt = ChatPromptTemplate.from_template(system_prompt)


# 3. 创建 "问答链"，负责结合上下文和问题生成答案
# question_answer_chain = create_stuff_documents_chain(llm, prompt)

# 4. 创建 "检索链"，负责获取相关文档并调用问答链
# chain = create_retrieval_chain(retriever, question_answer_chain)

# use LCEL

from operator import itemgetter

chain = (
    {
        "context": itemgetter("question") | retriever,  # 提取问题 → 检索文档
        "question": itemgetter("question"),  # 提取问题原样传递
    }
    | prompt
    | llm
    | StrOutputParser()
)


from fastapi import FastAPI

app = FastAPI()


@app.post("/chat")
async def chat(query):

    # 5. 调用链
    response = chain.invoke({"question": query})

    # return response["answer"]

    return response
