from flask import Blueprint, request, jsonify
from utils.bitget_client import BitgetClient
from lib.MyFlask import get_current_app

test_bitget_bp = Blueprint("test_bitget", __name__)


@test_bitget_bp.route("/test/get_account_info", methods=["POST"])
def test_get_account_info():
    """
    测试接口：获取账户信息
    
    请求参数:
        - product_type: 产品线类型（可选，默认 "umcbl"）
    """
    logger = get_current_app().logger
    payload = request.get_json() or {}
    
    try:
        product_type = payload.get("product_type", "umcbl")
        logger.info(f"🧪 测试获取账户信息 | product_type: {product_type}")
        
        client = BitgetClient()
        result = client.get_account_info(product_type)
        
        return jsonify({
            "status": "success",
            "data": result,
            "product_type": product_type
        })
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 400


@test_bitget_bp.route("/test/get_position", methods=["POST"])
def test_get_position():
    """
    测试接口：获取单个合约仓位信息
    
    请求参数:
        - symbol: 合约交易对符号，如 "BTCUSDT"
        - margin_coin: 保证金币种（可选，默认 "USDT"）
    """
    logger = get_current_app().logger
    payload = request.get_json()
    
    if not payload or not payload.get("symbol"):
        return jsonify({"status": "error", "message": "symbol 参数必填"}), 400
    
    try:
        symbol = payload.get("symbol", "").upper()
        margin_coin = payload.get("margin_coin", "USDT")
        logger.info(f"🧪 测试获取单个仓位 | symbol: {symbol} | margin_coin: {margin_coin}")
        
        client = BitgetClient()
        result = client.get_position(symbol, margin_coin)
        
        return jsonify({
            "status": "success",
            "data": result,
            "symbol": symbol,
            "margin_coin": margin_coin
        })
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 400


@test_bitget_bp.route("/test/get_all_positions", methods=["POST"])
def test_get_all_positions():
    """
    测试接口：获取全部合约仓位信息
    
    请求参数:
        - product_type: 产品线类型（可选，默认 "umcbl"）
        - margin_coin: 保证金币种（可选，默认 "USDT"）
    """
    logger = get_current_app().logger
    payload = request.get_json() or {}
    
    try:
        product_type = payload.get("product_type", "umcbl")
        margin_coin = payload.get("margin_coin", "USDT")
        logger.info(f"🧪 测试获取全部仓位 | product_type: {product_type} | margin_coin: {margin_coin}")
        
        client = BitgetClient()
        result = client.get_all_positions(product_type, margin_coin)
        
        return jsonify({
            "status": "success",
            "data": result,
            "product_type": product_type,
            "margin_coin": margin_coin
        })
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 400


@test_bitget_bp.route("/test/get_ticker", methods=["POST"])
def test_get_ticker():
    """
    测试接口：获取单个Ticker行情
    
    请求参数:
        - symbol: 合约交易对符号，如 "BTCUSDT"
    """
    logger = get_current_app().logger
    payload = request.get_json()
    
    if not payload or not payload.get("symbol"):
        return jsonify({"status": "error", "message": "symbol 参数必填"}), 400
    
    try:
        symbol = payload.get("symbol", "").upper()
        logger.info(f"🧪 测试获取Ticker行情 | symbol: {symbol}")
        
        client = BitgetClient()
        result = client.get_ticker(symbol)
        
        return jsonify({
            "status": "success",
            "data": result,
            "symbol": symbol
        })
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 400


@test_bitget_bp.route("/test/get_depth", methods=["POST"])
def test_get_depth():
    """
    测试接口：获取深度行情
    
    请求参数:
        - symbol: 合约交易对符号，如 "BTCUSDT"
        - limit: 深度数量（可选，默认 5）
    """
    logger = get_current_app().logger
    payload = request.get_json()
    
    if not payload or not payload.get("symbol"):
        return jsonify({"status": "error", "message": "symbol 参数必填"}), 400
    
    try:
        symbol = payload.get("symbol", "").upper()
        limit = int(payload.get("limit", 5))
        logger.info(f"🧪 测试获取深度行情 | symbol: {symbol} | limit: {limit}")
        
        client = BitgetClient()
        result = client.get_depth(symbol, limit)
        
        return jsonify({
            "status": "success",
            "data": result,
            "symbol": symbol,
            "limit": limit
        })
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 400


@test_bitget_bp.route("/test/place_order", methods=["POST"])
def test_place_order():
    """
    测试接口：下单
    
    请求参数:
        - symbol: 合约交易对符号，如 "BTCUSDT"
        - side: 交易方向 "open_long", "open_short", "close_long", "close_short"
        - order_type: 订单类型 "limit" 或 "market"
        - size: 下单数量
        - price: 限价单价格（order_type为"limit"时必填）
        - product_type: 产品线类型（可选，默认 "umcbl"）
        - margin_coin: 保证金币种（可选，默认 "USDT"）
        - margin_mode: 保证金模式（可选，默认 "isolated"）
        - leverage: 杠杆倍数（可选）
    """
    logger = get_current_app().logger
    payload = request.get_json()
    
    if not payload:
        return jsonify({"status": "error", "message": "无效请求"}), 400
    
    required_fields = ["symbol", "side", "order_type", "size"]
    missing_fields = [field for field in required_fields if not payload.get(field)]
    if missing_fields:
        return jsonify({
            "status": "error",
            "message": f"缺少必填参数: {', '.join(missing_fields)}"
        }), 400
    
    try:
        symbol = payload.get("symbol", "").upper()
        side = payload.get("side")
        order_type = payload.get("order_type")
        size = str(payload.get("size"))
        price = payload.get("price")
        product_type = payload.get("product_type", "umcbl")
        margin_coin = payload.get("margin_coin", "USDT")
        margin_mode = payload.get("margin_mode", "isolated")
        leverage = payload.get("leverage")
        
        if order_type == "limit" and not price:
            return jsonify({
                "status": "error",
                "message": "限价单必须提供 price 参数"
            }), 400
        
        logger.info(
            f"🧪 测试下单 | symbol: {symbol} | side: {side} | order_type: {order_type} | "
            f"size: {size} | price: {price} | leverage: {leverage}"
        )
        
        client = BitgetClient()
        result = client.place_order(
            symbol=symbol,
            side=side,
            order_type=order_type,
            size=size,
            price=str(price) if price else None,
            product_type=product_type,
            margin_coin=margin_coin,
            margin_mode=margin_mode,
            leverage=str(leverage) if leverage else None,
        )
        
        return jsonify({
            "status": "success",
            "data": result,
            "params": {
                "symbol": symbol,
                "side": side,
                "order_type": order_type,
                "size": size,
                "price": price,
                "leverage": leverage
            }
        })
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 400


@test_bitget_bp.route("/test/cancel_order", methods=["POST"])
def test_cancel_order():
    """
    测试接口：撤单
    
    请求参数:
        - symbol: 合约交易对符号，如 "BTCUSDT"
        - order_id: 订单ID
        - product_type: 产品线类型（可选，默认 "USDT-FUTURES"）
    """
    logger = get_current_app().logger
    payload = request.get_json()
    
    if not payload:
        return jsonify({"status": "error", "message": "无效请求"}), 400
    
    required_fields = ["symbol", "order_id"]
    missing_fields = [field for field in required_fields if not payload.get(field)]
    if missing_fields:
        return jsonify({
            "status": "error",
            "message": f"缺少必填参数: {', '.join(missing_fields)}"
        }), 400
    
    try:
        symbol = payload.get("symbol", "").upper()
        order_id = payload.get("order_id")
        product_type = payload.get("product_type", "USDT-FUTURES")
        
        logger.info(f"🧪 测试撤单 | symbol: {symbol} | order_id: {order_id}")
        
        client = BitgetClient()
        result = client.cancel_order(symbol, order_id, product_type)
        
        return jsonify({
            "status": "success",
            "data": result,
            "symbol": symbol,
            "order_id": order_id
        })
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 400


@test_bitget_bp.route("/test/get_current_orders", methods=["POST"])
def test_get_current_orders():
    """
    测试接口：获取当前委托
    
    请求参数:
        - symbol: 合约交易对符号，如 "BTCUSDT"
        - product_type: 产品线类型（可选，默认 "USDT-FUTURES"）
    """
    logger = get_current_app().logger
    payload = request.get_json()
    
    if not payload or not payload.get("symbol"):
        return jsonify({"status": "error", "message": "symbol 参数必填"}), 400
    
    try:
        symbol = payload.get("symbol", "").upper()
        product_type = payload.get("product_type", "USDT-FUTURES")
        
        logger.info(f"🧪 测试获取当前委托 | symbol: {symbol}")
        
        client = BitgetClient()
        result = client.get_current_orders(symbol, product_type)
        
        return jsonify({
            "status": "success",
            "data": result,
            "symbol": symbol
        })
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 400


@test_bitget_bp.route("/test/get_order_detail", methods=["POST"])
def test_get_order_detail():
    """
    测试接口：获取订单详情
    
    请求参数:
        - symbol: 合约交易对符号，如 "BTCUSDT"
        - order_id: 订单ID
        - product_type: 产品线类型（可选，默认 "USDT-FUTURES"）
    """
    logger = get_current_app().logger
    payload = request.get_json()
    
    if not payload:
        return jsonify({"status": "error", "message": "无效请求"}), 400
    
    required_fields = ["symbol", "order_id"]
    missing_fields = [field for field in required_fields if not payload.get(field)]
    if missing_fields:
        return jsonify({
            "status": "error",
            "message": f"缺少必填参数: {', '.join(missing_fields)}"
        }), 400
    
    try:
        symbol = payload.get("symbol", "").upper()
        order_id = payload.get("order_id")
        product_type = payload.get("product_type", "USDT-FUTURES")
        
        logger.info(f"🧪 测试获取订单详情 | symbol: {symbol} | order_id: {order_id}")
        
        client = BitgetClient()
        result = client.get_order_detail(symbol, order_id, product_type)
        
        return jsonify({
            "status": "success",
            "data": result,
            "symbol": symbol,
            "order_id": order_id
        })
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 400


@test_bitget_bp.route("/test/get_openable_size", methods=["POST"])
def test_get_openable_size():
    """
    测试接口：获取可开数量
    
    请求参数:
        - symbol: 产品ID，必须大写，如 "SBTCSUSDT_SUMCBL"
        - margin_coin: 保证金币种，如 "SUSDT" 或 "USDT"
        - open_price: 开仓价格
        - open_amount: 开仓金额
        - leverage: 杠杆倍数（可选）
    """
    logger = get_current_app().logger
    payload = request.get_json()
    
    if not payload:
        return jsonify({"status": "error", "message": "无效请求"}), 400
    
    required_fields = ["symbol", "margin_coin", "open_price", "open_amount"]
    missing_fields = [field for field in required_fields if not payload.get(field)]
    if missing_fields:
        return jsonify({
            "status": "error",
            "message": f"缺少必填参数: {', '.join(missing_fields)}"
        }), 400
    
    try:
        symbol = payload.get("symbol", "").upper()
        margin_coin = payload.get("margin_coin")
        open_price = str(payload.get("open_price"))
        open_amount = str(payload.get("open_amount"))
        leverage = payload.get("leverage")
        
        logger.info(
            f"🧪 测试获取可开数量 | symbol: {symbol} | margin_coin: {margin_coin} | "
            f"open_price: {open_price} | open_amount: {open_amount} | leverage: {leverage}"
        )
        
        client = BitgetClient()
        result = client.get_openable_size(
            symbol=symbol,
            margin_coin=margin_coin,
            open_price=open_price,
            open_amount=open_amount,
            leverage=str(leverage) if leverage else None
        )
        
        return jsonify({
            "status": "success",
            "data": result,
            "params": {
                "symbol": symbol,
                "margin_coin": margin_coin,
                "open_price": open_price,
                "open_amount": open_amount,
                "leverage": leverage
            }
        })
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 400


@test_bitget_bp.route("/test/set_leverage", methods=["POST"])
def test_set_leverage():
    """
    测试接口：设置杠杆倍数
    
    请求参数:
        - symbol: 合约交易对符号，如 "BTCUSDT"
        - leverage: 杠杆倍数
        - margin_coin: 保证金币种（可选，默认 "USDT"）
    """
    logger = get_current_app().logger
    payload = request.get_json()
    
    if not payload:
        return jsonify({"status": "error", "message": "无效请求"}), 400
    
    required_fields = ["symbol", "leverage"]
    missing_fields = [field for field in required_fields if not payload.get(field)]
    if missing_fields:
        return jsonify({
            "status": "error",
            "message": f"缺少必填参数: {', '.join(missing_fields)}"
        }), 400
    
    try:
        symbol = payload.get("symbol", "").upper()
        leverage = str(payload.get("leverage"))
        margin_coin = payload.get("margin_coin", "USDT")
        
        logger.info(f"🧪 测试设置杠杆 | symbol: {symbol} | leverage: {leverage}x | margin_coin: {margin_coin}")
        
        client = BitgetClient()
        result = client.set_leverage(symbol, leverage, margin_coin)
        
        return jsonify({
            "status": "success",
            "data": result,
            "symbol": symbol,
            "leverage": leverage,
            "margin_coin": margin_coin
        })
    except Exception as e:
        logger.error(f"❌ 测试失败: {e}", exc_info=True)
        return jsonify({"status": "error", "message": str(e)}), 400

