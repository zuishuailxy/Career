# function_call机制

现在是Tools

OpenAI 的 Function Calling（现在通常称为 **Tools**）是一种让大模型能够调用外部函数或 API 的机制。它的核心是让模型**输出结构化的函数调用指令，而不是直接输出纯文本**。这使得你可以将大模型与各种外部系统（如数据库、API、业务逻辑）连接起来。

### ⚙️ 工作流程

Function Calling 的工作流程通常分为以下几步：

1.  **定义函数 (Define Functions)**：你首先需要用 **JSON Schema** 格式描述你的函数，包括函数名称、描述和参数（类型、是否必填等）。这些定义会通过 `tools` 参数传给模型。
2.  **模型决策 (Model Decides)**：模型收到用户问题和函数定义后，会判断是否需要调用函数来回答问题。如果需要，它会返回一个结构化的 `tool_calls` 对象。
3.  **你执行函数 (You Execute Function)**：你的代码解析模型返回的 `tool_calls`，获取函数名和参数，然后在你的后端安全地执行对应的真实函数。
4.  **返回结果 (Return Result)**：你可以将函数执行的结果再次发送给模型。模型会结合这些结果，生成一个最终的自然语言回复，返回给用户。

### 💻 完整代码示例：查询股票价格

下面通过一个查询股票价格的示例，展示完整的实现过程。

#### 1. 定义函数

首先，定义 `get_stock_price` 函数及其 JSON Schema 描述。

```python
import json
from openai import OpenAI

client = OpenAI()

# 1. 定义真实的函数
def get_stock_price(symbol: str) -> str:
    """模拟获取股票价格的函数"""
    # 这里可以替换为真实的API调用
    stock_prices = {"AAPL": "150.25", "GOOGL": "2800.50", "TSLA": "700.10"}
    return stock_prices.get(symbol.upper(), "未知股票")

# 2. 定义函数的 JSON Schema，用于传给模型
tools = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "获取指定股票代码的当前价格",  # 清晰的描述帮助模型决策
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "股票的代码，例如 AAPL, GOOGL",
                    }
                },
                "required": ["symbol"],  # 必填参数
            },
        },
    }
]
```

#### 2. 发起第一次请求

将用户问题与 `tools` 一起发送给模型。

```python
# 用户的问题
user_message = "苹果公司的股票现在多少钱？"

# 第一次调用模型
response = client.chat.completions.create(
    model="gpt-4o",  # 或 gpt-4-turbo 等支持function calling的模型
    messages=[{"role": "user", "content": user_message}],
    tools=tools,  # 传入函数定义
    tool_choice="auto",  # 让模型自动决定是否调用
)

# 获取模型的响应
response_message = response.choices[0].message
tool_calls = response_message.tool_calls
```

#### 3. 执行函数并处理结果

模型返回 `tool_calls` 后，你的代码解析并执行它。

```python
# 检查模型是否想要调用函数
if tool_calls:
    # 我们假设只处理第一个 tools call
    tool_call = tool_calls[0]
    function_name = tool_call.function.name
    function_args = json.loads(tool_call.function.arguments)  # 解析参数 JSON

    print(f"模型请求调用函数: {function_name}")
    print(f"函数参数: {function_args}")

    # 执行真实的函数
    if function_name == "get_stock_price":
        # 从解析出的参数中获取股票代码
        symbol = function_args.get("symbol")
        price = get_stock_price(symbol)  # 调用真实函数
        function_response = f"股票 {symbol} 的价格是 ${price}"

        print(f"函数执行结果: {function_response}")
```

#### 4. 将结果返回给模型（可选）

将函数执行结果作为新消息发给模型，让它生成最终的自然语言回复。

```python
    # 将函数结果作为新消息追加到对话中
    messages = [
        {"role": "user", "content": user_message},
        response_message,  # 模型的第一次响应（包含tool_calls）
        {
            "role": "tools",
            "tool_call_id": tool_call.id,  # 关联对应的 tool_call
            "content": function_response,  # 函数执行的结果
        },
    ]

    # 第二次调用模型，生成最终回复
    final_response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
    )

    print("\n最终回复:", final_response.choices[0].message.content)
else:
    # 如果模型没有要求调用函数，直接输出其回复
    print(response_message.content)
```

在这个例子中，模型会先返回调用 `get_stock_price` 的指令，你的代码执行后，将结果传回，模型最终生成一句自然语言回复，如“苹果公司（AAPL）的股票当前价格为 $150.25”。

### 🎮 核心控制参数：`tool_choice`

`tool_choice` 参数可以精确控制模型的调用行为。

- **`"auto"`（默认）**：模型自行判断是否需要调用函数。这是最灵活的方式，适用于通用对话场景。
- **`{"type": "function", "function": {"name": "函数名"}}`**：**强制**模型调用你指定的函数。适用于确定需要执行某个特定任务的场景。
- **`"none"`**：强制模型不调用任何函数，只进行纯文本回复。适用于不希望模型调用工具的场景。

### ⚠️ 重要提醒：`tools` 是标准用法

需要留意的是，`functions` 和 `function_call` 这些旧参数已经被 OpenAI **弃用**。现在和未来的开发都应使用 **`tools`** 和 **`tool_choice`** 这个新标准。

总而言之，Function Calling 是一种高效、可靠的方式，让大模型能够与外部世界交互，是构建各类 AI Agent 应用的关键技术。

### 📝 `tools`：定义可用的工具

`tools` 参数是一个对象数组，用于向模型声明所有可供调用的函数或工具。每个工具的定义都遵循一个固定的结构。

| 字段                                                 | 说明                                                                | 重要性       |
| :--------------------------------------------------- | :------------------------------------------------------------------ | :----------- |
| **`type`**                                           | 固定为 `"function"`，表示这是一个可调用的函数。                     | 必需         |
| **`function`**                                       | 包含函数具体定义的对象。                                            | 必需         |
| ↳ **`name`**                                         | 函数的唯一名称，模型通过此名称指定要调用的目标。                    | 必需         |
| ↳ **`description`**                                  | 函数的自然语言描述，**这是模型理解何时调用该函数的关键**。          | **强烈建议** |
| ↳ **`parameters`**                                   | 使用 **JSON Schema** 格式定义函数的参数。                           | 必需         |
| &nbsp;&nbsp;&nbsp;&nbsp;↳ **`type`**                 | 固定为 `"object"`。                                                 | 必需         |
| &nbsp;&nbsp;&nbsp;&nbsp;↳ **`properties`**           | 一个对象，定义每个参数的名称、类型（如 `string`、`number`）和描述。 | 必需         |
| &nbsp;&nbsp;&nbsp;&nbsp;↳ **`required`**             | 字符串数组，列出所有必填参数。                                      | 可选         |
| &nbsp;&nbsp;&nbsp;&nbsp;↳ **`additionalProperties`** | 建议设为 `false`，禁止模型生成未定义的参数。                        | **强烈建议** |
| ↳ **`strict`**                                       | 布尔值，建议设为 `true`，强制模型输出完全符合 Schema 的参数。       | **强烈建议** |

**代码示例：定义 `get_weather` 工具**

```python
tools = [{
    "type": "function",
    "function": {
        "name": "get_weather",
        "description": "查询指定城市的天气信息", # 清晰描述，帮助模型决策
        "strict": True, # 开启严格模式
        "parameters": {
            "type": "object",
            "properties": {
                "city": {
                    "type": "string",
                    "description": "城市名称，例如：北京"
                },
                "unit": {
                    "type": "string",
                    "enum": ["celsius", "fahrenheit"], # 限制输入枚举值
                    "description": "温度单位"
                }
            },
            "required": ["city"],
            "additionalProperties": False
        }
    }
}]
```

### 🎮 `tool_choice`：控制模型的调用行为

`tool_choice` 参数用于精确控制模型是否以及如何调用工具。它主要有三种取值：

| 取值                                                       | 行为                                         | 适用场景                                     |
| :--------------------------------------------------------- | :------------------------------------------- | :------------------------------------------- |
| **`"auto"`** (默认)                                        | 模型自主决定是调用工具还是直接回复文本。     | 绝大多数通用场景，将决策权交给模型。         |
| **`"none"`**                                               | 强制模型**不调用任何工具**，只生成文本回复。 | 当明确不需要工具交互时，确保模型只进行对话。 |
| **`{"type": "function", "function": {"name": "工具名"}}`** | 强制模型**必须调用**指定的那个工具。         | 需要引导对话流程，强制模型执行特定任务时。   |

**代码示例：强制调用 `get_weather`**

```python
tool_choice = {"type": "function", "function": {"name": "get_weather"}}
```

### ⚙️ 处理模型响应

当模型决定调用工具时，其响应中的 `message` 对象会包含 `tool_calls` 字段，而不是 `content`。

- **`tool_calls`**：一个数组，包含所有要调用的工具指令。
- **`id`**：本次调用的唯一标识符，后续将结果返回给模型时需要用到。
- **`function`**：包含要调用的 `name` 和 `arguments`（JSON 字符串格式）。

**响应示例**：

```json
{
  "choices": [{
    "message": {
      "role": "assistant",
      "content": null, # 无文本回复
      "tool_calls": [{
        "id": "call_abc123",
        "type": "function",
        "function": {
          "name": "get_weather",
          "arguments": "{\"city\": \"北京\"}" # 参数是 JSON 字符串
        }
      }]
    },
    "finish_reason": "tool_calls" # 结束原因为调用了工具
  }]
}
```

### 🚀 高级特性：并行函数调用

新标准支持**并行函数调用** (`parallel_tool_calls`)，允许模型在一次响应中返回多个工具调用请求。此功能默认开启。

**适用场景**：当用户询问“北京和上海的天气怎么样？”时，模型可以一次性返回两个 `get_weather` 的调用指令，你的后端可以并行执行它们，大幅提升效率。

### 💎 总结

`tools` 和 `tool_choice` 作为新标准，提供了更清晰、更强大的方式来让大模型与外部世界交互。

- **`tools`**：用于**声明**你可以提供给模型的所有“工具”（函数）。
- **`tool_choice`**：用于**控制**模型在何时、以何种方式使用这些工具。
- **响应**：模型通过 `tool_calls` 字段返回**结构化的调用指令**，而非自然语言。

建议在开发新应用时，统一采用以 `tools` 和 `tool_choice` 为核心的新标准，并开启 `strict` 模式以确保输出格式的可靠性。

# 例子

好的，我来用新的 `tools` 和 `tool_choice` 标准重写查询股票价格的示例，并对比旧版差异。

---

### 🔄 新版 vs 旧版核心变化

| 方面         | 旧版 (`functions`)      | 新版 (`tools`)                                             |
| ------------ | ----------------------- | ---------------------------------------------------------- |
| **参数名**   | `functions`             | `tools`                                                    |
| **控制参数** | `function_call`         | `tool_choice`                                              |
| **响应字段** | `function_call`（单个） | `tool_calls`（数组，支持并行）                             |
| **消息角色** | 无专用角色              | 新增 `tool` 角色，用于返回函数结果                         |
| **关联方式** | 无显式 ID               | 每个 `tool_call` 有唯一 `id`，后续需用 `tool_call_id` 关联 |
| **推荐配置** | 无严格模式              | 建议开启 `strict: true` 和 `additionalProperties: false`   |

---

### 🧩 新版完整代码示例（查询股票价格）

#### 1. 定义工具（使用 `tools`）

```python
import json
from openai import OpenAI

client = OpenAI()

# 真实的业务函数
def get_stock_price(symbol: str) -> str:
    stock_prices = {"AAPL": "150.25", "GOOGL": "2800.50", "TSLA": "700.10"}
    return stock_prices.get(symbol.upper(), "未知股票")

# 定义工具（新标准）
tools = [{
    "type": "function",
    "function": {
        "name": "get_stock_price",
        "description": "获取指定股票代码的当前价格",
        "strict": True,  # 推荐开启
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "股票代码，如 AAPL, GOOGL",
                }
            },
            "required": ["symbol"],
            "additionalProperties": False
        }
    }
}]
```

#### 2. 第一次请求：用户提问

```python
user_message = "苹果公司的股票现在多少钱？"

# 第一次调用模型
response = client.chat.completions.create(
    model="gpt-4o",
    messages=[{"role": "user", "content": user_message}],
    tools=tools,                # 传入工具定义
    tool_choice="auto",         # 让模型自主决定
)

# 获取模型返回的消息
response_message = response.choices[0].message
tool_calls = response_message.tool_calls
```

#### 3. 处理模型的工具调用请求

```python
if tool_calls:
    # 目前只处理第一个工具调用（可扩展并行）
    tool_call = tool_calls[0]
    function_name = tool_call.function.name
    function_args = json.loads(tool_call.function.arguments)

    print(f"模型请求调用: {function_name}，参数: {function_args}")

    # 执行具体函数
    if function_name == "get_stock_price":
        symbol = function_args.get("symbol")
        price = get_stock_price(symbol)
        function_response = f"股票 {symbol} 的价格是 ${price}"
        print(f"函数执行结果: {function_response}")
```

#### 4. 将结果返回给模型（生成最终自然语言回复）

```python
    # 构造新的消息列表，包含：
    # - 原始用户消息
    # - 模型的工具调用请求（包含 tool_calls）
    # - 工具执行结果（使用专用 role="tools"）
    messages = [
        {"role": "user", "content": user_message},
        response_message,  # 这里包含 tool_calls
        {
            "role": "tools",
            "tool_call_id": tool_call.id,  # 必须与对应的 tool_call id 匹配
            "content": function_response,
        }
    ]

    # 第二次调用模型，生成最终回复
    final_response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
    )

    print("\n最终回复:", final_response.choices[0].message.content)
else:
    # 没有工具调用，直接输出模型的文本回复
    print(response_message.content)
```

---

### 🔍 关键点解释

1. **`tool_calls` 是数组**：即使在简单场景下可能只有一个，也必须按数组方式处理。这为并行调用（`parallel_tool_calls=True`）打下了基础。

2. **`tool` 角色与 `tool_call_id`**：当你把函数执行结果传回模型时，必须使用 `role="tool"`，并通过 `tool_call_id` 与原始调用对应。这样模型才能正确关联结果和请求。

3. **`strict` 与 `additionalProperties`**：强烈建议开启 `strict: true` 并设置 `additionalProperties: false`，这样模型会严格遵守参数 Schema，避免生成额外字段或错误类型，提高程序健壮性。

4. **`tool_choice` 的用法**：
   - `"auto"` —— 让模型自己判断是否调用工具（最常用）。
   - `"none"` —— 强制模型不要调用任何工具（纯文本）。
   - `{"type": "function", "function": {"name": "get_stock_price"}}` —— 强制模型必须调用该工具。

5. **并行工具调用**：默认情况下 `parallel_tool_calls` 为 `true`。如果用户问“苹果和谷歌的股票价格”，模型可能一次性返回两个 `tool_calls`，你的后端可以并发执行它们，提升效率。

---

### 📦 完整脚本（含异常处理）

```python
import json
from openai import OpenAI

client = OpenAI()

def get_stock_price(symbol: str) -> str:
    prices = {"AAPL": "150.25", "GOOGL": "2800.50", "TSLA": "700.10"}
    return prices.get(symbol.upper(), "未知股票")

tools = [{
    "type": "function",
    "function": {
        "name": "get_stock_price",
        "description": "获取指定股票代码的当前价格",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {
                    "type": "string",
                    "description": "股票代码，如 AAPL, GOOGL",
                }
            },
            "required": ["symbol"],
            "additionalProperties": False
        }
    }
}]

def chat_with_stock(user_input):
    messages = [{"role": "user", "content": user_input}]

    # 第一轮：获取模型是否要调用工具
    response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
        tools=tools,
        tool_choice="auto",
    )
    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    # 如果没有工具调用，直接返回内容
    if not tool_calls:
        return response_message.content

    # 处理工具调用
    messages.append(response_message)  # 添加模型的消息（含 tool_calls）
    for tool_call in tool_calls:
        func_name = tool_call.function.name
        func_args = json.loads(tool_call.function.arguments)
        if func_name == "get_stock_price":
            result = get_stock_price(**func_args)
        else:
            result = "未知函数"
        # 添加工具执行结果
        messages.append({
            "role": "tools",
            "tool_call_id": tool_call.id,
            "content": result,
        })

    # 第二轮：生成最终回复
    final_response = client.chat.completions.create(
        model="gpt-4o",
        messages=messages,
    )
    return final_response.choices[0].message.content

# 测试
print(chat_with_stock("苹果的股价是多少？"))
```

---

### 💎 总结

使用新标准 `tools` 和 `tool_choice` 后，代码更清晰、更健壮，并支持并行工具调用和严格的参数校验。建议所有新项目都采用此标准，并逐步迁移旧代码。
