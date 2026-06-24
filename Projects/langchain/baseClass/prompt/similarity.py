from ..utils import create_llm, create_embedding
from langchain_core.example_selectors import SemanticSimilarityExampleSelector
from langchain_core.prompts import FewShotPromptTemplate, PromptTemplate
from langchain_chroma import Chroma  # 或其他向量数据库

llm = create_llm()

embedding = create_embedding()
# 1. 定义示例列表
examples = [
    {
        "flower_type": "玫瑰",
        "occasion": "爱情",
        "ad_copy": "玫瑰，浪漫的象征，是你向心爱的人表达爱意的最佳选择。",
    },
    {
        "flower_type": "康乃馨",
        "occasion": "母亲节",
        "ad_copy": "康乃馨代表着母爱的纯洁与伟大，是母亲节赠送给母亲的完美礼物。",
    },
    {
        "flower_type": "百合",
        "occasion": "庆祝",
        "ad_copy": "百合象征着纯洁与高雅，是你庆祝特殊时刻的理想选择。",
    },
    {
        "flower_type": "向日葵",
        "occasion": "鼓励",
        "ad_copy": "向日葵象征着坚韧和乐观，是你鼓励亲朋好友的最好方式。",
    },
]

# 2. 定义每个示例的格式化模板
template = "鲜花类型: {flower_type}\n场合: {occasion}\n文案: {ad_copy}"
example_prompt = PromptTemplate(
    input_variables=["flower_type", "occasion", "ad_copy"], template=template
)

# 3. 创建 SemanticSimilarityExampleSelector
example_selector = SemanticSimilarityExampleSelector.from_examples(
    examples,  # 示例列表
    embedding,  # 用于生成向量的嵌入模型
    Chroma,  # 向量数据库
    k=1,  # 想要选择的示例数量
)
# 4. 创建 FewShotPromptTemplate，并传入 example_selector
similar_prompt = FewShotPromptTemplate(
    example_selector=example_selector,  # 使用动态选择器
    example_prompt=example_prompt,
    suffix="鲜花类型: {flower_type}\n场合: {occasion}",
    input_variables=["flower_type", "occasion"],
)

print(similar_prompt.format(flower_type="红玫瑰", occasion="爱情"))

chain = similar_prompt | llm
response = chain.invoke({"flower_type": "向日葵", "occasion": "鼓励"})
print(response.content)
