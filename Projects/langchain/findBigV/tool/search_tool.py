from langchain_community.tools import DuckDuckGoSearchRun
from langchain_core.tools import tool


@tool
def get_uid(flower: str) -> str:
    """搜索微博上某种鲜花相关大V的UID。
    先用不同策略多次搜索，尽可能找到包含 weibo.com/u/数字 的主页链接。
    输入鲜花名称如 '牡丹'。"""
    search = DuckDuckGoSearchRun()

    # 策略1：直接搜微博主页 UID 链接
    r1 = search.invoke(f"{flower} weibo.com/u/")
    # 策略2：搜微博用户/博主
    r2 = search.invoke(f"{flower} 微博 博主 大V")

    return f"[UID链接搜索]\n{r1}\n\n[博主账号搜索]\n{r2}"
