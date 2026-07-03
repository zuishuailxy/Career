from dotenv import load_dotenv
import os

from langchain.agents import create_agent
from langchain_deepseek import ChatDeepSeek
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


load_dotenv()

# ---- LangSmith 配置 ----
os.environ["LANGSMITH_TRACING"] = "true"  # 必须显式设为 "true"
os.environ["LANGSMITH_PROJECT"] = "test"  # 项目名，必填！
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")


def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"


llm = ChatDeepSeek(
    model="deepseek-chat",
    temperature=0.7,  # 控制随机性，范围 0-1[reference:10]
    max_tokens=None,  # 最大生成 token 数[reference:11]
    timeout=None,  # 请求超时时间[reference:12]
    max_retries=2,  # 最大重试次数[reference:13]
)

prompt = ChatPromptTemplate.from_template("讲一个关于{topic}的笑话")

chain = prompt | llm | StrOutputParser()

# Run the agent
result = chain.invoke({"topic": "睡觉"})

print(result)
