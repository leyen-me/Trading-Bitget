from flask import Blueprint, request, jsonify
import threading

from config import Config
from lib.MyFlask import get_current_app
from services.trade_service import (
    estimate_max_purchase_quantity,
    get_best_ask_price,
    get_best_bid_price,
    handle_contract_signal,
)

webhook_bp = Blueprint("webhook", __name__)


@webhook_bp.route("/webhook", methods=["POST"])
def receive_webhook():
    get_current_app().logger.info("收到来自 TradingView 的信号")
    payload = request.get_json()
    if not payload:
        return jsonify({"status": "error", "message": "无效请求"}), 400

    token = payload.get("token")
    expected_token = Config.WEBHOOK_EXPECTED_TOKEN

    if token != expected_token:
        get_current_app().logger.warning("Token 不匹配")
        return jsonify({"status": "error", "message": "token 不匹配"}), 401

    # 解析必要字段
    try:
        action = payload.get("action", "").lower()
        sentiment = payload.get("sentiment", "").lower()
        ticker = payload.get("ticker", "").upper()
        price = payload.get("price")

        # 参数校验
        if action not in ["buy", "sell"]:
            raise ValueError("无效的 action")
        if sentiment not in ["long", "short", "flat"]:
            raise ValueError("无效的 sentiment")

        app = get_current_app()._get_current_object()
        app_context = app.app_context()

        # 在后台线程处理交易逻辑，避免阻塞 HTTP 响应
        def background_task():
            with app_context:
                try:
                    handle_contract_signal(ticker, action, sentiment, price)
                except Exception as e:
                    get_current_app().logger.error(f"后台任务执行失败: {e}")

        thread = threading.Thread(target=background_task)
        thread.start()

        return jsonify({"status": "success", "message": "信号已接收，正在处理..."})

    except Exception as e:
        get_current_app().logger.error(f"解析信号失败: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400


@webhook_bp.route("/test_estimate_max_purchase_quantity", methods=["POST"])
def test_estimate_max_purchase_quantity():
    payload = request.get_json()
    if not payload:
        return jsonify({"status": "error", "message": "无效请求"}), 400
    ticker = payload.get("ticker", "").upper()
    price = payload.get("price")
    if not price:
        price = float(get_best_ask_price(ticker))
    max_buy = estimate_max_purchase_quantity(ticker, "buy", price)
    max_sell = estimate_max_purchase_quantity(ticker, "sell", price)
    return jsonify(
        {"status": "success", "max_buy": float(max_buy), "max_sell": float(max_sell)}
    )
