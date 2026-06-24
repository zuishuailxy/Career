from openai import AsyncOpenAI


async def compress_history(history: list[dict], client: AsyncOpenAI) -> None:
    """
    当 history 中用户消息超过 3 条时，将最早的 3 轮对话压缩为一句摘要，
    直接在原 history 上修改。

    示例：
      压缩前: [system, user1, assistant1, user2, assistant2, user3, assistant3, user4, ...]
      压缩后: [system, 摘要, user4, ...]
    """
    # 找到所有 user 消息的索引（跳过 system prompt）
    user_indices = [i for i, msg in enumerate(history) if msg["role"] == "user"]

    if len(user_indices) <= 3:
        return  # 不超过 3 条，无需压缩

    # 取前 3 轮对话（user + assistant 成对）
    first_user_idx = user_indices[0]
    # 第三轮 assistant 在第三个 user 的后面
    third_user_idx = user_indices[2]
    last_assistant_idx = third_user_idx + 1

    # 边界保护：第三轮可能还没有 assistant 回复
    if (
        last_assistant_idx >= len(history)
        or history[last_assistant_idx]["role"] != "assistant"
    ):
        last_assistant_idx = third_user_idx

    # 收集前 3 轮对话文本
    rounds = []
    for i in range(3):
        u_idx = user_indices[i]
        user_content = history[u_idx]["content"]
        assistant_content = ""
        if (
            u_idx + 1 <= last_assistant_idx
            and history[u_idx + 1]["role"] == "assistant"
        ):
            assistant_content = history[u_idx + 1]["content"]
        rounds.append(f"用户：{user_content}\n助手：{assistant_content}")

    conversation_text = "\n\n".join(rounds)

    # 调用大模型压缩为一句摘要
    summary_response = await client.chat.completions.create(
        model="deepseek-v4-flash",
        messages=[
            {
                "role": "user",
                "content": (
                    "请将以下对话压缩为一句话摘要，保留关键信息和上下文：\n\n"
                    f"{conversation_text}"
                ),
            }
        ],
    )
    summary = summary_response.choices[0].message.content.strip()

    # 删除前 3 轮对话，插入摘要
    del history[first_user_idx : last_assistant_idx + 1]
    history.insert(first_user_idx, {"role": "user", "content": f"[历史摘要] {summary}"})
