from langsmith import Client
from dotenv import load_dotenv
import os

load_dotenv()

# ---- LangSmith 配置 ----
os.environ["LANGSMITH_TRACING"] = "true"  # 必须显式设为 "true"
os.environ["LANGSMITH_PROJECT"] = "test"  # 项目名，必填！
os.environ["LANGSMITH_API_KEY"] = os.getenv("LANGSMITH_API_KEY", "")

client = Client()

# 创建一个数据集
examples = [
    ("Shut up,idiot", "Toxic"),  # 有害
    ("You're a wonderful person", "Not Toxic"),  # 无害("This is the worst thing ever","Toxic"), # 有害
    ("I had a great day today", "Not Toxic"),  # 无
    ("Nobody likes you", "Toxic"),  # 有害
    ("This is unacceptable. I want to speak to the manager.", "Not Toxic"),  # 无害
    ("大傻子.", "Toxic"),
    ("缺心眼.", "Toxic"),
]

# 数据集名称
dataset_name = "Toxic Queries"
dataset = client.create_dataset(dataset_name=dataset_name)
# 提取输入和输出
inputs, outputs = zip(*[({"text": text}, {"label": label}) for text, label in examples])


# 批量添加示例到数据集中
client.create_examples(
    dataset_id=dataset.id,
    inputs=inputs,
    outputs=outputs
)
