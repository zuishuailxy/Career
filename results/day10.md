# Streaming（流式输出）

## 1. 什么是 Streaming？

Streaming = 模型生成一个 Token，就立刻返回给客户端，而不是等全部生成完再返回。

## 2. 为什么 Streaming 很重要？

1. 大模型就是根据一个token去预测一个token，本身也是流式生成的。Streaming 其实更符合 GPT 的工作方式。

2. 一次性生成，用户需要等待一段时间，才能看到输出，用户体验不好

## Streaming 在前端中的实现

### Server-Sent Events（SSE）

最常用。

### WebSocket

双向通信

## 底层协议 ： SSE

Streaming 基于 Server-Sent Events（SSE），响应的 Content-Type 是 text/event-stream，每个 chunk 格式如下：

```
data: {"choices":[{"delta":{"content":"今天"},"finish_reason":null}]}

data: {"choices":[{"delta":{"content":"天气"},"finish_reason":null}]}

data: [DONE]
```

### finish_reason 的处理

流结束时最后一个 chunk 的 finish_reason 会告诉你原因，需要区分处理：

| finish_reason | 含义            | 处理方式                    |
| ------------- | --------------- | --------------------------- |
| `stop`        | 正常结束        | 正常展示                    |
| `length`      | 撞上 max_tokens | 提示用户回答被截断          |
| `tool_calls`  | 模型要调用工具  | 解析 tool_calls，执行后继续 |

### 实践建议

前端展示时，直接把每个 chunk 追加到 DOM 上，配合光标动画（`▌`），用户体验会接近 ChatGPT 的效果。对于 Function Calling + Streaming 的组合，需要先把所有 `tool_calls` 的 chunk 拼完整再执行，不能边收边执行。

## Streaming 的挑战

### 1. 内容不完整

前端要处理：Partial Output

### 2. JSON 可能不完整

避免不是合法json

```
Function Calling
通常先缓冲
再解析
```

### 3. 中断

用户点击：停止生成, 需要：取消连接

## AI 面试高频题

为什么 Streaming 能提升体验？

答：

因为 GPT 本身是逐 Token 生成的，Streaming 允许模型生成一个 Token 就立即返回给客户端，从而显著降低首 Token 延迟（TTFT，Time To First Token），虽然总生成时间不变，但用户感知速度明显提升。

面试级总结

Streaming 是一种流式生成机制，允许大语言模型在生成过程中实时返回 Token 或文本片段，而无需等待完整响应生成结束。它能够显著降低首 Token 延迟（TTFT），提升用户交互体验。在工程实践中，通常结合 SSE 或 WebSocket 实现前后端实时通信，是 ChatGPT、Agent 和 AI Copilot 等产品的标准能力。

## 前端处理流式数据块的核心步骤：

1. 使用 fetch 获取响应，通过 response.body.getReader() 获取读取器。

2. 循环调用 reader.read()，每次获取一个 Uint8Array 数据块。

3. 用 TextDecoder 将二进制转换为字符串，并处理可能跨块的不完整消息。

4. 根据后端约定的格式（如 SSE 的 data: 或纯文本），提取有效内容并逐步更新界面。

这样就能实现类似 ChatGPT 的逐字输出效果，大幅提升交互体验。
