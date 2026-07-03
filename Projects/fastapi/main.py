from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from openai import AsyncOpenAI
from dotenv import load_dotenv
import os
from fastapi import Request, Body
from pydantic import BaseModel
from fastapi.responses import StreamingResponse
from utils import compress_history
from tools import tools, get_stock_price
import json
import logging
from log import setup_logging

# 在启动任何其他模块之前，先初始化日志
setup_logging()

# 获取当前模块的 Logger
logger = logging.getLogger(__name__)
logger.info("应用启动")

# Basic config
# logging.basicConfig(
#     level=logging.INFO,  # 设置全局级别
#     format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",  # 格式
#     datefmt="%Y-%m-%d %H:%M:%S",
#     handlers=[
#         logging.FileHandler("app.log"),  # 输出到文件
#         logging.StreamHandler(),  # 输出到控制台
#     ],
# )

# logging.info("应用启动了")

# 加载 .env 文件中的环境变量
load_dotenv()

api_key = os.getenv("API_KEY")
if not api_key:
    raise ValueError(
        "未找到 API_KEY 环境变量。请在项目根目录创建 .env 文件，内容如下：\n"
        "API_KEY=your_deepseek_api_key_here\n"
        "或者直接设置环境变量: export API_KEY=your_deepseek_api_key_here"
    )

client = AsyncOpenAI(api_key=api_key, base_url="https://api.deepseek.com")


app = FastAPI()

# 允许跨域请求（前端 Live Server 和 FastAPI 在不同端口）
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class History(BaseModel):
    messages: list[dict]


history = [{"role": "system", "content": "你是一个助手"}]


@app.post("/chat")
async def chat(query):
    history.append({"role": "user", "content": query})
    response = await client.chat.completions.create(
        model="deepseek-v4-flash",  # 或 deepseek-v4-flash
        messages=history,
        tools=tools,
        tool_choice="auto",

    )

    print("before compress", len(history))
    await compress_history(history, client)  # 超过 3 轮自动压缩
    print("after compress", len(history))

    # 获取模型的响应
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    if not tool_calls:
        history.append({"role": "assistant", "content": response_message.content})
        return {"response": response}

    # add 需要tool call 的message
    history.append(response_message)

    # 可能会返回多个tool ，需要遍历调用
    for tool_call in tool_calls:
        function_name = tool_call.function.name
        function_args = json.loads(tool_call.function.arguments)  # 解析参数 JSON

        print(f"模型请求调用函数: {function_name}")
        print(f"函数参数: {function_args}")

        # 执行真实的函数
        if function_name == "get_stock_price":
            # 从解析出的参数中获取股票代码
            symbol = function_args.get("symbol")
            result = get_stock_price(symbol)  # 调用真实函数
            function_response = f"股票 {symbol} 的价格是 ${result}"

            print(f"函数执行结果: {function_response}")
        else:
            result = "未知函数"

        history.append(
            {
                "role": "tools",
                "tool_call_id": tool_call.id,
                "content": result,
            }
        )

    print(history)
    # 第二轮：生成最终回复
    final_response = await client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=history,
    )
    return final_response.choices[0].message.content


class QueryRequest(BaseModel):
    query: str


# 核心步骤是：创建一个异步生成器，用它来消费OpenAI API返回的流式chunks，并最终将这个生成器传给FastAPI的StreamingResponse类。
@app.post("/stream")
async def stream(body: QueryRequest, raw_request: Request):
    query = body.query

    # 定义一个异步生成器，用于产生流式数据块
    async def stream_generator():
        assistant_content = ""  # 累积完整的助手回复
        try:
            # 将用户输入添加到对话历史中
            history.append({"role": "user", "content": query})
            print(history)
            response = await client.chat.completions.create(
                model="deepseek-v4-flash",  # 或 deepseek-v4-flash
                messages=history,
                stream=True,  # 关键参数：启用流式输出
            )
            # 异步迭代 OpenAI 返回的流式数据块
            async for chunk in response:
                # 检查客户端是否已断开连接，避免做无用功
                if await raw_request.is_disconnected():
                    print("Client disconnected, stopping stream.")
                    break
                content = chunk.choices[0].delta.content or ""
                if content:
                    assistant_content += content  # 累积内容
                    # 以 Server-Sent Events (SSE) 格式 yield 数据
                    yield f"data: {content}\n\n"

            # 流结束后，将完整的助手回复存入历史
            if assistant_content:
                history.append({"role": "assistant", "content": assistant_content})
                await compress_history(history, client)  # 超过 3 轮自动压缩
                print(
                    "Assistant reply saved to history:", assistant_content[:50], "..."
                )

        except Exception as e:
            # 发生错误时，可以向客户端发送一个错误事件
            error_msg = f"event: error\ndata: {str(e)}\n\n"
            yield error_msg
        finally:
            # 无论成功或失败，都发送 SSE 结束信号
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        stream_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",  # 禁用缓存
            "X-Accel-Buffering": "no",  # 为 Nginx 等代理禁用缓冲
            "Connection": "keep-alive",  # 保持连接打开
        },
    )
