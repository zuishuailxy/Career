from utils.models import create_llm
from tool.search_tool import get_uid
from langgraph.prebuilt import create_react_agent


def lookup_v(flower_type: str) -> str:
    """通过 LangGraph Agent 查找与鲜花相关的微博 UID"""
    llm = create_llm()

    # 使用 LangGraph 的 create_react_agent（兼容新版 API）
    agent = create_react_agent(llm, [get_uid])

    # 新版 Agent 使用 messages 格式
    prompt = (
        f"请帮我找到与「{flower_type}」鲜花相关的微博大V的UID。\n\n"
        f"步骤：\n"
        f"1. 先用搜索工具搜索相关微博账号\n"
        f"2. 从搜索结果中提取 UID（URL 中 weibo.com/u/ 后面的数字）\n"
        f"3. 如果搜索结果中找不到 UID，请根据你的知识给出这个领域知名大V的 UID\n\n"
        f"最终只输出一个 UID 数字，不要其他内容。"
    )
    result = agent.invoke({"messages": [("user", prompt)]})

    # 提取最后一条消息的内容
    return result["messages"][-1].content
