# Function Calling

Function Calling = 让 LLM 不只是说话，而是能“调用外部工具做事”。

Function Calling 是让 LLM 能够调用外部函数/工具的机制，是构建 AI Agent 的核心能力。

## 1. 为什么需要 Function Calling？

早期 GPT 只能做一件事：生成文本

它的问题是：

- 不能查实时数据（股票/天气）
- 不能操作数据库
- 不能调用API
- 不能执行业务逻辑

## 2. Function Calling 是什么？

让模型学会“决定什么时候调用什么函数 + 传什么参数”

Function Calling 做的是：

```
用户问题
   ↓
LLM判断
   ↓
是否需要调用工具？
   ↓
生成函数调用（不是自然语言）
   ↓
外部系统执行函数
   ↓
结果返回给LLM
   ↓
LLM组织最终回答
```

## 3. 一个真实例子

用户输入：

帮我查一下纽约天气

### Step 1：LLM 不直接回答

而是输出：

```json
{
  "function": "get_weather",
  "arguments": {
    "city": "New York"
  }
}
```

### Step 2：系统执行函数

```
get_weather("New York")
→ 22°C, Sunny
```

### Step 3：返回 LLM

Step 3：返回 LLM

## 4. Function Calling 的本质

LLM 负责“理解 + 决策”，工具负责“执行”。

| 模块              | 作用        |
| --------------- | --------- |
| LLM             | 判断该不该调用工具 |
| Function Schema | 定义工具能力    |
| External API    | 真正执行      |


### 关键要点

LLM 本身不执行函数，它只是输出"我想调用哪个函数、传什么参数"的结构化 JSON，真正执行的是你的代码。这个设计让 LLM 能够触达任何外部系统。

工具定义的核心是 JSON Schema，告诉模型函数叫什么、干什么、需要哪些参数：

```python

tools = [{
    "name": "get_weather",
    "description": "获取指定城市的当前天气",
    "input_schema": {
        "type": "object",
        "properties": {
            "city": {"type": "string", "description": "城市名称"}
        },
        "required": ["city"]
    }
}]
```

模型返回的不是文字，而是结构化的调用指令：

```json
{
  "type": "tool_use",
  "name": "get_weather",
  "input": { "city": "北京" }
}
```

你拿到这个之后，去真正调天气 API，把结果作为 tool_result 再发回给模型，模型才生成最终的自然语言回答。

### 在 RAG 里的位置

RAG 的"检索"步骤本质上就是一次 Function Calling——search_documents(query) 就是一个工具，模型决定调用它，你执行向量检索，把 Top-K 结果塞回去。

## 5. Function Calling 和 Prompt 的关系

Function Calling 本质上是：Prompt Engineering 的结构化升级版

普通 Prompt：

如果用户问天气，请调用天气API

问题：

- 模型可能忽略
- 参数不规范
- 不稳定

Function Calling：

系统强制输出结构化 JSON

优势：

- 稳定
- 可解析
- 可执行
- 工业级可靠

## 6. Function Schema（函数定义）

你要先告诉模型“有哪些工具”。

例如：

```json
{
  "name": "get_weather",
  "description": "获取城市天气",
  "parameters": {
    "type": "object",
    "properties": {
      "city": {
        "type": "string"
      }
    },
    "required": ["city"]
  }
}
```

模型会学习：

什么时候用这个函数
需要填什么参数

## 7. Function Calling 能做什么？

- 7.1 查询类
- 7.2 业务系统
- 7.3 工程系统
- 7.4 AI Agent
    例如： 帮我订一个上海到东京的机票
    流程:
    ```
    LLM → search_flights()
    LLM → select_flight()
    LLM → book_ticket()
    ```


## Function Calling vs Prompt


| 项目   | Prompt | Function Calling |
| ---- | ------ | ---------------- |
| 输出   | 自然语言   | 结构化JSON          |
| 可执行性 | 弱      | 强                |
| 稳定性  | 一般     | 高                |
| 工业级  | 不够     | 标准方案             |

## 面试级回答

Function Calling 是一种让大语言模型以结构化方式调用外部工具的机制。模型根据用户输入判断是否需要调用函数，并生成符合 schema 的参数，而实际执行由外部系统完成。该机制将“语言生成能力”扩展为“工具使用能力”，是构建 AI Agent 的核心基础之一。在架构上，它连接了 LLM 与外部 API，使模型从对话系统升级为可执行系统。