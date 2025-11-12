from flask import Blueprint, request, jsonify
import threading

from config import Config
from lib.MyFlask import get_current_app
from services.trade_service import (
    estimate_max_purchase_quantity,
    handle_contract_signal,
)

webhook_bp = Blueprint("webhook", __name__)


@webhook_bp.route("/webhook", methods=["POST"])
def receive_webhook():
    """
    接收 TradingView Webhook 信号并触发合约交易
    
    请求参数:
        - token: 安全认证令牌
        - action: 交易动作 "buy" 或 "sell"
        - sentiment: 市场观点 "long", "short", "flat"
        - ticker: 合约交易对符号，如 "BTCUSDT"
        - leverage: 杠杆倍数（可选，默认 2）
        - position_ratio: 逐仓比例（可选，默认 0.1 即 10%）
    """
    logger = get_current_app().logger
    logger.info("📨 收到来自 TradingView 的信号")
    
    payload = request.get_json()
    if not payload:
        logger.error("❌ 无效请求：请求体为空")
        return jsonify({"status": "error", "message": "无效请求"}), 400

    token = payload.get("token")
    expected_token = Config.WEBHOOK_EXPECTED_TOKEN

    if token != expected_token:
        logger.warning("⚠️ Token 不匹配，拒绝请求")
        return jsonify({"status": "error", "message": "token 不匹配"}), 401

    # 解析必要字段
    try:
        action = payload.get("action", "").lower()
        sentiment = payload.get("sentiment", "").lower()
        ticker = payload.get("ticker", "").upper()
        
        # 杠杆倍数，默认 2 倍
        leverage = str(payload.get("leverage", Config.DEFAULT_LEVERAGE))
        
        # 逐仓比例，默认 10%
        position_ratio = float(payload.get("position_ratio", Config.DEFAULT_POSITION_RATIO))
        
        # 参数校验
        if action not in ["buy", "sell"]:
            raise ValueError(f"无效的 action: {action}，必须是 'buy' 或 'sell'")
        if sentiment not in ["long", "short", "flat"]:
            raise ValueError(f"无效的 sentiment: {sentiment}，必须是 'long', 'short' 或 'flat'")
        if not ticker:
            raise ValueError("ticker 不能为空")
        
        logger.info(
            f"📋 解析信号成功 | ticker: {ticker} | action: {action} | sentiment: {sentiment} | "
            f"leverage: {leverage}x | position_ratio: {position_ratio*100}%"
        )

        app = get_current_app()._get_current_object()
        app_context = app.app_context()

        # 在后台线程处理交易逻辑，避免阻塞 HTTP 响应
        def background_task():
            with app_context:
                try:
                    handle_contract_signal(ticker, action, sentiment, leverage, position_ratio)
                except Exception as e:
                    logger.error(f"❌ 后台任务执行失败: {e}", exc_info=True)

        thread = threading.Thread(target=background_task)
        thread.start()

        return jsonify({
            "status": "success", 
            "message": "信号已接收，正在处理...",
            "data": {
                "ticker": ticker,
                "action": action,
                "sentiment": sentiment,
                "leverage": leverage,
                "position_ratio": position_ratio
            }
        })

    except Exception as e:
        logger.error(f"❌ 解析信号失败: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400


@webhook_bp.route("/test_estimate_max_purchase_quantity", methods=["POST"])
def test_estimate_max_purchase_quantity():
    """
    测试接口：估算最大可购买数量
    
    请求参数:
        - ticker: 合约交易对符号
        - leverage: 杠杆倍数（可选，默认 2）
        - position_ratio: 逐仓比例（可选，默认 0.1）
    """
    logger = get_current_app().logger
    payload = request.get_json()
    if not payload:
        return jsonify({"status": "error", "message": "无效请求"}), 400
    
    ticker = payload.get("ticker", "").upper()
    leverage = str(payload.get("leverage", Config.DEFAULT_LEVERAGE))
    position_ratio = float(payload.get("position_ratio", Config.DEFAULT_POSITION_RATIO))
    
    try:
        logger.info(f"🧪 测试可开数量 | {ticker} | 杠杆: {leverage}x | 逐仓比例: {position_ratio*100}%")
        max_quantity = estimate_max_purchase_quantity(ticker, leverage, position_ratio)
        return jsonify({
            "status": "success",
            "max_quantity": float(max_quantity),
            "leverage": leverage,
            "position_ratio": position_ratio
        })
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}")
        return jsonify({"status": "error", "message": str(e)}), 400
