# GPT 到底是什么

全称 Generative Pre-trained Transformer， 生成预训练transformer模型

G = Generative

核心能力不是分类，而是根据已有内容预测下一个token

P = Pre-trained（预训练）

模型预先读海量数据

预训练阶段学会：
- 语言规模
- 常识知识
- 编程知识
- 推理模式

T = Transformer

GPT 的核心神经网络结构。

Transformer 解决了一个关键问题：
如何理解一句话中不同单词之间的关系

Transformer 能通过 Attention 机制找到这种关联。
Transformer 是 GPT 的大脑结构，而 Self-Attention 是这个大脑最重要的神经回路。
Self-Attention让每个Token看到其它Token

Transformer 通过 Self-Attention 机制建模长距离上下文关系，是 GPT 的核心神经网络架构。

# GPT 本质在干什么？

本质是超大规模的“下一个 Token 预测器”，根据已有内容预测出现概率最高的下一个token.

Token 是大模型处理文本的最小单位。

# GPT 的训练过程

第一阶段：预训练（Pretraining）

给大模型喂海量数据，最终形成语言能力。

第二阶段：监督微调（SFT）

人工准备问答数据，模型学习如何回答问题，遵循指令

第三阶段：对齐训练（RLHF）

Reinforcement Learning from Human Feedback

人工比较哪个更好：

回答A
回答B

哪个更好：
B

模型不断优化



# 对Agent 开发的理解

GPT = 推理引擎

Agent 架构通常是：

用户
 ↓
LLM(GPT)
 ↓
工具调用(Function Calling)
 ↓
搜索
数据库
代码执行
RAG
MCP
API

面试题：

如果面试官问：

GPT 是什么？

你可以回答：

GPT（Generative Pre-trained Transformer）是一种基于 Transformer 架构的大语言模型。它通过海量文本进行预训练，本质上通过预测下一个 Token 来学习语言规律，并经过监督微调和人类反馈强化学习进行对齐。现代 GPT 不仅能生成文本，还能结合 Function Calling、RAG 和外部工具构建 Agent 系统，实现复杂任务的推理与执行。

GPT是基于 Transformer Decoder 的自回归语言模型，通过预测下一个 Token 来生成文本。