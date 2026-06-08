# Prompt Engineering

Prompt Engineering（提示词工程）:通过设计输入结构，稳定地控制大模型输出行为的一套工程方法论。

如果把 GPT 当成一个“概率引擎”，Prompt Engineering 就是：

如何用输入，稳定地“引导概率分布”, 让模型输出你想要的结果

## 1. Prompt Engineering 的本质

### 1.1 从模型角度理解

GPT做的事情是：在所有可能输出中，选概率最大的那个。

### 1.2 Prompt Engineering 的本质目标

改变“条件概率分布”，让目标答案概率更高


## 2. Prompt Engineering 在做什么？

可以拆成 4 个层级：

1. 角色（Who）
2. 任务（What）
3. 约束（How strict）
4. 输出结构（Format）


### 2.1 Role（角色设定）

让模型进入“语境空间”。

本质是激活不同语料分布区域


### 2.2 Task（任务定义）

告诉模型“做什么”。

例如：
基于价值投资框架分析联想集团是否值得长期持有
 
### 2.3 Constraints（约束）

约定大模型如何做

例如

必须包含：
- 商业模式
- 财务分析
- 风险
- 结论

### 2.4 Output Format（输出结构）

约定大模型回答的输出结构

例如：

```json
请以 JSON 输出：

{
  "conclusion": "",
  "risk": [],
  "valuation": ""
}
```

## 3.Prompt Engineering 的核心技术

### 3.1 Zero-shot Prompt

没有示例，直接提问

把下面句子翻译成英文

### 3.2 Few-shot Prompt（非常重要）

提问时候给例子

中文：我喜欢苹果
英文：I like apples

中文：今天天气很好
英文：

模型会“模仿模式”

本质

不是“理解规则”，而是：模式匹配 + 延续结构

### 3.3 Chain-of-Thought（思维链）

让模型“分步推理”。

例如

请一步一步思考

或者

先分析，再结论

#### 为什么有效？

强制它走“推理路径token分布”

### 3.4 Role + Instruction + Format（工业标准）


```md
你是xxx（Role）

任务：xxx（Task）

约束：
- xxx
- xxx

输出格式：
xxx
```

### 4. Prompt Engineering 在真实系统中的位置

在 agent / AI 应用中

```
User Input
   ↓
Prompt Engineering Layer
   ↓
LLM
   ↓
Tool / API
   ↓
Result
```

### 5. Prompt Engineering vs Fine-tuning

| 方法                 | 本质  | 成本 | 灵活性 |
| ------------------ | --- | -- | --- |
| Prompt Engineering | 改输入 | 低  | 高   |
| Fine-tuning        | 改模型 | 高  | 低   |

90% AI应用只需要 Prompt Engineering，不需要训练模型

### 6. Prompt Engineering 的三种能力等级

Level 1：会写 Prompt

帮我总结这段话

Level 2：结构化 Prompt

```
请按：
- 要点
- 总结
- 风险

输出
```

Level 3：系统化 Prompt（Agent级）

```
你是金融分析Agent

规则：
- 必须调用工具获取数据
- 不允许编造数字
- 输出必须JSON

流程：
1. 理解问题
2. 判断是否需要工具
3. 分析数据
4. 输出结构化结果
```

### 7. Prompt Engineering 的高级技巧（工业级）

#### 7.1 分层Prompt（System + Developer）

```
System：定义安全和身份
Developer：定义业务逻辑
User：问题
```

#### 7.2 反幻觉提示

```
如果不知道，请明确说“不确定”
```

#### 7.3 约束输出空间

```
只能从以下选项选择：
A / B / C
```

#### 7.4 结构稳定性优化

```
严格JSON输出，不要多余文本
```


### 面试


Prompt Engineering 是一种通过设计输入提示来控制大语言模型输出行为的工程方法。其核心包括角色设定（Role）、任务定义（Task）、约束控制（Constraints）和输出格式（Format）。本质上，Prompt Engineering 通过影响模型的条件概率分布，引导模型生成更符合预期的结果，而不是改变模型本身的参数。


总结

Prompt结构

最经典：

```
Role
Task
Constraint
Output
```