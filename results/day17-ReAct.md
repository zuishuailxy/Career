**ReAct** 是 **Reasoning（推理）** + **Acting（行动）** 的缩写。它是 2022 年由 Google 和普林斯顿大学联合提出的一种**通用智能体（Agent）决策范式**。

你可以把它理解为**大模型在执行任务时的“思考-行动-观察”循环算法**。它是目前几乎所有主流 Agent 框架（LangGraph、AutoGPT、Coze 工作流）的底层理论基础。

为了让你彻底理解，我们不谈空泛概念，直接从 **“它长什么样”**、**“为什么需要它”** 以及 **“它和你的代码有什么关系”** 三个维度拆解。

---

### 1. ReAct 的核心循环（三步走）

ReAct 把一个复杂的任务分解成一个不断重复的 **“思考-行动-观察”** 三角循环。Agent 会一直重复这个循环，直到任务完成为止。

| 步骤  | 名称                    | 作用                                                        | 在代码/API 层面的表现                                                          |
| :---- | :---------------------- | :---------------------------------------------------------- | :----------------------------------------------------------------------------- |
| **1** | **Thought（思考）**     | 模型分析当前状态，决定“我下一步该做什么”。                  | 模型输出的 `content` 文字（通常对用户隐藏，只在日志中可见）。                  |
| **2** | **Action（行动）**      | 模型调用一个外部工具（Function/Tool）去获取信息或执行操作。 | 模型输出 `tool_calls`（即你之前学的 Function Calling）。你的后端执行这段代码。 |
| **3** | **Observation（观察）** | 模型读取工具返回的结果（成功/失败/数据）。                  | 你的后端把工具执行结果通过 `role: "tool"` 发回给模型。模型据此判断下一步。     |

---

### 2. 举个例子（自然语言翻译版）

假设你给 Agent 的任务是：**“帮我查一下北京今天的天气，并告诉我适不适合户外运动。”**

如果没有 ReAct（普通对话）：模型直接瞎猜一个答案。

有了 ReAct（循环推理）：

1.  **Thought（思考）**：用户想知道北京天气，我需要先查天气数据。
2.  **Action（行动）**：调用 `get_weather(city="Beijing")`。
3.  **Observation（观察）**：工具返回 `{"temp": "35°C", "condition": "暴晒"}`。
4.  **Thought（再次思考）**：温度为 35°C，属于高温暴晒，不太适合户外运动。
5.  **Action（行动）**：调用 `generate_advice(weather="hot")`（可选，也可以直接回复）。
6.  **Observation（观察）**：得到建议“建议室内活动，避免中暑”。
7.  **Answer（最终回答）**：输出自然语言“北京今天 35°C，暴晒，不建议户外运动，尽量待在室内。”

**你看，模型一共“思考”了两次，调用了两次工具，观察了两次结果，才生成最终答案。这就是 ReAct 的威力——它把一次性问答变成了链式推理。**

---

### 3. 为什么叫 ReAct，而不只是“调用工具”？

重点在于 **Re（Reasoning）** 和 **Act（Acting）** 的**交错进行**。

- **纯推理（CoT，思维链）**：模型只在脑子里想（推理），不执行工具。缺点是无法获取实时信息，容易产生幻觉。
- **纯行动（Act-only）**：模型遇到问题就盲目调工具。缺点是没有规划，如果第一个工具调错了，后续全错。
- **ReAct（推理+行动交错）**：**“想一步，走一步，看一眼结果，再想下一步”**。这种“边走边看”的策略，使得模型能根据实时反馈动态调整计划，极大提高了复杂任务的完成率。

---

### 4. ReAct 在手写 Agent 代码中长什么样（结合你的 FastAPI）

你之前一直纠结的 `while` 循环手写 Agent，其实就是 ReAct 的朴素实现。伪代码如下：

```python
# ReAct 循环的核心骨架
max_steps = 5  # 防止死循环
while step < max_steps:
    # 1. 调用大模型（带 tools 参数）
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,  # 包含 system, user, 以及历史的 tool 结果
        tools=tools         # 你定义的工具列表
    )

    message = response.choices[0].message

    # 2. 判断是否有 Action（工具调用）
    if message.tool_calls:
        # === 这是 ReAct 的 Action 阶段 ===
        for tool_call in message.tool_calls:
            result = execute_tool(tool_call)  # 你的 Python 函数
            # 将结果以 observation 形式加入消息历史
            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "content": result  # === 这是 ReAct 的 Observation 阶段 ===
            })
    else:
        # === 没有工具调用，说明 ReAct 循环结束，这是最终 Answer ===
        return message.content

    step += 1
# 如果跳出循环还没结束，返回超时提示
```

**关键点**：在 ReAct 的官方论文里，`Thought` 通常要求模型输出 `Action:` 和 `Action Input:`。但在 OpenAI 的 `tool_calls` 机制下，`Thought` 被隐式包含在模型的推理过程中，而 `Action` 直接由结构化的 `tool_calls` 接管，省去了你解析文本的麻烦。

---

### 5. 为什么 ReAct 是必需的？（它解决了什么痛点）

如果没有 ReAct，你的 Function Calling 就只能是“一问一答”：

- _用户_：“帮我查北京天气，再算一下 3+5。”
- _模型_：（要么只查天气，要么只算数，**无法同时完成两个连贯的步骤**）。

有了 ReAct，模型会在内部进行如下思考链：

1.  先调天气工具 → 得到 35°C
2.  再调计算工具 → 得到 8
3.  最后组合回答：“北京 35°C，3+5=8。”

**结论：ReAct 赋予了模型“解决多步骤复杂任务”的能力，而不仅仅是“回答单轮问题”。**

---

### 6. 结合你之前的 Assistants API 疑问

你之前截图里的 `type: "retrieval"`，底层就是 OpenAI 帮你跑了一个 ReAct 循环：

- **Action**：查询向量数据库（检索知识库）。
- **Observation**：拿到匹配的文档片段。
- **Thought**：基于文档片段生成最终答案。

因为 OpenAI 把 ReAct 循环封装在了 Assistants API 内部，所以你只需要传 `tools`，不需要自己写 `while`。

---

### 💎 总结

**ReAct = 让 AI “边想边做，做完再看，看完再想”的决策闭环。**

在后续的学习中，你只需要记住：

- 如果你自己写 `while` 循环，你就是在**实现 ReAct**。
- 如果你用 LangGraph 的 `create_react_agent`，你就是在**使用封装好的 ReAct**。
- 如果你用 Coze 的工作流，你就是在**可视化地拖拽 ReAct 流程图**。

## OpenAI Assistants API

看到你代码中的 `"type": "retrieval"`，我必须先提醒你一个关键区别：**这是 OpenAI Assistants API（托管智能体）的专属写法**，和你之前学的 Chat Completions API（手写循环）不是同一个接口。

针对你的情况，分两种场景告诉你**“在哪里输入 Agent 描述”**：

---

### 场景一：如果你用的是 OpenAI Assistants API（对应你的 `type: "retrieval"`）

在 Assistants API 中，Agent 的“描述/人设/任务目标”是通过 **`instructions`** 参数传入的，它独立于 `tools` 之外。

```python
from openai import OpenAI
client = OpenAI()

# 1. 创建 Assistant（智能体）时，instructions 就是它的“灵魂描述”
file = client.files.create(file=open("course.txt", "rb"),
                                   purpose='assistants')
assistant = client.beta.assistants.create(
    name="智能客服专家",
    instructions="""你是一个资深售后客服助手。你的职责是：
    1. 优先使用知识库（retrieval）回答产品问题。
    2. 如果用户愤怒，先安抚情绪再解决问题。
    3. 严禁编造产品参数，必须基于检索结果回答。
    """,  # <--- 这就是 Agent 的描述/系统提示词
    model="gpt-4o",
    tools=[{"type": "retrieval"}]   # 给助理配置上你的业务知识
    ile_ids=[file.id]

)

# 2. 创建会话（Thread）并运行
thread = client.beta.threads.create()
message = client.beta.threads.messages.create(
    thread_id=thread.id,
    role="user",
    content="我的订单还没到"
)
run = client.beta.threads.runs.create(
    thread_id=thread.id,
    assistant_id=assistant.id,
    # 这里甚至可以临时覆盖 instructions（针对本次会话）
    instructions="请用简洁的英文回复"  # 覆盖上面默认的
)
```

**关键点**：`instructions` 不仅能在创建时写死，还能在每次 `run`（执行）时动态覆盖，非常灵活。

---

### 场景二：如果你在手写 ReAct 循环（Chat Completions API）

如果你没有用 Assistants API，而是用你之前学的 `openai.chat.completions.create` 手写 `while` 循环，那么 Agent 的“描述”就藏在你每次调用的 **`messages` 数组的 System Prompt** 里。

```python
messages = [
    {
        "role": "system",
        "content": "你是一个拥有工具调用能力的AI助手。你的任务是协助用户查询天气和计算。"
    },
    {
        "role": "user",
        "content": "北京今天热吗？"
    }
]

# 每次循环调用时，带上 tools 参数
response = client.chat.completions.create(
    model="gpt-4o",
    messages=messages,  # 描述就在 system 里
    tools=[  # 这里只能写 function，不能写 retrieval
        {
            "type": "function",
            "function": {
                "name": "get_weather",
                "description": "查询天气"
            }
        }
    ],
    tool_choice="auto"
)
```

---

### 核心区别与选择建议

| 维度           | Assistants API（托管）                                            | 手写 ReAct（自建）                                                            |
| :------------- | :---------------------------------------------------------------- | :---------------------------------------------------------------------------- |
| **描述传参**   | `instructions` 字段（独立于 tools）                               | `messages` 中的 `system` 角色                                                 |
| **知识库检索** | 直接写 `{"type": "retrieval"}`，上传文件即可，OpenAI 帮你做 RAG。 | 需自己用向量数据库（如 Chroma）+ 代码实现检索，再塞进 system 或 user 消息中。 |
| **状态管理**   | 自动管理 `Thread`（等同于 Redis 记忆），不需要你维护 history。    | 必须自己维护 `messages` 列表（可用 Redis 存）。                               |
| **适用场景**   | 快速原型、需要“文件上传问答”的场景。                              | 追求极致控制权、需要对接公司内部复杂工具（非 OpenAI 托管）的场景。            |

---

### 回到你的问题：如何写一个好的 Agent 描述？

不管是 `instructions` 还是 `system`，**描述的质量决定了 Agent 智能体的上限**。一个标准的 Agent 描述应该包含以下四个要素：

```python
instructions = """
1. 角色定义：你是 [角色名称]，负责 [核心职责]。
2. 工具使用规则：当用户问 [X] 时，必须优先调用 [工具A]；如果工具返回错误，转用 [工具B]。
3. 知识边界：如果知识库中没有相关信息，请直接告知用户“我暂时查不到，建议联系人工”，严禁胡编乱造。
4. 风格要求：回复必须使用 [简洁/热情/专业] 的语气，并在结尾加上 [emoji/感谢语]。
"""
```

---

### 针对你的代码（`type: "retrieval"`）的最终写法

如果你决定使用 Assistants API，完整的创建逻辑如下：

```python
assistant = client.beta.assistants.create(
    name="企业知识库顾问",
    instructions="你是一个企业知识库助手。请严格基于检索到的文档回答，如果文档中没有相关信息，请明确表示不知道。",
    tools=[{"type": "retrieval"}],
    model="gpt-4-turbo-preview",
    file_ids=["file-xxx"]  # 你上传的 PDF/Word 文件 ID
)
```

注意：这里的 `description` 字段（如果官网有）只是给开发者看的备注，**真正给 AI 读的是 `instructions`**。
