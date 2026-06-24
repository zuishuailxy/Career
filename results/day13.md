## 前端流式渲染

**“流式渲染”**（Streaming Rendering）。结合你之前问的 SSE 和 ReadableStream，前端这边要做的不只是“接收数据”，更要**“平滑、高效地把文字画到屏幕上”**。

如果处理不当（比如每收到一个字就操作一次 DOM），页面会直接卡死。以下是前端流式渲染的三种实战方案，难度从低到高。

### 1. 基础方案：直接操作 textContent（适合纯文本）

如果你的后端返回的是纯文本块（没有 Markdown 格式），直接修改 DOM 节点的 `textContent` 是最快的方式。

```javascript
// 假设页面有一个 <div id="output"></div>
const outputEl = document.getElementById("output");

// 在读取流的循环中
while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  // 直接追加文本（只触发一次重排，比 innerHTML += 性能好）
  outputEl.textContent += chunk;
}
```

> **注意**：千万**不要**用 `outputEl.innerHTML += chunk`，这会导致整个 DOM 片段被反序列化、拼接再序列化，性能极差且容易引发 XSS 安全问题。

---

### 2. 进阶方案：requestAnimationFrame 节流（高并发推送下的保命技）

当网络很快时，`reader.read()` 可能在 1 毫秒内吐出几十个数据块。如果每块都更新 DOM，浏览器会疯狂重绘（Reflow），导致界面卡顿。

**核心思路**：维护一个“缓冲区”，用 `requestAnimationFrame`（跟随屏幕刷新率，约 16.7ms 一次）统一刷新。

```javascript
let buffer = "";
let pendingUpdate = false;
const outputEl = document.getElementById("output");

function flushBuffer() {
  if (buffer) {
    // 一次性将所有累积的文本追加进去
    outputEl.textContent += buffer;
    buffer = "";
  }
  pendingUpdate = false;
}

// 在读取流的循环中
while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  buffer += decoder.decode(value);

  // 如果当前帧没有安排更新，就安排一次
  if (!pendingUpdate) {
    pendingUpdate = true;
    requestAnimationFrame(flushBuffer);
  }
}
// 流结束后，确保最后一次残留的 buffer 刷出
flushBuffer();
```

---

### 3. 高级方案：流式 Markdown 渲染（AI 聊天标配）

现在的 AI 回答通常包含 Markdown 语法（`**加粗**`、`### 标题`、代码块）。如果直接把 Markdown 源码丢给 `innerHTML`，用户会看到一堆 `**` 符号，体验极差。

**难点**：Markdown 是上下文敏感的，比如 `**bo` 可能只是加粗语法的前半部分，如果立即渲染会破坏 HTML 结构。

**解决方案（策略）**：

1. **非阻塞渲染（业界主流）**：维护完整的累积文本，每次数据块到来时，**重新解析整个累积文本**，并用新的 HTML 替换 `innerHTML`。
   - 虽然看起来效率低，但现代浏览器配合 `requestAnimationFrame` 足以流畅处理每秒 10 次以内的重绘。
   - 注意：要在同一个 `requestAnimationFrame` 周期内完成解析和赋值，避免出现闪烁。

```javascript
// 使用 marked 或 marked.js 库
import { marked } from "marked";

let fullText = "";
let renderTimer = null;

function renderMarkdown() {
  // 将累积的全文转为 HTML
  const html = marked.parse(fullText);
  outputEl.innerHTML = html;
  // 滚动到底部
  outputEl.scrollTop = outputEl.scrollHeight;
}

// 循环接收 chunk
fullText += chunk;
clearTimeout(renderTimer);
// 防抖：如果用户停止输入 50ms，立即渲染；否则等待下一帧
renderTimer = setTimeout(() => {
  requestAnimationFrame(renderMarkdown);
}, 50);
```

2. **流式 Markdown 解析器（极客方案）**：使用 `micromark` 或 `remark` 的流式版本，它们会处理不完整的 AST（抽象语法树），但配置极其复杂，对于绝大多数场景，**“完整重解析 + 防抖”**已经足够。

---

### 4. 在 React / Vue 中的特殊注意点

如果你在用前端框架：

- **React**：**不要**用 `useState` 去更新每一个字！`setState` 会触发整个组件的 Diff 和重渲染，导致 UI 掉帧。
  - **正确姿势**：使用 `useRef` 挂载 DOM 节点，直接操作 `ref.current.textContent`，配合外部强制更新（或直接用 `flushSync`，但不推荐）。
  - 或者使用 `useDeferredValue` 将高频更新降级，但不如直接操作 DOM 来得干脆。

- **Vue**：同理，避免频繁修改 `ref` 响应式数据。直接操作 `template ref` 的 DOM，或者使用 `v-once` 配合手动更新。

---

### 5. 处理“光标闪烁”和“滚动锁定”

- **跟随滚动**：每次更新后，自动将容器滚动到底部（`scrollTop = scrollHeight`）。但如果用户手动向上滑动浏览历史，**不要强制滚动**，否则体验极差。需要设置一个 `isUserScrolling` 标志位。
- **输入光标（插入符）**：在流式渲染时，可以在文本末尾添加一个闪烁的 `<span class="cursor">|</span>`，并在每次渲染时保留它，模拟“正在输入”的呼吸感。

---

### 💎 总结：生产环境的最佳组合

| 场景                 | 推荐方案                                               |
| :------------------- | :----------------------------------------------------- |
| **简单聊天、纯文本** | `textContent` 直接追加 + 无额外处理                    |
| **高吞吐、超快流**   | `requestAnimationFrame` 缓冲区批量刷新                 |
| **带 Markdown 格式** | 全文重解析 + `setTimeout` 防抖 (50ms~100ms) + 保留光标 |
| **React/Vue 项目**   | `useRef` + 直接 DOM 操作，避开响应式更新陷阱           |

如果还需要考虑代码高亮（Prism.js 或 highlight.js），记得在渲染 Markdown 后异步调用高亮函数，且只高亮新增的代码块，避免全局高亮导致卡顿。如果你用的是具体哪个前端框架，或者遇到了渲染时的闪烁问题，可以告诉我具体情况，我再给针对性的调整建议。你提到的应该是**“流式渲染”**（Streaming Rendering）。结合你之前问的 SSE、ReadableStream 和 AI 对话场景，前端实现流式渲染的核心难点在于：**既要让文字“一个字一个字”地快速显示，又要保证页面不卡顿，还得处理 Markdown 等复杂格式**。

以下是前端处理流式渲染的**三种实战方案**，以及对应的性能优化技巧。

---

### 方案一：直接 DOM 操作（最基础，适合纯文本）

如果你的后端只返回纯文本（不包含 Markdown），直接修改 DOM 节点的 `textContent` 是最快的方式。

```javascript
// 假设页面有一个 <div id="output"></div>
const outputEl = document.getElementById("output");

// 在读取流的循环中 (fetch + ReadableStream)
while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  const chunk = decoder.decode(value);
  // ✅ 正确：直接追加文本，只触发一次重排
  outputEl.textContent += chunk;
}
```

> **⚠️ 严重避坑**：**绝对不要**使用 `outputEl.innerHTML += chunk`。这会导致整个 DOM 片段被反序列化、拼接再序列化，性能极差且极易引发 XSS 漏洞。

---

### 方案二：requestAnimationFrame 节流（高并发下的必备优化）

当网络很快时，`reader.read()` 可能在 **1 毫秒内吐出几十个数据块**。如果每块都更新 DOM，浏览器会疯狂重绘（Reflow），导致界面明显卡顿。

**解决思路**：维护一个“文本缓冲区”，利用 `requestAnimationFrame`（跟随屏幕刷新率，约 16.7ms 刷新一次）统一将缓冲区的内容刷到 DOM 上。

```javascript
let buffer = "";
let pendingUpdate = false;
const outputEl = document.getElementById("output");

function flushBuffer() {
  if (buffer) {
    // 一次性将所有累积的文本追加到界面
    outputEl.textContent += buffer;
    buffer = "";
  }
  pendingUpdate = false;
}

// 在读取流的循环中
while (true) {
  const { done, value } = await reader.read();
  if (done) break;

  buffer += decoder.decode(value);

  // 如果当前帧没有安排更新，就安排一次
  if (!pendingUpdate) {
    pendingUpdate = true;
    requestAnimationFrame(flushBuffer);
  }
}
// 流结束后，确保最后一次残留的 buffer 刷出
flushBuffer();
```

---

### 方案三：流式 Markdown 渲染（AI 聊天的标配）

现在的 AI 回答通常包含 Markdown 语法（`**加粗**`、`### 标题`、代码块）。如果直接把 Markdown 源码丢给用户，体验会非常差。

**难点**：Markdown 是上下文敏感的，比如 `**bo` 可能只是加粗语法的前半部分，如果立即渲染可能破坏 HTML 结构。

**业界主流策略（非阻塞渲染）**：
维护完整的累积文本，每次数据块到来时，**重新解析整个累积文本**，并用新的 HTML 替换 `innerHTML`。

```javascript
// 使用 marked 库 (或 highlight.js)
import { marked } from "marked";

let fullText = "";
let renderTimer = null;
const outputEl = document.getElementById("output");

function renderMarkdown() {
  // 将累积的全文转为 HTML
  const html = marked.parse(fullText);
  outputEl.innerHTML = html;
  // 自动滚动到底部
  outputEl.scrollTop = outputEl.scrollHeight;
}

// 循环接收 chunk
fullText += chunk;
// 防抖：停止接收数据 50ms 后，触发一次渲染
clearTimeout(renderTimer);
renderTimer = setTimeout(() => {
  requestAnimationFrame(renderMarkdown);
}, 50);
```

> **原理**：虽然“完整重解析”听起来低效，但配合 `setTimeout` 防抖（如 50ms）和 `requestAnimationFrame`，足以流畅应对每秒 10~20 次的更新。这比维护复杂的流式 AST（抽象语法树）要简单可靠得多。

---

### 在 React / Vue 中的特殊注意事项

如果你在使用前端框架，**千万不要**用响应式数据（如 `useState`、`ref`）去更新每一个字！

- **React 陷阱**：每调用一次 `setState`，都会触发组件 Diff 和重渲染。在 1 秒内调用 100 次 `setState`，浏览器必卡死。
- **正确做法（React）**：使用 `useRef` 获取 DOM 节点，**直接操作** `ref.current.textContent` 或 `innerHTML`，完全绕过 React 的响应式更新机制。

```jsx
const outputRef = useRef(null);

// 在流回调中直接操作
outputRef.current.textContent += chunk;
```

---

### 加分体验：处理“滚动锁定”与“光标闪烁”

1.  **智能滚动**：每次更新后自动滚动到底部。但如果用户手动向上滑动浏览历史，**必须停止自动滚动**。需要设置一个 `isUserScrolling` 标志位，监听 `scroll` 事件判断。
2.  **输入光标（插入符）**：在流式渲染时，可以在文本末尾添加一个闪烁的 `<span class="cursor">|</span>`，并在每次渲染时保留它（如果覆盖了 `innerHTML`，记得在末尾补回），模拟“正在输入”的呼吸感。

---

### 💎 总结：生产环境选型指南

| 你的场景                         | 推荐方案                                                               |
| :------------------------------- | :--------------------------------------------------------------------- |
| **纯文本聊天，数据量小**         | `textContent` 直接追加，不用做额外优化                                 |
| **高吞吐、超快流（如日志输出）** | `requestAnimationFrame` 缓冲区批量刷新                                 |
| **AI 对话（含 Markdown）**       | 全文重解析 + `setTimeout` 防抖 (50ms~100ms)                            |
| **React / Vue 项目**             | 使用 `useRef` / `template ref` 进行**命令式 DOM 操作**，避免响应式更新 |

如果你用的是具体的 UI 组件库（如 Ant Design、Element Plus），或者遇到了 Markdown 渲染时代码块高亮卡顿的问题，可以告诉我具体细节，我再给针对性的优化代码。

## HTTPX

**HTTPX 是一个功能全面的 Python HTTP 客户端库，可以看作是经典 Requests 库的“下一代”版本**。它与 Requests API 高度兼容，上手容易，同时提供了异步支持和 HTTP/2 等现代化特性。

### 🚀 快速上手

首先通过 pip 安装：

```bash
pip install httpx
```

#### 1. 同步请求（与 Requests 几乎一样）

如果你熟悉 Requests，那么使用 HTTPX 的同步 API 将毫无压力。

```python
import httpx

# 发送 GET 请求
response = httpx.get('https://api.example.com/data')
print(response.status_code)  # 200
print(response.json())       # 自动解析 JSON 响应
```

#### 2. 异步请求 (Async/Await)

这是 HTTPX 的核心优势之一，允许你编写高并发的代码。在 `async` 函数中，需要使用 `AsyncClient`。

```python
import httpx
import asyncio

async def main():
    async with httpx.AsyncClient() as client:
        response = await client.get('https://api.example.com/data')
        print(response.text)

# 在 Python 脚本中运行
asyncio.run(main())
```

### ✨ 核心特性

#### 1. 同步与异步的双重支持

这是 HTTPX 与 Requests 最根本的区别。HTTPX 提供了标准的同步 API，同时也提供了异步 API，让你能在同一个库中灵活选择。在处理大量 I/O 密集型任务（如并发请求多个 API）时，异步模式能显著提升性能。

#### 2. 支持 HTTP/2

HTTPX 原生支持 HTTP/2 协议，这是 Requests 所不具备的。HTTP/2 通过多路复用等特性，能有效降低延迟，提升网络性能。

#### 3. 连接池 (`Client`)

对于生产环境，强烈建议使用 `httpx.Client()`（同步）或 `httpx.AsyncClient()`（异步）来代替顶层的 `httpx.get()` 等方法。

- **更高的性能**：`Client` 对象会复用底层的 TCP 连接（连接池），避免了为每个请求重新建立连接的开销，显著提升性能。
- **共享配置**：你可以在创建 `Client` 时设置通用的请求头、认证信息、超时时间等，所有通过该客户端发出的请求都会自动应用这些配置。
- **推荐用法**：将 `Client` 作为上下文管理器使用，以确保连接被正确清理。
  ```python
  with httpx.Client(timeout=30.0, headers={'User-Agent': 'my-app'}) as client:
      r1 = client.get('https://api.example.com/endpoint1')
      r2 = client.get('https://api.example.com/endpoint2')
  ```

### 🆚 HTTPX vs Requests

| 特性           | HTTPX                   | Requests               |
| :------------- | :---------------------- | :--------------------- |
| **异步支持**   | ✅ 支持 (`AsyncClient`) | ❌ 不支持              |
| **HTTP/2**     | ✅ 支持                 | ❌ 不支持              |
| **连接池**     | ✅ 通过 `Client` 实现   | ✅ 通过 `Session` 实现 |
| **超时设置**   | ✅ 默认启用合理的超时   | ❌ 默认无超时          |
| **API 兼容性** | ✅ 与 Requests 高度相似 | -                      |
| **性能**       | 在异步场景下性能更优    | 同步场景下性能良好     |

### 💡 应用场景与最佳实践

1.  **在 FastAPI 等异步框架中使用**：这是 HTTPX 最典型的应用场景之一。在 FastAPI 的 `async` 路由中，必须使用异步 HTTP 客户端（如 `httpx.AsyncClient`）来发送请求，以避免阻塞事件循环。

    ```python
    from fastapi import FastAPI
    import httpx

    app = FastAPI()
    # 推荐在应用启动时创建一个全局的 AsyncClient 实例并复用
    client = httpx.AsyncClient()

    @app.on_event("shutdown")
    async def shutdown():
        await client.aclose()

    @app.get("/proxy")
    async def proxy():
        # 使用全局的 client 实例发送异步请求
        response = await client.get("https://api.example.com")
        return response.json()
    ```

2.  **并发执行多个请求**：利用 `asyncio.gather` 可以轻松实现多个请求的并发，极大提升程序效率。

    ```python
    import asyncio
    import httpx

    async def fetch_data(client, url):
        response = await client.get(url)
        return response.json()

    async def main():
        async with httpx.AsyncClient() as client:
            urls = ['https://api.example.com/item/1', 'https://api.example.com/item/2']
            # 并发执行所有请求
            results = await asyncio.gather(*[fetch_data(client, url) for url in urls])
            print(results)

    asyncio.run(main())
    ```

### 💎 总结

HTTPX 是一个现代化、功能强大且与 Requests 兼容的 HTTP 客户端。它不仅继承了 Requests 的易用性，还提供了异步支持和 HTTP/2 等关键特性。

对于新项目，特别是使用异步框架（如 FastAPI）的项目，HTTPX 是发送 HTTP 请求的理想选择。对于现有的 Requests 项目，迁移到 HTTPX 的成本也很低，并能立即享受到异步和 HTTP/2 带来的好处。
