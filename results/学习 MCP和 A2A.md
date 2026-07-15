## 01｜开箱即用：MCP是LLM开发范式的增强

MCP（模型上下文协议）是一个开放标准，用于将 AI 连接到数据库和工具，就​​像专为 LLM 构建的 API 层一样。你可以将 MCP 想象成 AI 应用程序的“USB-C 接口”。正如 USB-C 为你的设备提供了连接各种外设的标准方式，MCP 为 AI 模型提供了连接不同数据源和工具的标准方式。

安装 MCP，并使用 mcp
用MotherDuck来帮我查询，并分析这个数据

## 02｜来而有往：A2A 协议是 Agent 之间的桥梁

A2A 和 MCP 是互补而非互斥关系 Agent2Agent（简称 A2A）协议应运而生，旨在为多 Agent 生态提供一套开放、标准、安全的互操作层，使不同厂商、不同平台上的 Agent 能够动态发现、调用并协同完成复杂任务，从而让 Agent 的生产力大幅上升，并优化成本。

A2A 与 MCP 各有专长，再加上 LLM，它们共同构成了一个完整的智能代理生态系统。正如下图所示，两者的关系可以这样理解：

- LLM：是 Agent 毫无疑问的“大脑”，负责处理信息，推理，做决策。
- MCP：负责模型与工具 / 资源的连接，是 Agent 的“手”，让 Agent 能够获取信息和执行操作。
- A2A：负责 Agent 之间的通信，是 Agent 的“嘴”，让 Agent 能够相互交流、协作完成任务。

A2A 的 5 大核心设计原则:

**第一是拥抱 Agent 能力**：A2A 不仅仅是将远端 Agent 视为工具调用，而是允许 Agent 以自由、非结构化的方式交换消息，支持跨内存、跨上下文的真实协作。

**第二是基于现有标准**：在 HTTP、Server-Sent Events、JSON-RPC 等成熟技术之上构建，确保与现有 IT 架构无缝集成。

**第三是企业级安全**：A2A 内置与 OpenAPI 同级别的认证与授权机制，满足企业级安全与合规需求。

**第四是长任务支持**：除了即时调用，还可管理需人机环节介入、耗时数小时甚至数天的深度研究任务，并实时反馈状态与结果。

**第五是多模态无差别**：不仅限于文本，还原生支持音频、视频、富表单、嵌入式 iframe 等多种交互形式。

A2A 协议定义了三个角色。

- 用户（User）：最终用户（人类或服务），使用 Agent 系统完成任务。
- 客户端（Client）：代表用户向远程 Agent 请求行动的实体。
- 远程 Agent（Remote Agent）：作为 A2A 服务器的“黑盒”Agent。

### A2A 协议的核心对象

A2A 协议设计了一套完整的对象体系，包括 Agent Card、Task、Artifact 和 Message。它们用于实现不同 Agent 之间的高效协作，这些核心对象相互配合，共同构成了 A2A 的通信框架。

### Agent Card（Agent 名片）

每个支持 A2A 的远程 Agent 需要发布一个 JSON 格式的 “Agent Card”，描述该 Agent 的能力和认证机制。Client 可以通过这些信息选择最适合的 Agent 来完成任务。

```json
{
  "name": "Google Maps Agent",
  "description": "Plan routes, remember places, and generate directions",
  "url": "https://maps-agent.google.com",
  "provider": {
    "organization": "Google",
    "url": "https://google.com"
  },
  "version": "1.0.0",
  "authentication": {
    "schemes": "OAuth2"
  },
  "defaultInputModes": ["text/plain"],
  "defaultOutputModes": ["text/plain", "application/html"],
  "capabilities": {
    "streaming": true,
    "pushNotifications": false
  },
  "skills": [
    {
      "id": "route-planner",
      "name": "Route planning",
      "description": "Helps plan routing between two locations",
      "tags": ["maps", "routing", "navigation"],
      "examples": [
        "plan my route from Sunnyvale to Mountain View",
        "what's the commute time from Sunnyvale to San Francisco at 9AM"
      ],
      "outputModes": ["application/html", "video/mp4"]
    }
  ]
}
```

### Task（任务）

Task 是 Client 和 Remote Agent 之间协作的核心概念。一个 Task 代表一个需要完成的任务，包含状态、历史记录和结果。

### Artifact（成果）

Artifact 是 Remote Agent 生成的任务结果。Artifact 可以有多个部分（parts），可以是文本、图像等。

### Message（消息）

Message 用于 Client 和 Remote Agent 之间的通信，可以包含指令、状态更新等内容。一个 Message 可以包含多个 parts，用于传递不同类型的内容。

## A2A 协议工作流程

接下来，我们通过 A2A 协议的工作流程和具体示例，来展示这些对象如何协同工作，完成 Agent 之间的对话。

A2A 协议的典型工作流程如下：

- 能力发现：每个 Agent 通过一个 JSON 格式的 “Agent Card” 公布自己能执行的能力（如检索文档、调度会议等）。
- 任务管理：Agent 间围绕一个 “task” 对象展开协作。该对象有生命周期、状态更新和最终产物（artifact），支持即时完成与长跑任务两种模式。
- 消息协作：双方可互发消息，携带上下文、用户指令或中间产物；消息中包含若干 “parts”，每个 part 都指明内容类型，便于双方就 UI 呈现形式（如图片、表单、视频）进行协商。
- 状态同步：通过 SSE 等机制，Client Agent 与 Remote Agent 保持实时状态同步，确保用户看到最新的进度和结果。

A2A 和 MCP 的互补关系：

MCP：提供垂直集成，将代理连接到工具和资源。
A2A：提供水平通信，将代理连接到其他代理。

## 03｜协议实战（上）：高德地图 + MiniMax语音开发私域旅游小助手

利用高德地图 MCP + minimax 的 语音合成功能

## 04｜协议实战（中）：从0到1，基于MCP快速搭建RAG“医疗健康“指北”

开发一套基于 MCP + FAISS 的 RAG 框架，这个 MCP 服务将具备端到端的索引、检索和工具提供能力，是一个非常清晰的原型 RAG 系统。

整个过程中 MCP 的通信机制明确分为三个阶段。

- 初始化阶段：客户端请求服务器的功能支持与协议版本。
- 通信阶段：客户端与服务器交换请求和通知，调用并执行工具。
- 终止阶段：安全结束通信，释放资源。

rag-server 把嵌入（Embedding）服务和检索（Retrieval）都以工具的形式通过 MCP 协议提供给 Client,因此我们的 MCP RAG 服务器就像是嵌入模型 + 向量数据库的结合

rag-client 生成仍由 Client 端的大模型来完成，此外，要进行嵌入的文档也由 Client 来提供给 MCP 服务。

## 05｜协议实战（下）：通过 A2A，你的智能体不仅能对话还可以协作！
