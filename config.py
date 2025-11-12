import os


def format_bool(s: str):
    return s.lower() in ("true", "1", "yes", "on")


def format_list(s: str):
    return s.split(",")


class Config:
    """
    配置类，从环境变量加载各项参数。
    具体作用请参考 README。
    """

    # ==================== 安全与认证 ====================
    WEBHOOK_EXPECTED_TOKEN = os.getenv("WEBHOOK_EXPECTED_TOKEN", "1234") # 调用 webhook 时的 token，用于安全认证，防止别人访问 webhook

    # ==================== Bitget API 配置 ====================
    BITGET_API_KEY = os.getenv("BITGET_API_KEY") # Bitget API Key
    BITGET_SECRET_KEY = os.getenv("BITGET_SECRET_KEY") # Bitget Secret Key
    BITGET_PASSPHRASE = os.getenv("BITGET_PASSPHRASE") # Bitget Passphrase
    BITGET_BASE_URL = os.getenv("BITGET_BASE_URL", "https://api.bitget.com") # Bitget API 基础地址

    # ==================== 交易相关 ====================
    MIN_PRICE_FILTER = float(os.getenv("MIN_PRICE_FILTER", "200")) # 最小开仓金额，小于此价格，便会全仓买入
    ORDER_CHECK_INTERVAL = int(os.getenv("ORDER_CHECK_INTERVAL", "60")) # 订单检查时间 1 分钟
    MAX_PURCHASE_RATIO = os.getenv("MAX_PURCHASE_RATIO", "0.5") # 每次交易的最大购买比例，即最多购买多少钱的合约