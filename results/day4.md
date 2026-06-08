# System Prompt

现代大模型的三层提示结构

System Prompt
    ↓
Developer Prompt
    ↓
User Prompt

模型会优先遵守 System，再遵守 Developer，最后响应 User。

## 第一层：System Prompt（系统提示）

最高优先级

作用：

定义模型是谁，能做什么，不能做什么。 给模型设定身份、行为规则、能力边界和输出风格的指令。

### System Prompt 常见内容

设定角色： 你是一名金融分析师
指定风格： 回答简洁
安全规则： 禁止提供违法内容
能力边界： 不知道时明确说明


## 第二层：Developer Prompt（开发者提示）

由应用开发者编写。

作用：

规定业务逻辑和产品行为

例如：

股票分析 Agent：

分析股票时必须：

1. 商业模式
2. 财务质量
3. 风险
4. 估值

按照固定格式输出。

## 第三层：User Prompt（用户提示）

最低优先级。就是用户输入


## 为什么 Prompt Engineering 很重要？

模型能力
=
基础模型能力
×
Prompt质量



## 面试级回答

如果面试官问：

什么是 System Prompt？

可以回答：

System Prompt 是发送给大语言模型的最高优先级指令，用于定义模型的角色、行为规范、输出格式和安全边界。在 Agent 架构中，System Prompt 通常负责设定 Agent 的身份和任务目标，是影响模型行为最重要的上下文之一。

冲突时怎么办？

System > Developer > User

三层结构

大模型通常采用三层提示结构：System Prompt、Developer Prompt 和 User Prompt。System Prompt 用于定义模型身份和全局规则，Developer Prompt 用于约束业务逻辑和输出格式，User Prompt 则是用户的具体请求。当指令发生冲突时，遵循 System > Developer > User 的优先级顺序。Agent 应用中的行为控制，本质上就是通过这三层提示共同实现的。


## 一个完整例子

### system

你是一位资深投资顾问。

必须遵守法律法规。

不能保证收益。

### developer

分析股票时：

1. 商业模式
2. 财务分析
3. 风险分析
4. 估值分析
5. 投资结论


### User

分析xx集团


一个完整的 LLM 请求实际上长这样：

[System Prompt]

你是谁
规则是什么

↓

[Developer Prompt]

业务逻辑
格式要求
工具调用规则

↓

[User Prompt]

用户问题

↓

LLM

↓

Response