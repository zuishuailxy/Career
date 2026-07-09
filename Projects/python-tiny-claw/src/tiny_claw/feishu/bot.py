"""飞书机器人 — 长连接模式，无需 ngrok"""

import asyncio
import json
import logging
import os
from typing import Any

from lark_oapi import Client
from lark_oapi.event.dispatcher_handler import EventDispatcherHandler
from lark_oapi.ws import Client as WsClient
from lark_oapi.api.im.v1 import CreateMessageRequest, CreateMessageRequestBody

from tiny_claw.engine import AgentEngine, Reporter

logger = logging.getLogger("tiny-claw.feishu")


class FeishuReporter(Reporter):
    """将引擎输出格式化后发送到飞书"""

    def __init__(self, client: Client, chat_id: str):
        self._client = client
        self._chat_id = chat_id

    async def on_thinking(self, content: str) -> None:
        await self._send("🤔 模型正在慢思考 (Thinking)...")

    async def on_tool_call(self, tool_name: str, args: dict[str, Any]) -> None:
        await self._send(
            f"🛠️ **正在执行工具**：`{tool_name}`\n"
            f"参数：`{json.dumps(args, ensure_ascii=False)}`"
        )

    async def on_tool_result(self, tool_name: str, output: str, is_error: bool) -> None:
        if is_error:
            await self._send(f"⚠️ **执行报错** ({tool_name})：\n{output}")
        else:
            await self._send(f"✅ **执行成功** ({tool_name})")

    async def on_message(self, content: str) -> None:
        await self._send(content)

    async def _send(self, text: str) -> None:
        content_str = json.dumps({"text": text}, ensure_ascii=False)
        req = (
            CreateMessageRequest.builder()
            .receive_id_type("chat_id")
            .request_body(
                CreateMessageRequestBody.builder()
                .receive_id(self._chat_id)
                .msg_type("text")
                .content(content_str)
                .build()
            )
            .build()
        )
        try:
            await self._client.im.v1.message.acreate(req)
        except Exception as e:
            logger.error("飞书消息发送失败: %s", e)


class FeishuBot:
    """飞书机器人 — 长连接模式"""

    def __init__(self, engine: AgentEngine):
        app_id = os.getenv("FEISHU_APP_ID", "")
        app_secret = os.getenv("FEISHU_APP_SECRET", "")
        if not app_id or not app_secret:
            raise ValueError("请设置 FEISHU_APP_ID 和 FEISHU_APP_SECRET")
        self._app_id = app_id
        self._app_secret = app_secret
        self._client = Client.builder().app_id(app_id).app_secret(app_secret).build()
        self._engine = engine
        logger.info("飞书机器人初始化完成（长连接模式）")

    def start(self) -> None:
        """启动长连接，阻塞运行"""

        def handle_message(event: Any) -> None:
            try:
                inner = event.event
                content = json.loads(inner.message.content).get("text", "")
                chat_id = inner.message.chat_id
                logger.info("收到会话 %s 消息: %s", chat_id, content[:100])
                asyncio.create_task(self._handle_agent(chat_id, content))
            except Exception as e:
                logger.error("消息处理失败: %s", e)

        handler = (
            EventDispatcherHandler.builder("", "")
            .register_p2_im_message_receive_v1(handle_message)
            .build()
        )

        logger.info("🚀 tiny-claw 飞书长连接已启动，等待消息...")
        WsClient(self._app_id, self._app_secret, event_handler=handler).start()

    async def _handle_agent(self, chat_id: str, prompt: str) -> None:
        reporter = FeishuReporter(self._client, chat_id)
        old = self._engine.reporter
        self._engine.reporter = reporter
        try:
            await self._engine.run(prompt)
        except Exception as e:
            await reporter._send(f"❌ Agent 运行崩溃: {e}")
        finally:
            self._engine.reporter = old
