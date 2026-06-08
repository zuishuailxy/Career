# temperature 与模型参数

## Temperature 是什么？

Temperature 控制 GPT 输出的“随机性 / 发散程度”。它不改变模型能力，只改变“选择答案的策略”。


## Temperature 如何影响结果？

Temperature = 0（确定性）

几乎总选概率最大的

稳定
可重复
适合代码 / Agent 工具调用

Temperature = 0.7（默认常用）

概率重分布 + 一定随机性

特点：

平衡
最常用
ChatGPT 默认体验


Temperature = 1.2（高随机）
更敢选低概率 Token

特点：

创意强
不稳定
适合写作 / 文案 / brainstorming

## 本质数学理解（关键）


模型原始输出：logits
转换概率：softmax(logits / T)， T = Temperature

T越小。整体概率越大，越确定


# Top-p（nucleus sampling）

Top-p（核心采样）

只在概率前 p 的 token 中选择

Top-p = 0.9， 模型只保留 累积概率达到 90% 的候选

A 0.4
B 0.3
C 0.2
D 0.05
E 0.05

op-p = 0.8：只保留 A + B + C, D/E 直接丢掉。

Temperature vs Top-p

| 参数          | 控制什么     | 作用     |
| ----------- | -------- | ------ |
| Temperature | 分布“平滑程度” | 控制随机性  |
| Top-p       | 候选范围     | 控制搜索空间 |


## 实战建议

1. 代码 / Agent / Function Calling

temperature = 0 ~ 0.2
top_p = 1

原因：

保证稳定
避免 hallucination
tool 调用必须可靠

2. 知识问答

temperature = 0.3 ~ 0.7
top_p = 1

3. 创意生成

temperature = 0.8 ~ 1.2
top_p = 0.9

✅ 工业级做法

Router 模型（判断任务类型）
if tool_call:
    temperature = 0
elif reasoning:
    temperature = 0.3
elif writing:
    temperature = 0.8


## “模型参数”到底指什么？

1）模型参数（Model Weights）

数百亿 / 数千亿参数

是训练出来的，不是能调节的

2）推理参数（Inference Parameters）


| 参数                | 作用    |
| ----------------- | ----- |
| temperature       | 随机性   |
| top_p             | 采样范围  |
| max_tokens        | 输出长度  |
| frequency_penalty | 重复惩罚  |
| presence_penalty  | 新话题倾向 |


max_tokens

控制输出长度：
最多生成多少 Token


frequency_penalty

降低重复：
更少重复词

适合：
写文章
长文本


presence_penalty

鼓励新内容：
避免重复主题

适合：
brainstorming
创意生成


| 参数                | 关注什么   | 作用     |
| ----------------- | ------ | ------ |
| frequency_penalty | 出现了多少次 | 减少重复用词 |
| presence_penalty  | 是否出现过  | 鼓励新主题  |

常见在agent中,追求稳定

{
  "temperature": 0.2,
  "frequency_penalty": 0,
  "presence_penalty": 0
}

## 面试级回答

如果问：

Temperature 是什么？

可以这样答：

Temperature 是控制语言模型输出随机性的采样参数，它通过调整 softmax logits 的分布平滑程度影响 token 选择概率。较低 temperature 会使模型倾向于选择高概率 token，提高确定性与一致性；较高 temperature 则增加低概率 token 的选择机会，提高多样性与创造性。在工程实践中，通常在工具调用或代码生成场景使用低 temperature，在文本创作场景使用较高 temperature。

如果面试官问：

frequency_penalty 和 presence_penalty 的区别是什么？

可以回答：

frequency_penalty 根据 Token 在当前上下文中出现的次数进行惩罚，出现次数越多，后续再次生成的概率越低，主要用于减少重复措辞。presence_penalty 只关注 Token 是否出现过，一旦出现过就会施加惩罚，从而鼓励模型引入新的概念或主题。前者解决“重复说同样的话”，后者解决“总围绕同一个话题展开”。