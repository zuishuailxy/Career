def get_stock_price(symbol: str) -> str:
    """模拟获取股票价格的函数"""
    # 这里可以替换为真实的API调用
    stock_prices = {"AAPL": "150.25", "GOOGL": "2800.50", "TSLA": "700.10"}
    return stock_prices.get(symbol.upper(), "未知股票")


tools = [
    {
        "type": "function",
        "function": {
            "name": "get_stock_price",
            "description": "获取指定股票代码的当前价格",  # 清晰的描述帮助模型决策
            "parameters": {
                "type": "object",
                "properties": {
                    "symbol": {
                        "type": "string",
                        "description": "股票的代码，例如 AAPL, GOOGL",
                    }
                },
                "required": ["symbol"],  # 必填参数
            },
        },
    }
]
