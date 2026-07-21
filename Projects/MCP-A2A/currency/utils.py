from langchain_deepseek import ChatDeepSeek
from dotenv import load_dotenv

load_dotenv()

# from langchain_huggingface import HuggingFaceEmbeddings


def create_llm(model="deepseek-v4-flash", temperature=0.7):
    llm = ChatDeepSeek(
        model=model,
        temperature=temperature,  # 控制随机性，范围 0-1[reference:10]
        max_tokens=None,  # 最大生成 token 数[reference:11]
        timeout=None,  # 请求超时时间[reference:12]
        max_retries=2,  # 最大重试次数[reference:13]
    )

    return llm


def create_embedding():
    # embedding model
    local_model_path = "../flowerQA/models"
    # 初始化嵌入模型
    embeddings = HuggingFaceEmbeddings(
        model_name=local_model_path,  # 1. 指定模型ID
        model_kwargs={"device": "cpu"},  # 2. 指定设备 (cpu/cuda)
        encode_kwargs={"normalize_embeddings": True},  # 3. 是否归一化向量
    )

    return embeddings
