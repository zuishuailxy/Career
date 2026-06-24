````markdown
# 个人职业发展背景（2026）

## 基本信息

- 年龄：32岁

- Base：成都

- 学历：
  - 本科：生物医学工程

  - 硕士：机电信息一体化

- 公司：联想（成都）

- 职级：B6

- 年包：20W

- 涨薪：每年约3%-4%

## 技术背景

### 前端（主力）

- Vue2 / Vue3

- TypeScript

- JavaScript

- Pinia

- Vue Router

- Vite

- Jest

### 后端（有基础）

- Node.js

- Python

- PHP（历史全栈经验）

- MySQL

- PostgreSQL

- MongoDB

### AI

- 了解 AI 基础概念

- 希望转向 AI 应用开发

- 希望未来做 Agent 开发

---

# 当前职业状态分析

## 现状

长期在联想从事：

- 前端开发

- Vue 项目开发

- 日常需求迭代

缺少：

- 核心项目

- 新项目机会

- 技术决策权

- 与领导的深度沟通

## 组织信号

目前存在：

- 非领导心腹

- 与领导交流较少

- 接触不到新项目

- 技术成长趋缓

- 绩效下降

结论：

被裁员，目前失业

---

# 职业规划结论

## 不建议继续走

纯前端工程师路线

原因：

- 红利期已过

- 替代性越来越高

- 35岁后风险上升

---

## 推荐路线

```text

前端工程师

    ↓

全栈工程师

    ↓

AI Full Stack Engineer

    ↓

Agent Engineer
```
````

---

## 不推荐路线

```text

前端工程师

    ↓

机器学习工程师

```

原因：

需要与：

- 算法硕士

- 算法博士

直接竞争。

成本过高。

---

# 跳槽策略

## 当前结论

开始准备找工作

采取：

```text

骑驴找马

```

策略。

---

## 下一份工作选择原则

### 不要选择

- 纯切页面前端

- 外包

- 传统维护项目

---

### 优先选择

即使 title 是前端，也必须满足：

- Node.js

- BFF

- SSR

- AI能力接入

- 数据平台

- Python协作

- 全栈机会

至少满足其中两个。

---

# 未来目标

## 1年目标

薪资：

```text

20W

 ↓

30W+

```

职位：

```text

前端

 ↓

全栈方向

```

---

## 3年目标

薪资：

```text

40W+

```

定位：

```text

AI Full Stack Engineer

```

---

## 5年目标

定位：

```text

Agent Engineer

技术负责人

AI应用架构师

```

---

# AI 学习路线（按阶段执行版）

## 核心定位

学习：

```text

AI应用开发

```

而不是：

```text

AI算法研究

```

主线顺序：

```text

LLM

↓

FastAPI

↓

PostgreSQL

↓

Redis

↓

RAG

↓

Agent

↓

Docker

↓

K8S

↓

MCP

```

执行原则：

- 每个阶段都要有可展示产出，不能只停留在看概念。

- 每个阶段结束后，都要能回答“这个能力如何服务 AI 应用项目”。

- 复习前端基础只做保温，不再作为主线投入最多精力。

- 学习顺序遵循“先能做单体应用，再做复杂系统，再做工程化与协议层”。

---

## 阶段0：前端能力保温

定位：

不是主攻方向，只做维持，不让 Vue3 / TypeScript / 工程化能力退化。

保温内容：

- Vue3 组合式 API

- TypeScript 类型系统

- 浏览器原理

- 工程化与性能优化

执行要求：

- 每周安排 2-3 次短复习。

- 目标是保证面试能答、项目能写，而不是继续深挖纯前端细节。

---

## 阶段1：LLM 基础

阶段目标：

建立大模型应用开发的最小认知闭环，先把“会用模型”打牢。

重点学习：

- GPT / Claude / Gemini / DeepSeek 的差异

- Token

- Temperature

- System Prompt

- Prompt Engineering

- Few-shot

- Embedding

- Function Calling 基本概念

阶段产出：

- 一份自己的 LLM 基础总结

- 一个最小 AI Chat Demo

完成标准：

- 能解释 Prompt、Token、Temperature、Embedding、Function Calling 分别解决什么问题。

- 能独立调用模型 API，完成流式输出和基础报错处理。

不要偏离：

- 不深入算法训练细节。

- 不在模型评测和论文阅读上花过多时间。

---

## 阶段2：FastAPI

阶段目标：

把“会调模型”升级为“能做后端服务”。

重点学习：

- 路由设计

- Pydantic 数据校验

- Depends

- Middleware

- JWT

- Background Task

- 流式响应

- 错误处理与日志

阶段产出：

- 一个 AI Chat Backend

- 提供会话接口、流式接口、基础鉴权

完成标准：

- 能独立设计一个 AI 应用后端接口。

- 能解释为什么用 FastAPI，而不是只会写脚本。

---

## 阶段3：PostgreSQL

阶段目标：

建立结构化数据存储能力，让 AI 应用不再只是临时 Demo。

重点学习：

- 数据建模

- 表关系设计

- 索引

- 常见查询

- 查询优化

- 会话、用户、消息、任务等核心表设计

阶段产出：

- 为 AI Chat / AI 投资分析项目设计数据库 Schema

- 完成用户、会话、消息、任务记录表

完成标准：

- 能把业务需求转成表结构。

- 能说明哪些数据放 PostgreSQL，为什么放这里。

---

## 阶段4：Redis

阶段目标：

补上高频访问和临时状态管理能力。

重点学习：

- 缓存

- Session

- TTL

- 限流

- 简单消息队列

- 热点数据与短期上下文管理

阶段产出：

- 为 AI Chat / Agent 服务增加缓存与会话状态层

完成标准：

- 能解释 PostgreSQL 和 Redis 的职责边界。

- 能在项目中落地缓存、会话和限流中的至少两项。

---

## 阶段5：RAG

阶段目标：

从“通用模型调用”升级到“结合私有知识”的 AI 应用。

重点学习：

- LangChain

- Chroma / Qdrant

- Embedding 落库

- Chunk 切分

- 检索召回

- Prompt 拼接

- 文档问答链路

阶段产出：

- 一个支持 PDF / Word 文档问答的企业知识库 Demo

完成标准：

- 能从 0 讲清 RAG 全链路。

- 能解释为什么需要向量库，为什么检索质量会影响最终回答。

---

## 阶段6：Agent

阶段目标：

把单轮问答系统升级为具备流程、状态和工具调用能力的 Agent。

重点学习：

- LangGraph

- State

- Node

- Edge

- Workflow

- Tool Calling

- 多步骤任务编排

- 错误恢复与人工兜底

阶段产出：

- AI 投资分析 Agent

- 包含财报分析、新闻分析、风险分析、估值分析等基础能力

完成标准：

- 能解释 Agent 和 RAG 的区别。

- 能搭出带状态流转的多步骤工作流。

---

## 阶段7：Docker

阶段目标：

把本地项目变成可部署、可复现的运行环境。

重点学习：

- Dockerfile

- 镜像

- Compose

- 多服务联调

- 环境变量

- 基础部署

阶段产出：

- 将前端、FastAPI、PostgreSQL、Redis 打包为可运行的 Compose 项目

完成标准：

- 新机器上可以通过标准命令启动整个项目。

- 能解释容器化给 AI 应用开发带来的价值。

---

## 阶段8：K8S

阶段目标：

补齐部署视角，达到“懂协作、能沟通、知道怎么上线”的水平。

重点学习：

- Pod

- Deployment

- Service

- ConfigMap / Secret

- Ingress

- 基础扩缩容概念

阶段产出：

- 把核心服务整理出基础 K8S 部署清单

完成标准：

- 能看懂常见 K8S 部署配置。

- 能和后端 / 运维讨论部署结构，而不是完全陌生。

---

## 阶段9：MCP

阶段目标：

进入 Agent 工程化阶段，理解工具协议和系统扩展方式。

重点学习：

- MCP 的角色与价值

- Tool 暴露方式

- Client / Server 关系

- Agent 集成方式

- 与 A2A / Multi-Agent 的关系

阶段产出：

- 一个最小 MCP Server Demo

- 或者为自己的 Agent 项目设计可扩展工具层

完成标准：

- 能解释 MCP 为什么重要。

- 能把 MCP 放到 Agent 工程化的整体图景里。

---

# 当前最优行动计划（90天执行版）

## 第1阶段：第1-2周

主攻：

- LLM

- Prompt

- Embedding

- Function Calling 基础

产出：

- AI Chat Demo

- LLM 核心知识总结

验收：

- 可以独立讲清 LLM 应用开发基础链路。

---

## 第2阶段：第3-4周

主攻：

- FastAPI

- 接口设计

- JWT

- 流式输出

产出：

- AI Chat Backend

验收：

- 能独立提供可用 API 给前端调用。

---

## 第3阶段：第5-6周

主攻：

- PostgreSQL

- Redis

- 数据建模

- 缓存与会话管理

产出：

- 完成 AI 项目的数据库与缓存层

验收：

- 能把用户、消息、任务、缓存等核心数据链路跑通。

---

## 第4阶段：第7-8周

主攻：

- RAG

- LangChain

- 向量检索

- 文档问答

产出：

- 企业知识库 Demo

验收：

- 能展示从文档导入到回答生成的完整链路。

---

## 第5阶段：第9-10周

主攻：

- Agent

- LangGraph

- 工作流编排

- Tool Calling

产出：

- AI 投资分析 Agent

验收：

- 至少完成一个多步骤分析流程。

---

## 第6阶段：第11周

主攻：

- Docker

- Compose

- 服务部署

产出：

- 项目容器化运行

验收：

- 本地一键启动前后端、数据库、缓存服务。

---

## 第7阶段：第12周

主攻：

- K8S 基础认知

- MCP 基础认知

- 简历和项目表达

- 开始投递

目标：

不是马上离职。

而是：

```text

验证市场价格

获得选择权

寻找成长型团队

```

核心目标：

成为：

AI Full Stack Engineer → Agent Engineer

```



这个 Markdown 现在已经整理为按阶段执行版，可以直接作为后续复习、项目推进和投递准备的总纲。

```

详细执行计划：

```text

90-day-review-plan.md

```
