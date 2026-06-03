# 90 天可执行复习计划

## 总目标

围绕以下路线完成从前端工程师到 AI Full Stack Engineer 的第一轮能力迁移：

```text
LLM -> FastAPI -> PostgreSQL -> Redis -> RAG -> Agent -> Docker -> K8S -> MCP
```

90 天结束时，应至少具备以下产出：

* 一个 AI Chat Demo
* 一个 FastAPI 后端服务
* 一套 PostgreSQL + Redis 数据层
* 一个 RAG 企业知识库 Demo
* 一个 AI 投资分析 Agent 原型
* 一套 Docker Compose 本地部署方案
* 一份 K8S / MCP 基础认知总结
* 一版面向 AI Full Stack / Agent Engineer 的简历项目描述

---

## 每周固定节奏

工作日每天 1.5-2 小时：

* 30 分钟：核心概念复习
* 45-60 分钟：代码实践
* 15-30 分钟：复盘笔记 / 面试表达整理

周末每天 3-4 小时：

* 半天：补齐本周未完成内容
* 半天：完成阶段项目产出
* 30 分钟：整理项目 README 和面试话术

每周必须输出：

* 一份学习笔记
* 一个可运行或可展示的小产出
* 5 道面试题自测
* 一段项目表达，要求能写进简历或面试中复述

---

# 第 1-2 周：LLM 基础

## 阶段目标

理解大模型应用开发的基础概念，能完成最小 AI Chat Demo。

## 第 1 周：LLM 基础概念

Day 1：模型生态

* 了解 GPT、Claude、Gemini、DeepSeek 的定位差异
* 整理不同模型适合的应用场景
* 输出：模型对比笔记

Day 2：Token

* 理解 Token、上下文窗口、输入输出成本
* 练习估算一次对话的大致成本
* 输出：Token 与成本总结

Day 3：Temperature 与模型参数

* 理解 Temperature、Top-p、max_tokens
* 对比不同参数下回答稳定性
* 输出：参数实验记录

Day 4：System Prompt

* 理解 system / user / assistant message 的职责
* 写 3 个不同角色的 System Prompt
* 输出：Prompt 模板库初版

Day 5：Prompt Engineering

* 练习结构化提问、约束输出、分步骤推理
* 将一个模糊问题改写成高质量 Prompt
* 输出：Prompt 改写案例

Day 6：Few-shot

* 理解 zero-shot、one-shot、few-shot
* 为一个分类任务设计 few-shot 示例
* 输出：few-shot 示例集

Day 7：周复盘

* 总结 LLM 基础概念
* 准备 5 道面试题
* 输出：第 1 周复盘卡片

## 第 2 周：API 调用与 AI Chat

Day 8-9：模型 API 调用

* 学习 Chat Completion 基本调用
* 完成一次普通对话请求
* 输出：最小 API 调用脚本

Day 10：Streaming

* 学习流式输出
* 实现命令行或简单页面流式显示
* 输出：Streaming Demo

Day 11：Conversation Memory

* 理解短期对话记忆
* 实现基于 messages 数组的上下文传递
* 输出：多轮对话 Demo

Day 12：错误处理

* 处理超时、限流、模型异常、空响应
* 输出：错误处理清单

Day 13：AI Chat Demo 整合

* 整合普通对话、流式输出、多轮上下文
* 输出：AI Chat Demo 初版

Day 14：阶段复盘

* 梳理 LLM -> AI Chat 的完整链路
* 输出：可复述的面试回答

## 阶段验收

* 能解释 Prompt、Token、Temperature、Embedding、Function Calling 的作用
* 能独立调用模型 API
* 能完成一个最小 AI Chat Demo

---

# 第 3-4 周：FastAPI

## 阶段目标

把 AI Chat 从脚本升级成可被前端调用的后端服务。

## 第 3 周：FastAPI 基础服务

Day 15：FastAPI 项目结构

* 初始化 FastAPI 项目
* 理解 app、router、schema、service 分层
* 输出：后端项目骨架

Day 16：路由设计

* 设计 /chat、/sessions、/messages 接口
* 输出：接口清单

Day 17：Pydantic

* 使用 Pydantic 做请求和响应校验
* 输出：ChatRequest / ChatResponse schema

Day 18：服务层封装

* 把模型调用封装到 service 层
* 输出：LLMService

Day 19：流式接口

* 实现 FastAPI StreamingResponse
* 输出：流式聊天接口

Day 20：日志与错误处理

* 增加基础日志、异常捕获、统一错误响应
* 输出：错误响应规范

Day 21：周复盘

* 梳理 FastAPI 接口设计原则
* 输出：第 3 周复盘卡片

## 第 4 周：鉴权与后台任务

Day 22：JWT 基础

* 理解登录态、Token、过期时间
* 输出：JWT 学习笔记

Day 23：登录接口

* 实现简单登录和 Token 签发
* 输出：auth router

Day 24：Depends

* 使用 Depends 获取当前用户
* 输出：受保护的聊天接口

Day 25：Middleware

* 增加请求日志或耗时统计 Middleware
* 输出：请求追踪能力

Day 26：Background Task

* 学习后台任务
* 模拟异步保存对话记录
* 输出：后台任务 Demo

Day 27：AI Chat Backend 整合

* 整合鉴权、聊天、流式输出、错误处理
* 输出：AI Chat Backend

Day 28：阶段复盘

* 准备 FastAPI 面试题和项目表达
* 输出：FastAPI 阶段总结

## 阶段验收

* 能独立设计 AI 应用后端接口
* 能解释 FastAPI 在 AI 应用中的价值
* 能提供可被前端调用的 AI Chat Backend

---

# 第 5-6 周：PostgreSQL + Redis

## 阶段目标

补齐结构化数据、会话状态、缓存与限流能力。

## 第 5 周：PostgreSQL

Day 29：数据建模

* 设计 users、sessions、messages、tasks 表
* 输出：ERD 或表结构说明

Day 30：PostgreSQL 基础查询

* 练习增删改查、分页、排序
* 输出：SQL 练习脚本

Day 31：索引

* 理解主键、唯一索引、普通索引
* 输出：核心表索引设计

Day 32：FastAPI 集成数据库

* 接入 ORM 或数据库访问层
* 输出：会话保存接口

Day 33：消息记录

* 保存用户消息和模型回复
* 输出：messages 持久化能力

Day 34：查询优化基础

* 学习 explain 和慢查询定位思路
* 输出：查询优化笔记

Day 35：周复盘

* 总结 AI 应用中的数据建模
* 输出：PostgreSQL 面试题

## 第 6 周：Redis

Day 36：Redis 基础数据结构

* 学习 string、hash、list、set、zset 常见用法
* 输出：Redis 数据结构笔记

Day 37：缓存

* 为热点会话或配置增加缓存
* 输出：缓存 Demo

Day 38：TTL 与过期策略

* 实现短期上下文缓存
* 输出：带 TTL 的会话缓存

Day 39：Session

* 使用 Redis 管理登录态或会话状态
* 输出：Session 管理 Demo

Day 40：限流

* 实现简单 API 调用限流
* 输出：限流中间件或服务

Day 41：数据层整合

* PostgreSQL 存长期数据，Redis 存短期状态
* 输出：数据层职责说明

Day 42：阶段复盘

* 准备 PostgreSQL + Redis 面试表达
* 输出：第 5-6 周总结

## 阶段验收

* 能解释 PostgreSQL 和 Redis 的职责边界
* 能保存用户、会话、消息、任务数据
* 能落地缓存、Session、限流中的至少两项

---

# 第 7-8 周：RAG

## 阶段目标

完成一个能导入文档并基于文档问答的企业知识库 Demo。

## 第 7 周：RAG 基础链路

Day 43：RAG 总览

* 理解文档加载、切分、Embedding、入库、检索、生成
* 输出：RAG 全链路图

Day 44：文档加载

* 支持 Markdown / PDF / Word 中至少一种文档导入
* 输出：Document Loader Demo

Day 45：Chunk 切分

* 对比不同 chunk_size 和 overlap
* 输出：切分策略实验记录

Day 46：Embedding

* 调用 Embedding API
* 输出：文本向量化脚本

Day 47：向量库

* 使用 Chroma 或 Qdrant 存储向量
* 输出：向量入库 Demo

Day 48：相似度检索

* 实现 top-k 检索
* 输出：语义搜索 Demo

Day 49：周复盘

* 总结 RAG 为什么能解决知识增强问题
* 输出：RAG 面试题

## 第 8 周：文档问答 Demo

Day 50：检索增强 Prompt

* 把检索结果拼接进 Prompt
* 输出：RAG Prompt 模板

Day 51：引用来源

* 在回答中返回文档来源片段
* 输出：带引用的问答接口

Day 52：接口封装

* 用 FastAPI 封装 /documents、/query 接口
* 输出：RAG Backend

Day 53：前端简单页面

* 做一个上传文档和提问页面
* 输出：企业知识库页面

Day 54：错误与边界

* 处理无相关文档、文档过长、检索结果噪声
* 输出：RAG 边界处理清单

Day 55：Demo 整合

* 完成企业知识库 Demo
* 输出：可演示版本

Day 56：阶段复盘

* 整理 RAG 简历项目描述
* 输出：RAG 项目表达

## 阶段验收

* 能从 0 讲清 RAG 全链路
* 能展示文档导入、向量化、检索、生成回答
* 能说明向量库、切分策略、召回质量的重要性

---

# 第 9-10 周：Agent

## 阶段目标

完成 AI 投资分析 Agent 原型，具备状态、工具调用和多步骤工作流。

## 第 9 周：Agent 基础

Day 57：Agent 与 RAG 的区别

* 理解 Agent、Workflow、Tool Calling 的关系
* 输出：Agent 概念总结

Day 58：LangGraph 基础

* 学习 State、Node、Edge
* 输出：最小 LangGraph Demo

Day 59：状态设计

* 设计投资分析 Agent 的状态结构
* 输出：Agent State Schema

Day 60：节点设计

* 设计财报分析、新闻分析、风险分析、估值分析节点
* 输出：Node 设计文档

Day 61：工具调用

* 实现一个查询工具，例如数据库查询或股票信息查询
* 输出：Tool Calling Demo

Day 62：工作流串联

* 串起 2-3 个节点形成分析流程
* 输出：投资分析工作流初版

Day 63：周复盘

* 整理 Agent 面试题
* 输出：第 9 周总结

## 第 10 周：AI 投资分析 Agent

Day 64：财报分析节点

* 输入公司信息，输出基础财务分析
* 输出：财报分析 Node

Day 65：新闻分析节点

* 输入新闻摘要，输出影响判断
* 输出：新闻分析 Node

Day 66：风险分析节点

* 汇总业务风险、估值风险、市场风险
* 输出：风险分析 Node

Day 67：估值分析节点

* 输出估值假设和结论，不做绝对确定判断
* 输出：估值分析 Node

Day 68：报告生成

* 汇总多节点结果生成结构化报告
* 输出：投资分析报告

Day 69：错误恢复

* 处理工具失败、数据缺失、模型回答不完整
* 输出：兜底策略

Day 70：阶段复盘

* 整理 AI 投资分析 Agent 的项目介绍
* 输出：Agent 简历项目描述

## 阶段验收

* 能解释 Agent 和 RAG 的区别
* 能完成一个多步骤 Agent 工作流
* 能把项目讲成“AI 应用工程项目”，不是玩具 Demo

---

# 第 11 周：Docker

## 阶段目标

把项目打包成可复现、可部署的本地环境。

Day 71：Docker 基础

* 学习镜像、容器、Dockerfile
* 输出：Docker 基础笔记

Day 72：后端 Dockerfile

* 为 FastAPI 服务编写 Dockerfile
* 输出：后端镜像

Day 73：前端 Dockerfile

* 为 Vue3 项目编写构建和运行配置
* 输出：前端镜像

Day 74：PostgreSQL + Redis Compose

* 使用 Compose 启动数据库和缓存
* 输出：基础 compose 文件

Day 75：多服务联调

* 前端、后端、PostgreSQL、Redis 一起启动
* 输出：完整 compose 文件

Day 76：环境变量

* 整理 .env.example
* 输出：环境变量说明

Day 77：阶段复盘

* 写项目启动文档
* 输出：README 部署章节

## 阶段验收

* 能用 Docker Compose 一键启动核心服务
* 能解释容器化对协作、部署、复现环境的价值

---

# 第 12 周：K8S + MCP + 投递准备

## 阶段目标

建立部署和 Agent 工程化认知，同时开始准备简历和投递。

Day 78：K8S 基础概念

* 学习 Pod、Deployment、Service
* 输出：K8S 概念笔记

Day 79：配置管理

* 学习 ConfigMap、Secret、环境变量管理
* 输出：配置管理总结

Day 80：Ingress 与服务暴露

* 理解服务访问入口
* 输出：K8S 部署链路图

Day 81：基础部署清单

* 为 FastAPI 服务写一个 Deployment / Service 示例
* 输出：K8S yaml 初版

Day 82：MCP 基础

* 理解 MCP 的 Client / Server / Tool
* 输出：MCP 概念总结

Day 83：MCP Server Demo

* 设计一个最小工具服务，例如查询项目数据或读取本地知识库
* 输出：MCP Server 设计稿或 Demo

Day 84：周复盘

* 整理 K8S 和 MCP 的面试表达
* 输出：部署与协议层总结

---

# 第 13 周：项目收口与市场验证

## 阶段目标

把学习成果包装成能投递、能面试、能展示的材料。

Day 85：项目 README

* 为 AI 投资分析 Agent 写完整 README
* 包含背景、架构、技术栈、功能、启动方式

Day 86：架构图

* 画出 Vue3 / FastAPI / PostgreSQL / Redis / RAG / Agent / Docker 的整体架构
* 输出：项目架构图

Day 87：简历项目描述

* 写 2-3 条简历项目经历
* 强调 AI 应用、全栈、Agent、工程化

Day 88：面试题复盘

* 整理 LLM、FastAPI、PostgreSQL、Redis、RAG、Agent、Docker 的高频问题
* 输出：面试题清单

Day 89：模拟面试

* 按 AI Full Stack 岗位进行一轮模拟面试
* 标记薄弱点

Day 90：投递准备

* 完成简历初版
* 筛选目标岗位
* 开始小规模投递验证市场反馈

## 阶段验收

* 能展示一个完整 AI 应用项目
* 能讲清技术选型、架构、数据流、部署方式
* 能开始投递 AI Full Stack / 全栈偏 AI / Agent 应用相关岗位

---

# 每周复盘模板

```markdown
## 第 X 周复盘

### 本周完成

- 

### 本周产出

- 

### 掌握较好的点

- 

### 薄弱点

- 

### 面试表达

- 

### 下周重点

- 
```

---

# 投递岗位筛选标准

优先选择：

* AI 应用开发
* AI Full Stack
* Agent 应用开发
* 前端 + Node.js / Python / BFF
* 数据平台 + AI 能力接入
* RAG / 知识库 / 智能问答
* 内部工具平台 + LLM 能力

谨慎选择：

* 纯切页面前端
* 外包驻场
* 传统维护项目
* 完全没有后端或 AI 接入机会的岗位

目标不是马上离职，而是验证市场价格、获得选择权、寻找成长型团队。
