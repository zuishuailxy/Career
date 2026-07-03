"""Base model"""

from langchain_core.messages import HumanMessage, SystemMessage
from models import create_llm


def main():
    llm = create_llm()
    # 创建一个消息列表
    messages = [
        SystemMessage(content="你是一个花卉行家。"),
        HumanMessage(content="朋友喜欢淡雅的颜色，她的婚礼我选择什么花？"),
    ]

    chain = llm
    response = chain.invoke(messages)
    print(response)


if __name__ == "__main__":
    main()
