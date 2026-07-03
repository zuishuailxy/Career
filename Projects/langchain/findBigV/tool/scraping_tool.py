import json
import time
import requests


def get_data(uid: str) -> dict:
    """根据微博 UID 爬取用户资料（微博 API 反爬严格，可能不稳定）。

    Cookie 获取方式：
    1. 浏览器登录 weibo.com
    2. F12 → Application → Cookies → weibo.com → 复制 SUB 的值
    3. 写入 .env: WEIBO_COOKIE="SUB=你的SUB值; SUBP=你的SUBP值"
    """
    import os
    from dotenv import load_dotenv

    load_dotenv()

    cookie_str = os.getenv("WEIBO_COOKIE", "")
    if not cookie_str:
        raise ValueError("请在 .env 中设置 WEIBO_COOKIE")

    # 解析 cookie
    cookies = {}
    for item in cookie_str.split("; "):
        if "=" in item:
            k, v = item.split("=", 1)
            cookies[k] = v

    # 提取 XSRF-TOKEN（微博 AJAX 接口必须）
    xsrf = cookies.get("XSRF-TOKEN", "")

    session = requests.Session()
    session.cookies.update(cookies)

    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Referer": f"https://weibo.com/u/{uid}",
        "X-Requested-With": "XMLHttpRequest",
        "X-XSRF-TOKEN": xsrf,
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        ),
    }

    # 第一步：先访问用户主页，让微博建立正常的浏览会话
    print(f"[1/2] 访问主页 https://weibo.com/u/{uid} ...")
    r1 = session.get(
        f"https://weibo.com/u/{uid}",
        headers={k: v for k, v in headers.items() if k != "X-Requested-With"},
        timeout=15,
    )
    print(f"     主页状态码: {r1.status_code}, URL: {r1.url[:80]}...")
    time.sleep(2)

    # 第二步：调用 AJAX 接口获取资料
    print(f"[2/2] 请求 AJAX 接口 ...")
    api_url = f"https://weibo.com/ajax/profile/detail?uid={uid}"
    r2 = session.get(api_url, headers=headers, timeout=15)

    # 诊断输出
    print(f"     AJAX 状态码: {r2.status_code}")
    if r2.status_code != 200 or "passport" in r2.url.lower():
        # 尝试 mobile API 降级
        print(f"[降级] 尝试手机版 API ...")
        m_url = f"https://m.weibo.cn/api/container/getIndex?type=uid&value={uid}"
        r2 = session.get(
            m_url, headers={"User-Agent": headers["User-Agent"]}, timeout=15
        )
        print(f"     Mobile API 状态码: {r2.status_code}")

    try:
        data = r2.json()
        print(
            f"     获取成功，数据键: {list(data.keys()) if isinstance(data, dict) else type(data).__name__}"
        )
        return data
    except json.JSONDecodeError:
        snippet = r2.text[:300]
        raise RuntimeError(
            f"JSON 解析失败（retcode=6102 表示触发了反爬验证）。\n"
            f"状态码: {r2.status_code}, 响应: {snippet}\n\n"
            f"建议：\n"
            f"1. 确保 Cookie 是最新的（刚登录后立即复制）\n"
            f"2. 确保 Cookie 中包含 SUB、SUBP、XSRF-TOKEN\n"
            f"3. 如仍失败，考虑用 Playwright 模拟真实浏览器"
        )
