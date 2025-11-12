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
    MODELSCOPE_API_KEY = os.getenv("MODELSCOPE_API_KEY") # 模型密钥，本项目默认使用 ModelScope，用于访问 AI 模型，处理 AI 逻辑

    # ==================== 交易相关 ====================
    MIN_PRICE_FILTER = float(os.getenv("MIN_PRICE_FILTER", "200")) # 最小开仓金额，小于此价格，便会全仓买入
    ORDER_CHECK_INTERVAL = int(os.getenv("ORDER_CHECK_INTERVAL", "60")) # 订单检查时间 1 分钟
    MAX_PURCHASE_RATIO = os.getenv("MAX_PURCHASE_RATIO", "0.5") # 每次交易的最大购买比例，即最多购买多少钱的股票
    
    # ==================== 消息通知 - QQ Bot ====================
    # QQ Bot 默认使用 napcat
    # https://napcat.apifox.cn/
    ENABLE_QQ_MSG = format_bool(os.getenv("ENABLE_QQ_MSG", "false")) # 是否启用 QQ 群消息通知
    MSG_QQ_BASE_URL = os.getenv("MSG_QQ_BASE_URL", "") # 部署好的 napcat 服务地址
    MSG_QQ_GROUP_ID = os.getenv("MSG_QQ_GROUP_ID", "") # QQ 群号
    MSG_QQ_TOKEN = os.getenv("MSG_QQ_TOKEN", "") # token

    # ==================== 消息通知 - QQ Email ====================
    ENABLE_EMAIL_MSG = format_bool(os.getenv("ENABLE_EMAIL_MSG", "false")) # 是否启用邮箱通知
    MSG_SMTP_USERNAME = os.getenv("MSG_SMTP_USERNAME") # 邮箱（发邮件和接收邮件都是用同一个）
    MSG_SMTP_PASSWORD = os.getenv("MSG_SMTP_PASSWORD") # 邮箱授权码

    # ==================== 定时任务 ====================
    ENABLE_PRICE_CACHE = format_bool(os.getenv("ENABLE_PRICE_CACHE", "false")) # 是否开启价格缓存，开启价格缓存后，会缓存价格，下次查询价格时直接从缓存中获取
    PRICE_CACHE_SYMBOL = format_list(os.getenv("PRICE_CACHE_SYMBOL", "TSLL.US,TSLQ.US")) # 需要缓存的股票
    ENABLE_NEWS_STREAM = format_bool(os.getenv("ENABLE_NEWS_STREAM", "false")) # 是否启用新闻推送，监测长桥的 7X24 新闻，使用 AI 分析并进行推送
    ENABLE_NETWORK_CHECK = format_bool(os.getenv("ENABLE_NETWORK_CHECK", "false")) # 是否启用网络检测，用于测试自己服务和 TradingView 和 LongPort 的网络延迟