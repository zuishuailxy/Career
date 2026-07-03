import re
from agents.web_agent import lookup_v
from tool.scraping_tool import get_data
from tool.general_tool import remove_non_chinese_fields
from langchain_core.prompts import ChatPromptTemplate
from utils.models import create_llm
from tool.textgen_tool import generate_letter


def find_big_v(flower: str):
    # # 拿到包含 UID 的响应文本
    response_uid = lookup_v(flower_type=flower)
    print(f"原始响应: {response_uid}")

    # 从响应中抽取 UID 数字（匹配 weibo.com/u/ 后面的数字，或纯数字串）
    match = re.search(r"weibo\.com/u/(\d+)", response_uid)
    if match:
        uid = match.group(1)
    else:
        # 降级：提取响应中第一个长度合理的纯数字
        numbers = re.findall(r"\d+", response_uid)
        uid = numbers[0] if numbers else "未找到"

    print(f"这位鲜花大V的微博ID是: {uid}")

    # 根据UID爬取大V信息
    person_info = get_data(uid)

    # 移除无用的信息
    remove_non_chinese_fields(person_info)

    print(person_info)
    # 生成文案
    result = generate_letter(person_info)
    print("result", result)

    return result
