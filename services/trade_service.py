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


@timed_api_call
def get_current_position_quantity(symbol: str) -> Decimal:
    """获取当前持仓数量，正数表示多仓，负数表示空仓"""
    current_app = get_current_app()
    client = current_app.bitget_client
    
    try:
        positions = client.get_all_positions()
        if isinstance(positions, list):
            for pos in positions:
                if pos.get("symbol") == symbol:
                    # 持仓方向: long 或 short
                    hold_side = pos.get("holdSide", "")
                    available = Decimal(str(pos.get("available", "0")))
                    if hold_side == "long":
                        return available
                    elif hold_side == "short":
                        return available * Decimal("-1")
        return Decimal("0")
    except Exception as e:
        current_app.logger.error(f"获取持仓失败 {symbol}: {e}")
        raise


@timed_api_call
def estimate_max_purchase_quantity(
    symbol: str,
    side: str,  # "buy" or "sell"
    price: Decimal,
) -> Decimal:
    """估算最大可买入数量"""
    current_app = get_current_app()
    client = current_app.bitget_client
    
    try:
        # 获取账户信息
        account_info = client.get_account_info()
        if isinstance(account_info, list) and len(account_info) > 0:
            available = Decimal(str(account_info[0].get("available", "0")))
        elif isinstance(account_info, dict):
            available = Decimal(str(account_info.get("available", "0")))
        else:
            available = Decimal("0")
        
        # 计算可开数量
        max_qty = available * Decimal(Config.MAX_PURCHASE_RATIO) / price
        return Decimal(str(int(max_qty)))
    except Exception as e:
        current_app.logger.error(f"估算最大购买数量失败: {e}")
        raise


@timed_api_call
def cancel_all_pending_orders_for_symbol(symbol: str):
    """取消该标的的所有挂单"""
    current_app = get_current_app()
    client = current_app.bitget_client
    
    try:
        orders = client.get_current_orders(symbol)
        if isinstance(orders, list):
            for order in orders:
                order_id = order.get("orderId")
                status = order.get("status", "")
                if status in [ORDER_STATUS_NEW, ORDER_STATUS_PENDING, ORDER_STATUS_PARTIAL_FILLED]:
                    current_app.logger.info(f"取消挂单 | {order_id} | {symbol}")
                    client.cancel_order(symbol, order_id)
    except Exception as e:
        current_app.logger.error(f"清理挂单失败: {e}")


@timed_api_call
def get_best_ask_price(symbol: str) -> Decimal:
    """获取卖一价（用于买入）"""
    current_app = get_current_app()
    client = current_app.bitget_client
    
    try:
        depth = client.get_depth(symbol, limit=5)
        asks = depth.get("asks", [])
        if asks and len(asks) > 0:
            ask_price = asks[0][0]  # [price, quantity]
            return Decimal(str(ask_price))
        raise ValueError("卖一价为空")
    except Exception as e:
        current_app.logger.error(f"获取卖一价失败 {symbol}: {e}")
        raise


@timed_api_call
def get_best_bid_price(symbol: str) -> Decimal:
    """获取买一价（用于卖出）"""
    current_app = get_current_app()
    client = current_app.bitget_client
    
    try:
        depth = client.get_depth(symbol, limit=5)
        bids = depth.get("bids", [])
        if bids and len(bids) > 0:
            bid_price = bids[0][0]  # [price, quantity]
            return Decimal(str(bid_price))
        raise ValueError("买一价为空")
    except Exception as e:
        current_app.logger.error(f"获取买一价失败 {symbol}: {e}")
        raise


@timed_api_call
def submit_limit_order(
    symbol: str,
    side: str,  # "open_long", "open_short", "close_long", "close_short"
    submitted_quantity: Decimal,
    submitted_price: Decimal,
) -> str:
    """提交限价单，返回 order_id"""
    current_app = get_current_app()
    client = current_app.bitget_client
    
    try:
        current_app.logger.info(
            f"提交限价单 | {symbol} {side} {submitted_quantity} @ {submitted_price}"
        )
        result = client.place_order(
            symbol=symbol,
            side=side,
            order_type="limit",
            size=str(int(submitted_quantity)),
            price=str(submitted_price),
        )
        order_id = result.get("orderId", "")
        current_app.logger.info(
            f"订单已提交 | ID={order_id} | {side} {submitted_quantity} @ {submitted_price}"
        )
        return order_id
    except Exception as e:
        current_app.logger.error(f"下单失败 {symbol}: {e}")
        raise


@timed_api_call
def submit_market_order(
    symbol: str,
    side: str,  # "open_long", "open_short", "close_long", "close_short"
    submitted_quantity: Decimal,
) -> str:
    """提交市价单，返回 order_id"""
    current_app = get_current_app()
    client = current_app.bitget_client
    
    try:
        result = client.place_order(
            symbol=symbol,
            side=side,
            order_type="market",
            size=str(int(submitted_quantity)),
        )
        order_id = result.get("orderId", "")
        current_app.logger.info(
            f"市价单已提交 | ID={order_id} | {side} {submitted_quantity}"
        )
        return order_id
    except Exception as e:
        current_app.logger.error(f"下单失败 {symbol}: {e}")
        raise


def check_order_status(order_id: str, symbol: str) -> str:
    """检查订单状态"""
    current_app = get_current_app()
    client = current_app.bitget_client
    
    try:
        detail = client.get_order_detail(symbol, order_id)
        return detail.get("status", "")
    except Exception as e:
        current_app.logger.error(f"检查订单状态失败 {order_id}: {e}")
        raise


def validate_order_price_or_qty(price: Decimal, quantity: Decimal):
    """验证订单价格或数量"""
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
    """等待并检查订单状态，如果未成交则撤单"""
    logger = get_current_app().logger
    client = get_current_app().bitget_client

    # 等待一段时间观察订单成交情况
    time.sleep(Config.ORDER_CHECK_INTERVAL)

    try:
        status = check_order_status(order_id, symbol)

        # 如果订单已全部成交
        if status == ORDER_STATUS_FILLED:
            logger.info(f"✅ 订单已全部成交 | {order_id}")
            return True

        # 如果订单部分成交
        elif status == ORDER_STATUS_PARTIAL_FILLED:
            logger.info(f"🟡 订单部分成交 | {order_id}")
            # 取消未成交部分
            client.cancel_order(symbol, order_id)
            logger.info(f"已取消未成交部分 | {order_id}")
            return False

        # 如果订单未成交
        else:
            # 取消订单
            client.cancel_order(symbol, order_id)
            logger.info(f"已取消未成交订单 | {order_id} | 状态: {status}")
            return False

    except Exception as e:
        logger.error(f"等待并检查订单状态失败 {order_id}: {e}")
        return False


def do_contract_long(
    symbol: str,
    price: float | None = None,
    is_validate_order_price_or_qty: bool = True,
):
    """执行做多操作（开多仓）"""
    logger = get_current_app().logger
    logger.info(f"开始做多 | {symbol}")

    if price:
        price_decimal = Decimal(str(price))
        logger.info(f"使用指定价格 | {price_decimal}")
    else:
        price_decimal = get_best_ask_price(symbol)
        logger.info(f"使用市场价格 | {price_decimal}")

    quantity = estimate_max_purchase_quantity(symbol, "buy", price_decimal)

    if is_validate_order_price_or_qty:
        validate_order_price_or_qty(price_decimal, quantity)

    # 提交订单（开多仓）
    order_id = submit_limit_order(symbol, "open_long", quantity, price_decimal)
    logger.info(f"限价单已提交 | 订单ID: {order_id}")

    # 等待并检查订单状态
    wait_and_check_order(order_id, symbol)


def do_contract_short(
    symbol: str,
    price: float | None = None,
    is_validate_order_price_or_qty: bool = True,
):
    """执行做空操作（开空仓）"""
    logger = get_current_app().logger
    logger.info(f"开始做空 | {symbol}")

    if price:
        price_decimal = Decimal(str(price))
        logger.info(f"使用指定价格 | {price_decimal}")
    else:
        price_decimal = get_best_bid_price(symbol)
        logger.info(f"使用市场价格 | {price_decimal}")

    quantity = estimate_max_purchase_quantity(symbol, "sell", price_decimal)

    if is_validate_order_price_or_qty:
        validate_order_price_or_qty(price_decimal, quantity)

    # 提交订单（开空仓）
    order_id = submit_limit_order(symbol, "open_short", quantity, price_decimal)
    logger.info(f"限价单已提交 | 订单ID: {order_id}")

    # 等待并检查订单状态
    wait_and_check_order(order_id, symbol)


def do_contract_close(symbol: str, side: str, quantity: Decimal, price: float | None = None):
    """平仓操作"""
    logger = get_current_app().logger
    logger.info(f"开始平仓 | {symbol} | {side.upper()} {quantity}")

    # 确定平仓方向
    # side: "long" 表示平多仓 -> close_long, "short" 表示平空仓 -> close_short
    if side.lower() == "long":
        close_side = "close_long"
    elif side.lower() == "short":
        close_side = "close_short"
    else:
        raise ValueError(f"无效的平仓方向: {side}")

    # 如果指定了价格，使用指定价格
    if price:
        target_price = Decimal(str(price))
        logger.info(f"使用指定价格 | {target_price}")
    else:
        # 获取目标价格
        if close_side == "close_long":
            # 平多仓，用买一价
            target_price = get_best_bid_price(symbol)
        else:
            # 平空仓，用卖一价
            target_price = get_best_ask_price(symbol)
        logger.info(f"使用市场价格 | {target_price}")

    # 提交限价单
    order_id = submit_limit_order(symbol, close_side, quantity, target_price)
    logger.info(f"限价平仓单已提交 | 订单ID: {order_id}")

    # 等待并检查订单状态
    if not wait_and_check_order(order_id, symbol):
        # 如果限价单未成交，改用市价单
        logger.info(f"限价单未完全成交，改用市价单平仓 | {symbol}")
        market_order_id = submit_market_order(symbol, close_side, quantity)
        logger.info(f"市价平仓单已提交 | 订单ID: {market_order_id}")


def handle_contract_signal(
    symbol: str,
    action: str,
    sentiment: str,
    price: float | None = None,
):
    """主入口：处理合约信号"""
    logger = get_current_app().logger
    logger.info(f"处理合约信号 | {symbol} | {action} {sentiment}")

    if action == "buy" and sentiment == "long":
        # 做多：开多仓
        do_contract_long(symbol, price)
    elif action == "sell" and sentiment == "short":
        # 做空：开空仓
        do_contract_short(symbol, price)
    elif sentiment == "flat":
        # 获取当前持仓
        current_position = get_current_position_quantity(symbol)
        # 平仓
        if current_position > 0:
            logger.info("收到平仓信号，准备平多仓")
            do_contract_close(symbol, "long", abs(current_position), price)
        elif current_position < 0:
            logger.info("收到平仓信号，准备平空仓")
            do_contract_close(symbol, "short", abs(current_position), price)
        else:
            logger.info("已是空仓，无需平仓")
