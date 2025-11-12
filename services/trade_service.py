from decimal import Decimal
import time
from config import Config
from utils.decorator import timed_api_call
from utils.bitget_client import BitgetClient
from lib.MyFlask import get_current_app


# Bitget 订单状态映射
ORDER_STATUS_FILLED = "filled"
ORDER_STATUS_PARTIAL_FILLED = "partially_filled"
ORDER_STATUS_NEW = "new"
ORDER_STATUS_PENDING = "pending"

# 逐仓模式固定为 isolated
MARGIN_MODE_ISOLATED = "isolated"


@timed_api_call
def get_current_position_quantity(symbol: str) -> Decimal:
    """
    获取当前持仓数量，正数表示多仓，负数表示空仓
    
    Args:
        symbol: 合约交易对符号，如 "BTCUSDT"
    
    Returns:
        Decimal: 持仓数量，正数表示多仓，负数表示空仓，0 表示无持仓
    """
    current_app = get_current_app()
    client = current_app.bitget_client
    logger = current_app.logger
    
    try:
        logger.info(f"📊 查询持仓 | {symbol}")
        positions = client.get_all_positions()
        
        if isinstance(positions, list):
            for pos in positions:
                if pos.get("symbol") == symbol:
                    # 持仓方向: long 或 short
                    hold_side = pos.get("holdSide", "")
                    available = Decimal(str(pos.get("available", "0")))
                    
                    if hold_side == "long":
                        logger.info(f"✅ 当前多仓数量: {available} | {symbol}")
                        return available
                    elif hold_side == "short":
                        logger.info(f"✅ 当前空仓数量: {available} | {symbol}")
                        return available * Decimal("-1")
        
        logger.info(f"ℹ️ 当前无持仓 | {symbol}")
        return Decimal("0")
    except Exception as e:
        logger.error(f"❌ 获取持仓失败 {symbol}: {e}")
        raise


@timed_api_call
def estimate_max_purchase_quantity(
    symbol: str,
    leverage: str = "2",
    position_ratio: float = 0.1,
) -> Decimal:
    """
    通过 Bitget API 获取可开数量，并根据逐仓比例计算实际下单数量
    
    Args:
        symbol: 合约交易对符号
        leverage: 杠杆倍数，默认 2 倍
        position_ratio: 逐仓比例，默认 0.1 (10%)
    
    Returns:
        Decimal: 可下单数量
    """
    current_app = get_current_app()
    client = current_app.bitget_client
    logger = current_app.logger
    
    try:
        logger.info(f"📊 计算可开数量 | {symbol} | 杠杆: {leverage}x | 逐仓比例: {position_ratio*100}%")
        
        # 调用 Bitget API 获取可开数量
        result = client.get_openable_size(
            symbol=symbol,
            margin_mode=MARGIN_MODE_ISOLATED,
            leverage=leverage
        )
        
        # 解析 API 返回的可开数量
        # API 返回格式: {"openCount": "1000", "openCountInUsdt": "50000"}
        if isinstance(result, dict):
            max_open_count = Decimal(str(result.get("openCount", "0")))
        elif isinstance(result, list) and len(result) > 0:
            max_open_count = Decimal(str(result[0].get("openCount", "0")))
        else:
            max_open_count = Decimal("0")
        
        logger.info(f"📊 API 返回最大可开数量: {max_open_count} | {symbol}")
        
        # 根据逐仓比例计算实际下单数量
        actual_quantity = max_open_count * Decimal(str(position_ratio))
        actual_quantity = Decimal(str(int(actual_quantity)))  # 向下取整
        
        logger.info(f"✅ 计算后实际下单数量: {actual_quantity} | {symbol} | 比例: {position_ratio*100}%")
        
        return actual_quantity
    except Exception as e:
        logger.error(f"❌ 估算最大购买数量失败 {symbol}: {e}")
        raise


@timed_api_call
def set_leverage(symbol: str, leverage: str):
    """
    设置合约杠杆倍数
    
    Args:
        symbol: 合约交易对符号
        leverage: 杠杆倍数，如 "2", "5", "10"
    """
    current_app = get_current_app()
    client = current_app.bitget_client
    logger = current_app.logger
    
    try:
        logger.info(f"⚙️ 设置杠杆倍数 | {symbol} | {leverage}x")
        client.set_leverage(
            symbol=symbol,
            leverage=leverage,
            margin_mode=MARGIN_MODE_ISOLATED
        )
        logger.info(f"✅ 杠杆设置成功 | {symbol} | {leverage}x")
    except Exception as e:
        logger.error(f"❌ 设置杠杆失败 {symbol}: {e}")
        raise


@timed_api_call
def cancel_all_pending_orders_for_symbol(symbol: str):
    """
    取消该标的的所有挂单
    
    Args:
        symbol: 合约交易对符号
    """
    current_app = get_current_app()
    client = current_app.bitget_client
    logger = current_app.logger
    
    try:
        logger.info(f"🔄 查询待取消订单 | {symbol}")
        orders = client.get_current_orders(symbol)
        
        if isinstance(orders, list):
            cancel_count = 0
            for order in orders:
                order_id = order.get("orderId")
                status = order.get("status", "")
                
                if status in [ORDER_STATUS_NEW, ORDER_STATUS_PENDING, ORDER_STATUS_PARTIAL_FILLED]:
                    logger.info(f"🔄 取消挂单 | 订单ID: {order_id} | {symbol} | 状态: {status}")
                    client.cancel_order(symbol, order_id)
                    cancel_count += 1
            
            if cancel_count > 0:
                logger.info(f"✅ 已取消 {cancel_count} 个挂单 | {symbol}")
            else:
                logger.info(f"ℹ️ 无待取消订单 | {symbol}")
        else:
            logger.info(f"ℹ️ 无待取消订单 | {symbol}")
    except Exception as e:
        logger.error(f"❌ 清理挂单失败 {symbol}: {e}")


@timed_api_call
def get_best_ask_price(symbol: str) -> Decimal:
    """
    获取卖一价（BBO 对手价，用于买入/开多仓）
    
    Args:
        symbol: 合约交易对符号
    
    Returns:
        Decimal: 卖一价
    """
    current_app = get_current_app()
    client = current_app.bitget_client
    logger = current_app.logger
    
    try:
        logger.debug(f"📊 查询卖一价 | {symbol}")
        depth = client.get_depth(symbol, limit=1)  # 只需要第一档
        
        asks = depth.get("asks", [])
        if asks and len(asks) > 0:
            ask_price = Decimal(str(asks[0][0]))  # [price, quantity]
            logger.info(f"✅ 卖一价: {ask_price} | {symbol}")
            return ask_price
        raise ValueError("卖一价为空")
    except Exception as e:
        logger.error(f"❌ 获取卖一价失败 {symbol}: {e}")
        raise


@timed_api_call
def get_best_bid_price(symbol: str) -> Decimal:
    """
    获取买一价（BBO 对手价，用于卖出/开空仓/平多仓）
    
    Args:
        symbol: 合约交易对符号
    
    Returns:
        Decimal: 买一价
    """
    current_app = get_current_app()
    client = current_app.bitget_client
    logger = current_app.logger
    
    try:
        logger.debug(f"📊 查询买一价 | {symbol}")
        depth = client.get_depth(symbol, limit=1)  # 只需要第一档
        
        bids = depth.get("bids", [])
        if bids and len(bids) > 0:
            bid_price = Decimal(str(bids[0][0]))  # [price, quantity]
            logger.info(f"✅ 买一价: {bid_price} | {symbol}")
            return bid_price
        raise ValueError("买一价为空")
    except Exception as e:
        logger.error(f"❌ 获取买一价失败 {symbol}: {e}")
        raise


@timed_api_call
def submit_limit_order(
    symbol: str,
    side: str,  # "open_long", "open_short", "close_long", "close_short"
    submitted_quantity: Decimal,
    submitted_price: Decimal,
    leverage: str = "2",
) -> str:
    """
    提交限价单，使用 BBO 对手价
    
    Args:
        symbol: 合约交易对符号
        side: 交易方向 "open_long", "open_short", "close_long", "close_short"
        submitted_quantity: 下单数量
        submitted_price: 下单价格（BBO 对手价）
        leverage: 杠杆倍数
    
    Returns:
        str: 订单ID
    """
    current_app = get_current_app()
    client = current_app.bitget_client
    logger = current_app.logger
    
    try:
        logger.info(
            f"📝 提交限价单 | {symbol} | 方向: {side} | 数量: {submitted_quantity} | "
            f"价格: {submitted_price} | 杠杆: {leverage}x"
        )
        
        result = client.place_order(
            symbol=symbol,
            side=side,
            order_type="limit",
            size=str(int(submitted_quantity)),
            price=str(submitted_price),
            margin_mode=MARGIN_MODE_ISOLATED,
            leverage=leverage,
        )
        
        order_id = result.get("orderId", "")
        logger.info(
            f"✅ 订单已提交 | 订单ID: {order_id} | {symbol} | {side} | "
            f"数量: {submitted_quantity} @ {submitted_price}"
        )
        return order_id
    except Exception as e:
        logger.error(f"❌ 下单失败 {symbol}: {e}")
        raise


@timed_api_call
def submit_market_order(
    symbol: str,
    side: str,  # "open_long", "open_short", "close_long", "close_short"
    submitted_quantity: Decimal,
    leverage: str = "2",
) -> str:
    """
    提交市价单
    
    Args:
        symbol: 合约交易对符号
        side: 交易方向
        submitted_quantity: 下单数量
        leverage: 杠杆倍数
    
    Returns:
        str: 订单ID
    """
    current_app = get_current_app()
    client = current_app.bitget_client
    logger = current_app.logger
    
    try:
        logger.info(
            f"📝 提交市价单 | {symbol} | 方向: {side} | 数量: {submitted_quantity} | "
            f"杠杆: {leverage}x"
        )
        
        result = client.place_order(
            symbol=symbol,
            side=side,
            order_type="market",
            size=str(int(submitted_quantity)),
            margin_mode=MARGIN_MODE_ISOLATED,
            leverage=leverage,
        )
        
        order_id = result.get("orderId", "")
        logger.info(
            f"✅ 市价单已提交 | 订单ID: {order_id} | {symbol} | {side} | "
            f"数量: {submitted_quantity}"
        )
        return order_id
    except Exception as e:
        logger.error(f"❌ 下单失败 {symbol}: {e}")
        raise


def check_order_status(order_id: str, symbol: str) -> str:
    """
    检查订单状态
    
    Args:
        order_id: 订单ID
        symbol: 合约交易对符号
    
    Returns:
        str: 订单状态
    """
    current_app = get_current_app()
    client = current_app.bitget_client
    logger = current_app.logger
    
    try:
        detail = client.get_order_detail(symbol, order_id)
        status = detail.get("status", "")
        logger.debug(f"📊 订单状态查询 | 订单ID: {order_id} | 状态: {status}")
        return status
    except Exception as e:
        logger.error(f"❌ 检查订单状态失败 {order_id}: {e}")
        raise


def validate_order_price_or_qty(price: Decimal, quantity: Decimal):
    """
    验证订单价格或数量
    
    Args:
        price: 订单价格
        quantity: 订单数量
    """
    # 检查最小下单数量
    if quantity < 1:
        raise ValueError(f"可卖数量不足 | 数量: {quantity}")

    # 检查最小开仓金额
    estimated_value = quantity * price
    if estimated_value < Decimal(str(Config.MIN_PRICE_FILTER)):
        raise ValueError(
            f"预估开仓金额 {estimated_value} < {Config.MIN_PRICE_FILTER}，低于阈值，拒绝下单"
        )


def wait_and_check_order(order_id: str, symbol: str) -> bool:
    """
    等待并检查订单状态，如果未成交则撤单
    
    Args:
        order_id: 订单ID
        symbol: 合约交易对符号
    
    Returns:
        bool: True 表示订单已全部成交，False 表示订单未完全成交或已取消
    """
    logger = get_current_app().logger
    client = get_current_app().bitget_client

    logger.info(f"⏳ 等待订单成交 | 订单ID: {order_id} | 等待时间: {Config.ORDER_CHECK_INTERVAL}秒")
    time.sleep(Config.ORDER_CHECK_INTERVAL)

    try:
        status = check_order_status(order_id, symbol)

        # 如果订单已全部成交
        if status == ORDER_STATUS_FILLED:
            logger.info(f"✅ 订单已全部成交 | 订单ID: {order_id} | {symbol}")
            return True

        # 如果订单部分成交
        elif status == ORDER_STATUS_PARTIAL_FILLED:
            logger.info(f"🟡 订单部分成交 | 订单ID: {order_id} | {symbol}")
            # 取消未成交部分
            client.cancel_order(symbol, order_id)
            logger.info(f"🔄 已取消未成交部分 | 订单ID: {order_id} | {symbol}")
            return False

        # 如果订单未成交
        else:
            # 取消订单
            client.cancel_order(symbol, order_id)
            logger.info(f"🔄 已取消未成交订单 | 订单ID: {order_id} | 状态: {status} | {symbol}")
            return False

    except Exception as e:
        logger.error(f"❌ 等待并检查订单状态失败 {order_id}: {e}")
        return False


def do_contract_long(
    symbol: str,
    leverage: str = "2",
    position_ratio: float = 0.1,
):
    """
    执行做多操作（开多仓），使用 BBO 卖一价
    
    Args:
        symbol: 合约交易对符号
        leverage: 杠杆倍数，默认 2 倍
        position_ratio: 逐仓比例，默认 0.1 (10%)
    """
    logger = get_current_app().logger
    logger.info(f"🚀 开始做多（开多仓） | {symbol} | 杠杆: {leverage}x | 逐仓比例: {position_ratio*100}%")

    # 使用 BBO 卖一价（对手价）
    ask_price = get_best_ask_price(symbol)
    logger.info(f"💰 使用 BBO 卖一价: {ask_price} | {symbol}")

    # 通过 API 获取可开数量，并根据逐仓比例计算
    quantity = estimate_max_purchase_quantity(symbol, leverage, position_ratio)
    
    # 验证订单
    validate_order_price_or_qty(ask_price, quantity)

    # 设置杠杆（如果需要）
    try:
        set_leverage(symbol, leverage)
    except Exception as e:
        logger.warning(f"⚠️ 设置杠杆失败，可能已设置: {e}")

    # 提交订单（开多仓）
    order_id = submit_limit_order(symbol, "open_long", quantity, ask_price, leverage)
    logger.info(f"✅ 限价单已提交 | 订单ID: {order_id} | {symbol}")

    # 等待并检查订单状态
    wait_and_check_order(order_id, symbol)


def do_contract_short(
    symbol: str,
    leverage: str = "2",
    position_ratio: float = 0.1,
):
    """
    执行做空操作（开空仓），使用 BBO 买一价
    
    Args:
        symbol: 合约交易对符号
        leverage: 杠杆倍数，默认 2 倍
        position_ratio: 逐仓比例，默认 0.1 (10%)
    """
    logger = get_current_app().logger
    logger.info(f"🚀 开始做空（开空仓） | {symbol} | 杠杆: {leverage}x | 逐仓比例: {position_ratio*100}%")

    # 使用 BBO 买一价（对手价）
    bid_price = get_best_bid_price(symbol)
    logger.info(f"💰 使用 BBO 买一价: {bid_price} | {symbol}")

    # 通过 API 获取可开数量，并根据逐仓比例计算
    quantity = estimate_max_purchase_quantity(symbol, leverage, position_ratio)
    
    # 验证订单
    validate_order_price_or_qty(bid_price, quantity)

    # 设置杠杆（如果需要）
    try:
        set_leverage(symbol, leverage)
    except Exception as e:
        logger.warning(f"⚠️ 设置杠杆失败，可能已设置: {e}")

    # 提交订单（开空仓）
    order_id = submit_limit_order(symbol, "open_short", quantity, bid_price, leverage)
    logger.info(f"✅ 限价单已提交 | 订单ID: {order_id} | {symbol}")

    # 等待并检查订单状态
    wait_and_check_order(order_id, symbol)


def do_contract_close(symbol: str, side: str, quantity: Decimal, leverage: str = "2"):
    """
    平仓操作，使用 BBO 对手价
    
    Args:
        symbol: 合约交易对符号
        side: 平仓方向 "long" 表示平多仓, "short" 表示平空仓
        quantity: 平仓数量
        leverage: 杠杆倍数
    """
    logger = get_current_app().logger
    logger.info(f"🔄 开始平仓 | {symbol} | 方向: {side.upper()} | 数量: {quantity} | 杠杆: {leverage}x")

    # 确定平仓方向
    # side: "long" 表示平多仓 -> close_long, "short" 表示平空仓 -> close_short
    if side.lower() == "long":
        close_side = "close_long"
        # 平多仓，使用 BBO 买一价（对手价）
        target_price = get_best_bid_price(symbol)
        logger.info(f"💰 平多仓使用 BBO 买一价: {target_price} | {symbol}")
    elif side.lower() == "short":
        close_side = "close_short"
        # 平空仓，使用 BBO 卖一价（对手价）
        target_price = get_best_ask_price(symbol)
        logger.info(f"💰 平空仓使用 BBO 卖一价: {target_price} | {symbol}")
    else:
        raise ValueError(f"无效的平仓方向: {side}")

    # 提交限价单
    order_id = submit_limit_order(symbol, close_side, quantity, target_price, leverage)
    logger.info(f"✅ 限价平仓单已提交 | 订单ID: {order_id} | {symbol}")

    # 等待并检查订单状态
    if not wait_and_check_order(order_id, symbol):
        # 如果限价单未成交，改用市价单
        logger.warning(f"⚠️ 限价单未完全成交，改用市价单平仓 | {symbol}")
        market_order_id = submit_market_order(symbol, close_side, quantity, leverage)
        logger.info(f"✅ 市价平仓单已提交 | 订单ID: {market_order_id} | {symbol}")


def handle_contract_signal(
    symbol: str,
    action: str,
    sentiment: str,
    leverage: str = "2",
    position_ratio: float = 0.1,
):
    """
    主入口：处理合约信号
    
    Args:
        symbol: 合约交易对符号，如 "BTCUSDT"
        action: 交易动作 "buy" 或 "sell"
        sentiment: 市场观点 "long", "short", "flat"
        leverage: 杠杆倍数，默认 2 倍
        position_ratio: 逐仓比例，默认 0.1 (10%)
    """
    logger = get_current_app().logger
    logger.info(
        f"📨 收到合约交易信号 | {symbol} | 动作: {action} | 观点: {sentiment} | "
        f"杠杆: {leverage}x | 逐仓比例: {position_ratio*100}%"
    )

    if action == "buy" and sentiment == "long":
        # 做多：开多仓
        logger.info(f"📈 执行做多操作 | {symbol}")
        do_contract_long(symbol, leverage, position_ratio)
    elif action == "sell" and sentiment == "short":
        # 做空：开空仓
        logger.info(f"📉 执行做空操作 | {symbol}")
        do_contract_short(symbol, leverage, position_ratio)
    elif sentiment == "flat":
        # 平仓
        logger.info(f"🔄 执行平仓操作 | {symbol}")
        # 获取当前持仓
        current_position = get_current_position_quantity(symbol)
        
        if current_position > 0:
            logger.info(f"📊 当前持仓: 多仓 {current_position} | {symbol}")
            do_contract_close(symbol, "long", abs(current_position), leverage)
        elif current_position < 0:
            logger.info(f"📊 当前持仓: 空仓 {abs(current_position)} | {symbol}")
            do_contract_close(symbol, "short", abs(current_position), leverage)
        else:
            logger.info(f"ℹ️ 当前无持仓，无需平仓 | {symbol}")
    else:
        logger.warning(f"⚠️ 无效的信号组合 | action: {action} | sentiment: {sentiment}")
