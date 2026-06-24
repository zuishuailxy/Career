from langchain_deepseek import ChatDeepSeek
from langchain_core.prompts import PromptTemplate

template = """您是一位专业的鲜花店文案撰写员。
对于售价为 {price} 元的 {flower_name} ，您能提供一个吸引人的简短描述吗？
"""
prompt = PromptTemplate.from_template(template)


# 推荐使用 deepseek-chat 模型，它功能最完整[reference:9]
llm = ChatDeepSeek(
    model="deepseek-chat",
    temperature=0.7,  # 控制随机性，范围 0-1[reference:10]
    max_tokens=None,  # 最大生成 token 数[reference:11]
    timeout=None,  # 请求超时时间[reference:12]
    max_retries=2,  # 最大重试次数[reference:13]
)

# 多种花的列表
flowers = ["玫瑰", "百合", "康乃馨"]
prices = ["50", "30", "20"]


for flower, price in zip(flowers, prices):
    # 得到模型的输出
    input = prompt.format(flower_name=flower, price=price)
    output = llm.invoke(input)
    # 打印输出内容
    print(output.content)
