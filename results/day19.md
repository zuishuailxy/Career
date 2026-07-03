# LLM

## 预训练 + 微调的模式

- 预训练：在大规模无标注文本数据上进行模型的训练，目标是让模型学习自然语言的基础表达、上下文信息和语义知识，为后续任务提供一个通用的、丰富的语言表示基础。
- 微调：在预训练模型的基础上，可以根据特定的下游任务对模型进行微调。

## 输出解析

语言模型输出的是文本，这是给人类阅读的。但很多时候，你可能想要获得的是程序能够处理的结构化信息。这就是输出解析器发挥作用的地方。

输出解析器是一种专用于处理和构建语言模型响应的类。一个基本的输出解析器类通常需要实现两个核心方法。

### 核心工作流程

一个标准的输出解析器有两个核心方法：

1. **获取格式指令**：通过 get_format_instructions() 方法，获取一段描述所需输出格式的文本，需将其融入提示词（Prompt）中。

2. **解析输出**：通过 parse() 方法，接收 LLM 的原始输出，并将其转化为目标数据结构。

# Chain

想开发更复杂的应用程序，那么就需要通过 “Chain” 来链接 LangChain 的各个组件和功能——模型之间彼此链接，或模型与其他组件链接。

链（Chain） 是构建应用的核心概念。你可以把它理解为 一个可复用、可组合的“工作流流水线”。它将多个操作步骤（如调用模型、处理数据、调用工具等）连接起来，让数据在这些步骤间顺序传递。一个步骤的输出，会自动成为下一个步骤的输入

## 核心思想：从“零件”到“流水线”

在没有链的情况下，你需要手动管理每一步的输入输出，代码会变得复杂且难以维护。而链就像一条智能流水线：

- **标准化流程**：将提示词模板（Prompt）、模型（Model）、输出解析器（Parser）等组件串联起来。

- **数据自动流转**：前一步的输出自动成为后一步的输入。

- **封装复杂性**：将内部复杂逻辑封装起来，对外提供一个简单的调用接口。

## 现代实践：LCEL (LangChain 表达式语言)

LangChain 官方推荐的、也是目前最主流的构建链的方式。它使用管道符 | 来连接各个组件，语法非常简洁直观

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_deepseek import ChatDeepSeek

# 1. 定义提示词模板
prompt = ChatPromptTemplate.from_template("为 {city} 写一句简短的旅游宣传语。")

# 2. 初始化模型
model = ChatDeepSeek(model="deepseek-chat")

# 3. 初始化输出解析器
parser = StrOutputParser()

# 4. 用管道符 | 构建链
chain = prompt | model | parser

# 5. 调用链
response = chain.invoke({"city": "成都"})
print(response)
# 输出: "天府之国，美食之都，成都等你来！"
```
