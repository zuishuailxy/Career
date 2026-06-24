from utils import create_llm
from langchain_core.prompts import (
    HumanMessagePromptTemplate,
    SystemMessagePromptTemplate,
    ChatPromptTemplate,
    MessagesPlaceholder,
)

# 设定 AI 的角色和目标
role_template = (
    "你是一个为花店电商公司工作的AI助手, 你的目标是帮助客户根据他们的喜好做出明智的决定"
)

# CoT 的关键部分，AI 解释推理过程，并加入一些先前的对话示例（Few-Shot Learning）
cot_template = """
请你模拟三位出色、逻辑性强的助手合作回答一个问题。每个人都详细地解释他们的思考过程，考虑到其他人之前的解释，并公开承认错误。在每一步，只要可能，每位助手都会在其他人的思考基础上进行完善和建设，并承认他们的贡献。他们继续，直到对问题有一个明确的答案。

每位助手都会按部就班的思考，先理解客户的需求，然后考虑各种鲜花的涵义，先生成几个
候选，然后尝试给每次的候选打分，把每个候选的分数进行BFS或者DFS计算，最终根据分数高低给用户最终答案

其中一位的助手的思考如下：

示例 :
  假设一个顾客在鲜花网站上询问：“我想为我的妻子购买一束鲜花，但我不确定应该选择哪种鲜花。她喜欢淡雅的颜色和花香。”   
   
  思维步骤 1：理解顾客的需求。 顾客想为妻子购买鲜花。 顾客的妻子喜欢淡雅的颜色和花香。   
  
  思维步骤 2：考虑可能的鲜花选择。 
  候选 1：百合，因为它有淡雅的颜色和花香， 分数：0.3。
  候选 2：玫瑰，选择淡粉色或白色，它们通常有花香， 分数：0.2。
  候选 3：紫罗兰，它有淡雅的颜色和花香， 分数：0.4。
  候选 4：桔梗，它的颜色淡雅但不一定有花香， 分数：0.2。
  候选 5：康乃馨，选择淡色系列，它们有淡雅的花香， 分数：0.3。  
  
  思维步骤 3：根据顾客的需求筛选最佳选择。 
  百合和紫罗兰都符合顾客的需求，因为它们都有淡雅的颜色和花香。 
  淡粉色或白色的玫瑰也是一个不错的选择。 
  桔梗可能不是最佳选择，因为它可能没有花香。 康乃馨是一个可考虑的选择。

  思维步骤 4：给出建议。 “考虑到您妻子喜欢淡雅的颜色和花香，我建议您可以选择百合或紫罗兰。淡粉色或白色的玫瑰也是一个很好的选择。希望这些建议能帮助您做出决策！”


"""
system_prompt_role = SystemMessagePromptTemplate.from_template(role_template)
system_prompt_cot = SystemMessagePromptTemplate.from_template(cot_template)

# 用户的询问
human_template = "{human_input}"
human_prompt = HumanMessagePromptTemplate.from_template(human_template)

# 将以上所有信息结合为一个聊天提示
prompt = ChatPromptTemplate.from_messages(
    [system_prompt_role, system_prompt_cot, human_prompt]
)


# prompt = chat_prompt.format_prompt(
#     human_input="我想为我的女朋友购买一些花。她喜欢粉色和紫色。你有什么建议吗?"
# ).to_messages()
# print(prompt)

llm = create_llm()
chain = prompt | llm

response = chain.invoke(
    {
        "human_input": "我想为我的老婆购买一些花。她喜欢鲜艳的颜色和花香。而且今天是结婚纪念日，你有什么建议吗?",
    }
)

print(response.content)
