import sys, asyncio, os, json
from mcp import ClientSession
from mcp.client.stdio import stdio_client, StdioServerParameters
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()


# ============================================================
# RAG 客户端 — 连接 MCP 服务端，通过 LLM + 知识检索回答问题
# 工作流程：
#   1. 通过 stdio 连接 MCP 服务端（rag-server）
#   2. 获取服务端暴露的工具（index_docs / retrieve_docs）
#   3. 用户提问 → LLM 判断是否需要检索 → 调用工具 → LLM 生成最终回答
# ============================================================
class RagClient:
    def __init__(self):
        self.session = None  # MCP 客户端会话
        self.transport = None  # stdio_client 的上下文管理器
        self.client = OpenAI(  # DeepSeek LLM 客户端
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            base_url="https://api.deepseek.com",
        )
        self.tools = None  # 从服务端获取的工具列表（将在 connect 时填充）

    async def connect(self, server_script: str):
        """连接到 MCP 服务端，获取可用工具。"""
        # 1) 构造 stdio 参数：通过 uv run 启动服务端脚本
        #    设置 cwd 为脚本所在目录，确保服务端能正确导入同目录模块
        server_dir = os.path.dirname(os.path.abspath(server_script))
        params = StdioServerParameters(
            command="uv",
            args=["run", server_script],
            cwd=server_dir,
        )
        # 2) 建立 stdio 传输通道（本质是启动子进程并通过管道通信）
        self.transport = stdio_client(params)
        self.stdio, self.write = await self.transport.__aenter__()
        # 3) 初始化 MCP 协议会话（必须调用 initialize 完成握手）
        self.session = await ClientSession(self.stdio, self.write).__aenter__()
        await self.session.initialize()
        # 4) 拉取服务端注册的工具列表，转换为 OpenAI Function Calling 格式
        resp = await self.session.list_tools()
        self.tools = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.inputSchema,
                },
            }
            for tool in resp.tools
        ]
        print("可用工具：", [t["function"]["name"] for t in self.tools])

    async def query(self, q: str):
        """处理用户查询：LLM 自主判断是否调用检索工具，循环直到生成最终回答。"""
        # 初始化对话消息：system 指令 + 用户问题
        messages = [
            {
                "role": "system",
                "content": "你是一个专业的医学助手，请根据提供的医学文档回答问题。如果用户的问题需要查询医学知识，请使用列表中的工具来获取相关信息。",
            },
            {"role": "user", "content": q},
        ]
        while True:
            try:
                # 1) 调用 DeepSeek API，传入可用工具让 LLM 自主选择
                response = self.client.chat.completions.create(
                    model="deepseek-v4-flash",
                    messages=messages,
                    tools=self.tools,
                    tool_choice="auto",  # LLM 自主决定是否调工具
                )
                message = response.choices[0].message
                messages.append(message)

                # 2) 如果 LLM 没有调用工具，说明已生成最终回答，直接返回
                if not message.tool_calls:
                    return message.content

                # 3) 遍历 LLM 请求调用的每个工具，执行并返回结果
                for tool_call in message.tool_calls:
                    # 解析 LLM 生成的工具参数（JSON 字符串）
                    args = json.loads(tool_call.function.arguments)
                    # 通过 MCP 会话调用服务端上的工具
                    result = await self.session.call_tool(tool_call.function.name, args)
                    # 将工具执行结果追加到对话历史，供 LLM 下一轮推理使用
                    messages.append(
                        {
                            "role": "tool",
                            "content": str(result),
                            "tool_call_id": tool_call.id,
                        }
                    )
                # 带着工具结果继续循环，让 LLM 生成最终回答
            except Exception as e:
                print(f"发生错误: {str(e)}")
                return "抱歉，处理您的请求时出现了问题。"

    async def close(self):
        """安全关闭 MCP 会话和传输通道。"""
        try:
            if self.session:
                await self.session.__aexit__(None, None, None)
            if self.transport:
                await self.transport.__aexit__(None, None, None)
        except Exception as e:
            print(f"关闭连接时发生错误: {str(e)}")


async def main():
    print(">>> 开始初始化 RAG 系统")
    if len(sys.argv) < 2:
        print("用法: python client.py <server.py 路径>")
        return

    # 1) 连接 MCP 服务端
    client = RagClient()
    res = await client.connect(sys.argv[1])
    print(res)
    print(">>> 系统连接成功")

    # 2) 索引一批医学知识文档到服务端
    medical_docs = [
        "糖尿病是一种慢性代谢性疾病，主要特征是血糖水平持续升高。",
        "高血压是指动脉血压持续升高，通常定义为收缩压≥180mmHg和/或舒张压≥60mmHg。",
        "冠心病是由于冠状动脉粥样硬化导致心肌缺血缺氧的疾病。",
        "哮喘是一种慢性气道炎症性疾病，表现为反复发作的喘息、气促、胸闷和咳嗽。",
        "肺炎是由细菌、病毒或其他病原体引起的肺部感染，常见症状包括发热、咳嗽和呼吸困难。",
    ]
    print(">>> 正在索引医学文档...")
    res = await client.session.call_tool("index_docs", {"docs": medical_docs})
    print(">>> 文档索引完成")

    # 3) 交互式问答循环
    while True:
        print("\n请输入您要查询的医学问题（输入'退出'结束查询）：")
        query = input("> ")
        if query.lower() == "退出":
            break
        print(f"\n正在查询: {query}")
        response = await client.query(query)
        print("\nAI 回答：\n", response)

    await client.close()
    print(">>> 系统已关闭")


if __name__ == "__main__":
    asyncio.run(main())
