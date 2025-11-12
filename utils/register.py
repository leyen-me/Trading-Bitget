import atexit
import logging
from logging import Formatter
from flask import jsonify, send_from_directory
from config import Config
from flask_cors import CORS
from longport.openapi import (
    Config as LongPortConfig,
    TradeContext,
    QuoteContext,
    PushDepth,
    PushCandlestick,
    SubType,
    TradeSessions,
    Period,
)
from apscheduler.schedulers.background import BackgroundScheduler
from lib.MyFlask import DepthData, MyFlask
from routes.webhook import webhook_bp
from scheduler.account_cache_sch import fetch_and_cache_account_info
from scheduler.network_check_sch import check_all_sites
from scheduler.news_stream_sch import (
    fetch_and_analyze_news_fundamentals,
    fetch_news_only_for_warmup,
)

depth_cache: dict[str, DepthData] = {}
scheduler = BackgroundScheduler()


def add_job(
    app: MyFlask,
    id: str,
    name: str,
    func,
    seconds: int = 30,
    replace_existing: bool = True,
):
    """
    添加一个定时任务到后台调度器。

    该函数用于向应用的调度器中注册一个周期性执行的任务，使用固定的时间间隔触发。
    适用于需要定期执行的后台任务，如清理缓存、同步数据、健康检查等。

    参数:
        app: Flask 应用实例（或其他框架的应用对象），用于绑定配置或上下文（当前未直接使用，保留用于扩展）。
        id (str): 任务的唯一标识符。用于后续查找、修改或删除任务。
        name (str): 任务的可读名称，便于在日志或监控中识别。
        func: 要执行的函数对象（不能加括号，传递的是函数本身）。
        seconds (int, 默认 30): 执行任务的时间间隔（单位：秒）。默认每 30 秒执行一次。
        replace_existing (bool, 默认 True):
            如果为 True，当存在相同 id 的任务时，会替换旧任务；
            如果为 False，且任务 id 已存在，则会抛出 ConflictError 异常。

    示例:
        def my_backup_task():
            print("正在执行备份...")

        add_job(app, id="backup", name="Daily Backup", func=my_backup_task, seconds=3600)
    """
    scheduler.add_job(
        func=func,  # 指定要执行的函数
        trigger="interval",  # 触发器类型：固定时间间隔
        seconds=seconds,  # 执行间隔（秒）
        id=id,  # 任务唯一 ID
        name=name,  # 任务名称（显示用）
        replace_existing=replace_existing,  # 是否替换已存在的同 ID 任务
    )


def on_depth(symbol: str, event: PushDepth):
    global depth_cache
    depth_cache[symbol] = DepthData(ask=event.asks[0].price, bid=event.bids[0].price)


def setup_logging(app: MyFlask) -> None:

    # --- 自定义日志格式 ---
    log_level = None
    if not app.debug and not app.testing:
        log_level = logging.INFO
    else:
        log_level = logging.DEBUG

    # --- 清除默认的 handler（避免重复日志）---
    app.logger.handlers.clear()

    # --- 创建一个控制台 handler ---
    handler = logging.StreamHandler()
    handler.setLevel(log_level)

    # --- 定义格式：包含时间、日志级别、文件名/函数名、消息 ---
    # in %(module)s.%(funcName)s:%(lineno)d
    formatter = Formatter(
        "[%(asctime)s] %(levelname)s : %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)


def setup_cors(app: MyFlask):
    CORS(app)


def setup_home(app: MyFlask):
    @app.route("/")
    def serve_html():
        return send_from_directory("static", "index.html")


def setup_error_handlers(app: MyFlask):
    @app.errorhandler(404)
    def not_found(e):
        app.logger.error(f"404错误: {e}")
        return jsonify({"status": "error", "message": "资源未找到", "code": 404}), 404


def setup_blueprint(app: MyFlask):
    app.register_blueprint(blueprint=webhook_bp, url_prefix="/api")


def setup_scheduled_tasks(app: MyFlask):
    quote_ctx: QuoteContext = app.quote_ctx
    if Config.ENABLE_NEWS_STREAM:
        fetch_news_only_for_warmup(app)
        add_job(
            app=app,
            func=lambda: fetch_and_analyze_news_fundamentals(app),
            seconds=60,
            id="analyze_news_fundamentals_job",
            name="查询新闻基本面",
        )
    if Config.ENABLE_NETWORK_CHECK:
        check_all_sites()
        add_job(
            app=app,
            func=check_all_sites,
            seconds=60,
            id="check_all_sites_job",
            name="检查网络延迟",
        )
    if Config.ENABLE_PRICE_CACHE:
        global depth_cache
        fetch_and_cache_account_info(app)
        add_job(
            app=app,
            func=lambda: fetch_and_cache_account_info(app),
            seconds=30, # 高频可以设置为 5
            id="account_cache_job",
            name="缓存账户现金和持仓",
        )
        quote_ctx.set_on_depth(on_depth)
        quote_ctx.subscribe(
            Config.PRICE_CACHE_SYMBOL, [SubType.Depth], is_first_push=False
        )
        app.depth_cache = depth_cache
        

    # Flask 关闭时安全停止调度器
    @app.teardown_appcontext
    def shutdown_scheduler(exception=None):
        pass  # 不需要在这里处理，而是下面注册 atexit

    scheduler.start()

    # 确保 Flask 停止时也关闭 scheduler
    atexit.register(lambda: scheduler.shutdown())
