# JSON Schema

JSON Schema 是用来描述和验证 JSON 数据结构的规范，本质上就是"用 JSON 来定义 JSON 长什么样"。

## 核心关键字

### 类型约束（type）

规定字段是什么数据类型，可选值有 string、number、integer、boolean、array、object、null。

### 字段定义（properties）

描述对象的每个属性，每个属性本身也是一个 Schema，可以无限嵌套。

### 必填字段（required）

是一个数组，列出哪些字段不可缺少：

```JSON
{
  "type": "object",
  "properties": {
    "name": { "type": "string" },
    "age":  { "type": "integer", "minimum": 0 }
  },
  "required": ["name"]
}
```

### 字符串约束

minLength、maxLength、pattern（正则），enum 限定枚举值：

```json
{
  "type": "string",
  "enum": ["low", "medium", "high"]
}
```

### 数组约束：

items 定义元素类型，minItems / maxItems 限制长度：

```json
{
  "type": "array",
  "items": { "type": "string" },
  "minItems": 1
}
```

## 和 Function Calling 的关系

schema = 工具说明书

Function Calling——工具定义里的 input_schema 就是 JSON Schema，模型看到它后知道该填什么参数、什么类型、哪些必填。description 字段尤其重要，模型会读它来理解每个参数的含义，写得越清晰，模型填参数越准确。

例如;

```json
{
  "name": "get_weather",
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

模型看到：这个函数需要一个 city 字符串; 于是输出

```json
{
  "city": "New York"
}
```

## 面试级总结

JSON Schema 是一种用于描述 JSON 数据结构的规范语言，用于定义字段类型、约束条件以及必填项。在大模型应用中，JSON Schema 通常用于约束模型输出格式，尤其是在 Function Calling 和 RAG 系统中，用来确保模型生成可解析、可执行的结构化数据，从而提升系统可靠性与工程可控性。

# Chat Completion

Chat Completion 是你与 GPT 交互的标准协议（API接口格式）。

## 1. 什么是 Chat Completion？

早期 GPT API 是把 对话表示为单个 Prompt，但是现实场景都是对话，需要记住前面聊过什么，所以出现了 Chat Completion

## 2. Chat Completion 的核心思想

把对话表示为：Message List， 而不是单个 Prompt

例如：

```json
[
  {
    "role": "system",
    "content": "你是一名Python专家"
  },
  {
    "role": "user",
    "content": "什么是FastAPI"
  }
]
```

模型返回：

```json
{
  "role": "assistant",
  "content": "FastAPI 是一个现代 Python Web 框架..."
}
```

## 3. Chat Completion 的数据结构

核心：messages是一组消息。

```json
{
  "messages": [
    {
      "role": "...",
      "content": "..."
    },
    ...
  ]
}
```

## 4. 三种最重要的 Role


### System

系统提示: 定义模型身份，全局规则

```json
{
  "role": "system",
  "content": "你是一位资深投资顾问"
}
```

### User

用户输入

```json
{
  "role": "user",
  "content": "分析联想集团"
}
```

### Assistant

历史回答

```json
{
  "role": "assistant",
  "content": "联想集团是一家..."
}
```

所以：

```
Chat Completion
=
Message History
```

## Chat Completion 的本质

每次请求把历史消息重新发给模型

即：

```
messages
↓
拼接上下文
↓
GPT
↓
新回答
```

Chat Completion 本质上是“带上下文的下一轮 Token 预测”。

## Function Calling 如何融入 Chat Completion？

```json
{
  "role": "tool",
  "content": "22°C Sunny"
}
```

把用户问题和工具结果一起发给模型

## 面试级回答

Chat Completion 是现代大语言模型最常见的交互接口形式，它通过 messages 数组组织 system、user 和 assistant 等不同角色的消息，从而支持多轮对话、上下文理解以及 Function Calling 等高级能力。本质上，Chat Completion 仍然是在历史消息上下文基础上的下一 Token 预测，但通过结构化消息机制实现了对话状态管理和 Agent 工作流支持。
