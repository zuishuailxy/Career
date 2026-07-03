from dotenv import load_dotenv
import os
from langchain_core.prompts import ChatPromptTemplate

load_dotenv()


# ---- LangSmith 配置 ----
os.environ["LANGSMITH_TRACING"] = "true"  # 必须显式设为 "true"
os.environ["LANGSMITH_PROJECT"] = "test"  # 项目名，必填！
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")

client = Client()

# 1. 定义并推送 (push) 一个提示词到 LangSmith[reference:17]
prompt = ChatPromptTemplate(
    [
        ("system", "你是一个乐于助人的{role}专家。"),
        ("user", "{question}"),
    ]
)
client.push_prompt("my-expert-prompt", object=prompt)

# 2. 从 LangSmith 拉取 (pull) 提示词并在代码中使用[reference:18]
pulled_prompt = client.pull_prompt("my-expert-prompt")

# 使用拉取下来的提示词
formatted_prompt = pulled_prompt.invoke(
    {"role": "Python", "question": "什么是装饰器？"}
)

print(formatted_prompt)
