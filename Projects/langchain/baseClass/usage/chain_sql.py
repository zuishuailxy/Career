"""
利用llm 操作数据库
"""

from langchain.agents import create_agent
from utils import create_llm
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits.sql.toolkit import SQLDatabaseToolkit

db_uri = "postgresql+psycopg2://admin:123456@localhost:5432/mydatabase"
db = SQLDatabase.from_uri(db_uri)
llm = create_llm(0)

# 获取 SQL 工具包中的所有工具
toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()

agent = create_agent(llm, tools)

# question = "库存最多的鲜花是哪一种？它的库存量是多少？"
# response = agent.invoke({"messages": [("user", question)]})
# # 取最后一条 AI 消息作为答案
# final_message = response["messages"][-1]
# print("回答：", final_message.content)

question = "Lily的销量+10"
response = agent.invoke({"messages": [("user", question)]})
# 取最后一条 AI 消息作为答案
final_message = response["messages"][-1]
print("回答：", final_message.content)
