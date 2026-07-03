"""
用 LangChain 实现一个类似 CAMEL 的框架，核心在于设计角色提示词和编排对话流程。
"""
import os
from typing import List, Dict, Any
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough
from utils import create_llm


# 它封装了一个 LLM 和特定的角色指令。
class RolePlayingAgent:
    def __init__(self, role_name: str, system_prompt: str, llm: ChatOpenAI):
        self.role_name = role_name
        self.llm = llm
        # 创建包含系统提示词的聊天模板
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", system_prompt),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{input}"),
        ])
        # 构建一个简单的处理链
        self.chain = self.prompt | self.llm | StrOutputParser()

    def invoke(self, history: List, input_text: str) -> str:
        """同步调用代理"""
        return self.chain.invoke({"history": history, "input": input_text})


# 负责整个对话流程，它接收初始任务，并让两个代理轮流发言。
class RolePlayingManager:
    def __init__(self, assistant_agent: RolePlayingAgent, user_agent: RolePlayingAgent):
        self.assistant_agent = assistant_agent
        self.user_agent = user_agent
        self.history: List = []  # 存储对话历史

    def _format_history(self) -> List:
        """将历史记录格式化为消息列表"""
        messages = []
        for entry in self.history:
            if entry["role"] == "assistant":
                messages.append(AIMessage(content=entry["content"]))
            elif entry["role"] == "user":
                messages.append(HumanMessage(content=entry["content"]))
        return messages

    def start_dialogue(self, initial_task: str, max_turns: int = 5) -> List[Dict]:
        """启动角色扮演对话"""
        # 1. 用户代理首先发言，提出任务
        user_input = initial_task
        for turn in range(max_turns):
            # 用户代理发言
            history_for_user = self._format_history()
            user_response = self.user_agent.invoke(history_for_user, user_input)
            self.history.append({"role": "user", "content": user_response})
            print(f"🤖 {self.user_agent.role_name}: {user_response}")

            # 检查任务是否完成（简单判断，实际可以更复杂）
            if "task completed" in user_response.lower():
                break

            # 助手代理发言
            history_for_assistant = self._format_history()
            assistant_response = self.assistant_agent.invoke(history_for_assistant, user_response)
            self.history.append({"role": "assistant", "content": assistant_response})
            print(f"🧠 {self.assistant_agent.role_name}: {assistant_response}")

            # 为下一轮准备输入
            user_input = "请继续"  # 简单的轮转机制

        return self.history


# 1. 初始化 LLM
llm = create_llm(temperature=0.7)

# 2. 定义角色提示词（模拟 CAMEL 的风格）[reference:9]
assistant_sys_prompt = """
你是一名资深的【AI 助手】。你的任务是帮助【AI 用户】解决他们提出的问题。
- 你必须始终以 "解决方案: <你的解决方案>" 开头来回应。
- 在提供解决方案后，必须以 "下一个请求。" 结尾，以保持对话继续。
- 永远不要翻转角色，不要指示用户。
- 如果你因为任何原因无法执行指令，必须诚实地拒绝并解释原因。
"""

user_sys_prompt = """
你是一名【AI 用户】。你的目标是向【AI 助手】提出清晰、具体的指令，以完成你的任务。
- 你的指令应该逐步推进任务的完成。
- 当你认为任务已经完全达成时，请明确说出 "任务完成"。
"""

# 3. 创建代理
assistant = RolePlayingAgent("AI 助手", assistant_sys_prompt, llm)
user = RolePlayingAgent("AI 用户", user_sys_prompt, llm)

# 4. 创建管理器并启动对话
manager = RolePlayingManager(assistant, user)

# 5. 开始任务
initial_task = "我需要一份关于'人工智能在医疗领域应用'的简要报告大纲。"
print(f"👤 初始任务: {initial_task}\n")
dialogue_history = manager.start_dialogue(initial_task, max_turns=4)