# Few-shot

## 什么是 Few-shot？

演进

```
Zero-shot
↓
One-shot
↓
Few-shot
```

### Zero-shot

不给任何例子, 直接提问

```
把下面句子翻译成英文：

我喜欢苹果
```

### One-shot

给一个例子：

```
中文：你好
英文：Hello

中文：我喜欢苹果
英文：
```

### Few-shot

给多个例子：

```
中文：你好
英文：Hello

中文：谢谢
英文：Thank you

中文：再见
英文：Goodbye

中文：我喜欢苹果
英文：
```

## Few-shot 到底在干什么？

它不是模型学习了规则，而是从上下文中识别模式（Pattern）

本质是模式补全（Pattern Completion），而不是重新学习（Learning）

## 为什么 Few-shot 有效？

因为 GPT 训练时看过无数：

```
问答
示例
教程
考试题
```

## Few-shot 在 Agent 中怎么用？

把例子放进 Prompt

developer prompt:

```
示例：

输入：
分析腾讯

输出：

# 商业模式
...

# 财务质量
...

# 风险
...

# 结论
...
```

## Few-shot 和 Fine-tuning 的区别

| 项目    | Few-shot | Fine-tuning |
| ----- | -------- | ----------- |
| 改模型参数 | ❌        | ✅           |
| 训练成本  | 无        | 高           |
| 实时生效  | ✅        | ❌           |
| 灵活性   | 高        | 中           |
| 部署复杂度 | 低        | 高           |


Few-shot：把例子放进 Prompt
Fine-tuning：把例子写进模型参数


## In-Context Learning

模型通过上下文中的示例,临时获得任务能力.这是 Few-shot 背后的核心概念。

## Few-shot 的最佳实践

### 1. 示例不要太多

一般 3~5个

### 2. 示例质量比数量重要

好示例

```
格式统一
风格统一
边界清晰
```

### 3. 覆盖边界情况

例如客服 Agent：
```
正常退款
异常退款
缺少订单号
```
都给示例。

## 面试级回答

Few-shot Prompting 是一种通过在提示词中提供少量示例，引导大语言模型模仿示例模式完成任务的技术。它不改变模型参数，而是利用模型的 In-Context Learning 能力，从上下文中识别输入输出模式并进行泛化。在实际应用中，Few-shot 常用于分类、信息抽取、格式化输出以及 Agent 工作流设计，是 Prompt Engineering 中最常用的方法之一。

面试题

Few-shot有什么作用？

答案：

降低模型理解成本，
提高输出一致性。