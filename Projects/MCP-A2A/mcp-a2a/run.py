from python_a2a.client import A2AClient

import os

agent_url = "http://localhost:7002"
# 创建客户端，指向你运行的代理服务地址
client = A2AClient(agent_url)
response = client.ask(
    "我计划下周去巴黎旅游，并且告诉我当地的天气情况，然后推荐各自的热门景点和美食"
)
print(response)
