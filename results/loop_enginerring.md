Loop Engineering（循环工程）是近两年 Agent 领域越来越重要的概念。

如果说：

- Prompt Engineering 决定 **模型怎么思考**
- Function Calling 决定 **模型怎么使用工具**
- RAG 决定 **模型怎么获取知识**

那么：

> **Loop Engineering 决定 Agent 如何持续执行任务，直到完成目标。**

它是现代 Agent（如 OpenAI Agents、LangGraph、AutoGen 等）的核心设计思想。

---

# 1. 为什么需要 Loop？

传统 ChatGPT 的工作方式：

```text
用户提问
    ↓
LLM
    ↓
回答结束
```

只有一次推理（One-shot）。

例如：

```text
用户：
北京天气怎么样？
```

模型：

```text
北京今天晴，28°C。
```

结束。

---

但现实中的任务往往不是一步完成。

例如：

```text
帮我规划一个日本旅行
```

需要：

- 查机票
- 查酒店
- 查天气
- 查签证
- 综合分析
- 输出方案

这不是一次调用能完成的。

---

于是需要：

```text
思考
↓
调用工具
↓
获得结果
↓
继续思考
↓
再调用工具
...
```

这就是 Loop。

---

# 2. Loop Engineering 是什么？

一句话：

> **Loop Engineering = 设计 Agent 的“思考 → 行动 → 观察 → 再思考”循环。**

经典流程：

```text
User
 ↓
Think
 ↓
Tool Call
 ↓
Observation
 ↓
Think
 ↓
Tool Call
 ↓
Observation
 ↓
Answer
```

---

# 3. 最经典的 Agent Loop

可以抽象为四步：

```text
Thought
    ↓
Action
    ↓
Observation
    ↓
Repeat
```

很多论文称之为：

> Thought → Action → Observation（TAO）

例如：

用户：

```text
分析苹果公司最近财报并总结风险
```

Agent：

### 第一步：Thought

```text
需要获取最新财报。
```

---

### 第二步：Action

调用：

```text
get_financial_report("Apple")
```

---

### 第三步：Observation

得到：

```text
收入增长5%
利润下降2%
```

---

### 第四步：Thought

```text
还需要分析风险。
```

再次调用新闻搜索。

最后综合输出。

---

# 4. Prompt Engineering vs Loop Engineering

这是很多人容易混淆的地方。

## Prompt Engineering

关注：

```text
一次 Prompt
```

例如：

```text
你是一位投资专家...
```

目标：

> 提高单次回答质量。

---

## Loop Engineering

关注：

```text
整个任务流程
```

例如：

```text
需要工具吗？
需要继续吗？
是否结束？
```

目标：

> 提高复杂任务完成能力。

---

# 5. 一个真实例子

用户：

```text
帮我预订明天去东京的航班。
```

Loop：

```text
LLM：
需要搜索航班

↓

search_flights()

↓

发现很多航班

↓

LLM：
选择价格最低

↓

book_ticket()

↓

成功

↓

LLM：
回复用户
```

如果没有 Loop：

模型只能说：

```text
建议你去某网站订票。
```

---

# 6. Loop 的终止条件

这是工程里必须考虑的问题。

什么时候结束？

通常有几种方式：

### 1）模型判断

模型输出：

```text
FINAL ANSWER
```

表示完成。

---

### 2）达到最大循环次数

例如：

```python
MAX_ITERATIONS = 10
```

避免无限循环。

---

### 3）工具返回成功

例如：

```text
订单创建成功
```

停止。

---

### 4）发生错误

例如：

```text
API调用失败
```

停止并返回错误。

---

# 7. Loop Engineering 在代码里的样子

伪代码：

```python
while True:

    response = llm(messages)

    if response.need_tool():

        result = call_tool(response.tool)

        messages.append(result)

        continue

    else:

        break
```

是不是很熟悉？

本质就是：

```text
while + LLM
```

---

# 8. 为什么说 Agent 本质就是 Loop？

可以把 Agent 简化成：

```text
while 未完成:

    思考()

    如果需要工具:
        调工具()

    更新上下文()

结束
```

所以很多人说：

> Agent = LLM + Tools + Memory + Loop

Loop 就是把这些能力串起来。

---

# 9. 与 RAG 的关系

RAG：

```text
Question
 ↓
Retrieve
 ↓
Generate
```

通常只有一次检索。

---

Loop Agent：

```text
Question
 ↓
Retrieve
 ↓
Generate
 ↓
Need More?
 ↓
Retrieve Again
 ↓
Generate
```

可以多轮检索。

例如：

```text
第一次找到文档A

↓

发现缺数据

↓

再找文档B

↓

继续分析
```

---

# 10. 为什么 Loop Engineering 越来越重要？

因为现代 Agent 已经不是：

```text
一次回答
```

而是：

```text
完成任务
```

例如：

- 写代码
- 调试代码
- 修改代码
- 再运行
- 再修改

整个过程就是：

```text
Loop
```

像 OpenAI Codex、Cursor、Claude Code 等开发工具，本质上都在循环执行：

```text
分析 → 修改 → 测试 → 再分析
```

---

# 11. 工业界常见的 Loop 设计

### 简单循环

```text
LLM
 ↓
Tool
 ↓
LLM
```

---

### 带 Memory

```text
LLM
 ↓
Tool
 ↓
Memory Update
 ↓
LLM
```

---

### 带 RAG

```text
LLM
 ↓
Retrieve
 ↓
LLM
 ↓
Tool
 ↓
LLM
```

---

### 多 Agent

```text
Planner
    ↓
Researcher
    ↓
Coder
    ↓
Reviewer
    ↓
Planner
```

每个 Agent 自己也可能运行一个 Loop。

---

# 12. 面试级回答

> Loop Engineering 是构建 AI Agent 的核心方法之一，它通过设计“思考（Thought）→ 行动（Action）→ 观察（Observation）→ 再思考”的循环，使模型能够持续调用工具、分析结果并逐步完成复杂任务，而不是依赖一次性生成答案。相比 Prompt Engineering 主要优化单次推理，Loop Engineering 更关注整个任务执行流程，因此是现代 Agent 系统的重要组成部分。

---

# 总结：把所有概念串起来

你已经学习了从 LLM 到 Agent 的核心知识，可以用下面这张图建立整体认知：

```text
                 用户输入
                     │
                     ▼
          Chat Completion（消息）
                     │
                     ▼
      System / Developer Prompt
                     │
                     ▼
        Prompt Engineering
                     │
                     ▼
          LLM（Transformer）
                     │
          ┌──────────┴──────────┐
          ▼                     ▼
     Function Calling        直接回答
          │
          ▼
     Tool / RAG / Database
          │
          ▼
      Observation（观察）
          │
          ▼
   Conversation Memory 更新
          │
          ▼
      Loop Engineering
          │
      是否完成任务？
       ├── 否：继续循环
       └── 是：输出最终结果
```

---

对于你的目标（成为 **AI 全栈 / Agent 开发工程师**），建议按照下面的学习顺序继续深入：

1. **Transformer 与 Attention**（模型原理）
2. **Embedding 与向量数据库**（RAG 基础）
3. **RAG 完整架构**（检索增强生成）
4. **Function Calling + JSON Schema**（工具调用）
5. **Memory 与 Loop Engineering**（Agent 核心）
6. **Agent Framework（LangGraph / OpenAI Agents 等）**（工程实现）

这条路线能够把模型原理、AI 应用开发和 Agent 系统设计串成一个完整的知识体系。
