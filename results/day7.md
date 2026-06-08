# Embedding

## 什么是Embedding

本质是：把人类无法计算的文字、图片、音频等信息，转换成机器可以计算的数字向量。可能是几百维甚至几千维的向量。

## 为什么需要 Embedding？


计算机只认识数字

## Embedding 的核心目标

让语义越相似的信息，向量越接近，语义越不同，向量越远离。

## 什么是向量空间？

指一个满足特定规则的数学结构。里面的向量可以自由地相加和缩放，结果仍然待在同一个空间里。

多维空间

## Embedding 是怎么训练出来的？

核心思想：让经常一起出现的词拥有相似向量。

## GPT中Embedding的位置

```
文本
↓
Tokenizer
↓
Token
↓
Embedding
↓
Transformer
↓
预测
```

## Embedding 最重要的应用：RAG

假设知识库：

```
文档A：
FastAPI 是 Python Web 框架

文档B：
Vue 是前端框架

文档C：
PostgreSQL 是数据库
```

用户问：

```
FastAPI是什么？
```

系统先把问题 Embedding：

```
Query Vector
```

然后和知识库向量比较：

```
文档A ← 最接近
文档B ← 很远
文档C ← 很远
```

找到：

FastAPI 是 Python Web 框架

再交给 GPT。

这就是 RAG。

## 向量相似度

如何判断两个向量是否接近？ 

Cosine Similarity（余弦相似度）

计算两个向量夹角，角度越小，越相似，角度越大越不相似。 这种只考虑了方向。

点积（必须归一化）

点积越大 = 方向越接近 = 语义越相似； 既考虑方向，又考虑了大小。

点积是工程实践中的实际首选，因为：

- 主流 Embedding 模型（OpenAI text-embedding-3、Cohere、BGE、E5 等）输出的向量默认已归一化，此时点积 = 余弦相似度
- 点积计算量更小，对点积优化更好，检索更快

## 向量数据库

向量数据库是专门为存储和检索高维向量而设计的数据库

### 核心组成

索引层是向量数据库的关键，决定了检索速度。常见算法

- HNSW（Hierarchical Navigable Small World）：图结构索引，检索速度最快，内存占用大，是 Pinecone、Qdrant 默认选择
- IVF（Inverted File Index）：先聚类再搜索，内存友好，适合大规模数据
- PQ（Product Quantization）：向量压缩，牺牲少量精度换取极低内存，常与 IVF 结合（IVF-PQ）
- DiskANN：微软出品，向量存磁盘而非内存，适合超大规模场景

存储层保存两类数据：原始向量本身，以及与之绑定的元数据（如文档来源、时间、标签等）。

元数据过滤让你可以在向量检索的同时加条件，比如"只在 2024 年以后的文档里找"。有预过滤（先筛后搜）和后过滤（先搜后筛）两种策略，前者精度更高。

### 查询向量

ANN（近似最近邻） 而非精确搜索

向量数据库做的是**近似最近邻**搜索，而不是精确遍历所有向量——数百万向量精确算点积太慢，ANN 以极小的精度损失换取毫秒级响应。


### 工作流程

```
文档
↓
Embedding
↓
Vector DB

用户问题
↓
Embedding
↓
Similarity Search
↓
Top K(K=3~10)
↓
GPT
```

## Agent 为什么离不开 Embedding？

因为 Agent 要记忆。

使用过程中系统：

```
把历史记录Embedding
↓
向量检索
↓
找回相关记忆
```

这就是长期记忆机制的基础。


## 面试级回答


Embedding 是一种将文本、图片等非结构化数据映射到高维向量空间的技术，其目标是让语义相近的数据在向量空间中距离更近。GPT 在处理文本时，会先将 Token 转换为 Embedding 向量，再输入 Transformer 网络。Embedding 也是 RAG、向量数据库和 Agent Memory 的核心基础，通常结合余弦相似度进行语义检索，实现基于语义而非关键词的搜索能力。

面试题

Embedding有什么作用？

标准答案：

将非结构化文本转换为向量表示，
便于语义检索、
聚类、
推荐、
RAG召回。