from decimal import Decimal
import time
from config import Config
from longport.openapi import (
    OrderType,
    OrderSide,
    TimeInForceType,
    OutsideRTH,
    OrderStatus,
)
from services.option_service import select_best_options, select_nearest_option_date
from utils.decorator import timed_api_call
from lib.MyFlask import get_current_app


@timed_api_call
def get_current_position_quantity_by_api(symbol: str) -> Decimal:
    """获取当前持仓数量"""
    current_app = get_current_app()
    try:
        resp = current_app.trade_ctx.stock_positions()
        for channel in resp.channels:
            for pos in channel.positions:
                if pos.symbol == symbol:
                    return Decimal(str(pos.quantity))
        return Decimal("0")
    except Exception as e:
        current_app.logger.error(f"获取持仓失败 {symbol}: {e}")
        raise


@timed_api_call
def get_current_position_quantity_by_cache(symbol: str) -> Decimal:
    """获取当前持仓数量"""
    current_app = get_current_app()
    try:
        positions = current_app.positions
        for pos in positions:
            if pos.symbol == symbol:
                return pos.quantity
        return Decimal("0")
    except Exception as e:
        current_app.logger.error(f"获取持仓失败 {symbol}: {e}")
        raise


@timed_api_call
def get_current_position_quantity(symbol: str) -> Decimal:
    """获取当前持仓数量"""
    use_cache = Config.ENABLE_PRICE_CACHE
    if use_cache:
        return get_current_position_quantity_by_cache(symbol)
    return get_current_position_quantity_by_api(symbol)


@timed_api_call
def estimate_max_purchase_quantity_by_api(
    symbol: str,
    side: type[OrderSide],
    price: Decimal,
    is_margin: bool | None,
) -> Decimal:
    """估算最大可买入数量，margin_rate 会在系统内部自动计算"""
    current_app = get_current_app()
    try:
        result = current_app.trade_ctx.estimate_max_purchase_quantity(
            symbol=symbol, order_type=OrderType.LO, side=side, price=price
        )
        if is_margin:
            if side == OrderSide.Buy:
                qty = result.margin_max_qty
            else:
                qty = result.cash_max_qty
        else:
            qty = result.cash_max_qty
        return Decimal(str(int(qty * Decimal(Config.MAX_PURCHASE_RATIO))))
    except Exception as e:
        current_app.logger.error(f"估算最大购买数量失败: {e}")
        raise


@timed_api_call
def estimate_max_purchase_quantity_by_cache(
    symbol: str,
    side: type[OrderSide],
    price: Decimal,
    is_margin: bool | None,
    margin_rate: float | None,
) -> Decimal:
    """估算最大可买入数量"""
    current_app = get_current_app()
    try:
        # 获取现金
        total_cash = current_app.total_cash
        if is_margin:
            qty = Decimal(int(total_cash * Decimal(str(margin_rate)) / price))
        else:
            qty = Decimal(int(total_cash / price))
        return Decimal(str(qty * Decimal(Config.MAX_PURCHASE_RATIO)))
    except Exception as e:
        current_app.logger.error(f"估算最大购买数量失败: {e}")
        raise


@timed_api_call
def estimate_max_purchase_quantity(
    symbol: str,
    side: type[OrderSide],
    price: Decimal,
    is_margin: bool | None,
    margin_rate: float | None,
) -> Decimal:
    """估算最大可买入数量"""
    use_cache = Config.ENABLE_PRICE_CACHE
    if use_cache:
        return estimate_max_purchase_quantity_by_cache(
            symbol, side, price, is_margin, margin_rate
        )
    return estimate_max_purchase_quantity_by_api(symbol, side, price, is_margin)


@timed_api_call
def cancel_all_pending_orders_for_symbol(symbol: str):
    """取消该标的的所有挂单"""
    current_app = get_current_app()
    try:
        orders = current_app.trade_ctx.today_orders(symbol=symbol)
        for order in orders:
            if order.status in [
                OrderStatus.WaitToNew,
                OrderStatus.New,
                OrderStatus.WaitToReplace,
                OrderStatus.PendingReplace,
                OrderStatus.PartialFilled,
                OrderStatus.WaitToCancel,
                OrderStatus.PendingCancel,
            ]:
                get_current_app().logger.info(
                    f"取消挂单 | {order.order_id} | {order.symbol}"
                )
                current_app.trade_ctx.cancel_order(order.order_id)
    except Exception as e:
        get_current_app().logger.error(f"清理挂单失败: {e}")


@timed_api_call
def get_best_ask_price(symbol: str) -> Decimal:
    """获取卖一价（用于买入）"""
    current_app = get_current_app()
    try:
        use_cache = Config.ENABLE_PRICE_CACHE
        if use_cache:
            has_symbol = current_app.depth_cache.get(symbol, None)
            if has_symbol:
                return Decimal(str(current_app.depth_cache[symbol].ask))

        depth = current_app.quote_ctx.depth(symbol)
        ask = depth.asks[0].price if depth.asks else None
        if not ask:
            raise ValueError("卖一价为空")
        return Decimal(str(ask))
    except Exception as e:
        get_current_app().logger.error(f"获取卖一价失败 {symbol}: {e}")
        raise


@timed_api_call
def get_best_bid_price(symbol: str) -> Decimal:
    """获取买一价（用于卖出）"""
    current_app = get_current_app()
    try:
        use_cache = Config.ENABLE_PRICE_CACHE
        if use_cache:
            has_symbol = current_app.depth_cache.get(symbol, None)
            if has_symbol:
                return Decimal(str(current_app.depth_cache[symbol].bid))

        depth = current_app.quote_ctx.depth(symbol)
        bid = depth.bids[0].price if depth.bids else None
        if not bid:
            raise ValueError("买一价为空")
        return Decimal(str(bid))
    except Exception as e:
        current_app.logger.error(f"获取买一价失败 {symbol}: {e}")
        raise


@timed_api_call
def submit_limit_order(
    symbol: str,
    side: type[OrderSide],
    submitted_quantity: Decimal,
    submitted_price: Decimal,
) -> str:
    """提交限价单，返回 order_id"""
    current_app = get_current_app()
    try:
        current_app.logger.info(
            f"提交限价单 | {symbol} {side} {submitted_quantity} @ {submitted_price}"
        )
        resp = current_app.trade_ctx.submit_order(
            symbol=symbol,
            order_type=OrderType.LO,
            side=side,
            submitted_quantity=submitted_quantity,
            submitted_price=submitted_price,
            time_in_force=TimeInForceType.GoodTilCanceled,
            outside_rth=OutsideRTH.AnyTime,
        )
        current_app.logger.info(
            f"订单已提交 | ID={resp.order_id} | {side} {submitted_quantity} @ {submitted_price}"
        )
        return resp.order_id
    except Exception as e:
        current_app.logger.error(f"下单失败 {symbol}: {e}")
        raise


@timed_api_call
def submit_market_order(
    symbol: str,
    side: type[OrderSide],
    submitted_quantity: Decimal,
) -> str:
    """提交市价单，返回 order_id"""
    current_app = get_current_app()
    try:
        resp = current_app.trade_ctx.submit_order(
            symbol=symbol,
            order_type=OrderType.MO,
            side=side,
            submitted_quantity=submitted_quantity,
            time_in_force=TimeInForceType.GoodTilCanceled,
            outside_rth=OutsideRTH.AnyTime,
        )
        current_app.logger.info(
            f"市价单已提交 | ID={resp.order_id} | {side} {submitted_quantity}"
        )
        return resp.order_id
    except Exception as e:
        current_app.logger.error(f"下单失败 {symbol}: {e}")
        raise


@timed_api_call
def submit_stop_order(
    symbol: str,
    side: type[OrderSide],
    submitted_quantity: Decimal,
    trigger_price: Decimal,
) -> str:
    """提交市价止损单"""
    current_app = get_current_app()
    try:
        resp = current_app.trade_ctx.submit_order(
            symbol=symbol,
            order_type=OrderType.MIT,
            side=side,
            submitted_quantity=submitted_quantity,
            trigger_price=trigger_price,
            time_in_force=TimeInForceType.GoodTilCanceled,
            outside_rth=OutsideRTH.AnyTime,
        )
        current_app.logger.info(
            f"止损订单已提交 | ID={resp.order_id} | {side} {submitted_quantity} @ {trigger_price}"
        )
        return resp.order_id
    except Exception as e:
        current_app.logger.error(f"下单失败 {symbol}: {e}")
        raise


def check_order_status(order_id: str) -> type[OrderStatus]:
    """检查订单状态"""
    current_app = get_current_app()
    try:
        detail = current_app.trade_ctx.order_detail(order_id)
        return detail.status
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
    trade_ctx = get_current_app().trade_ctx

    # 等待一段时间观察订单成交情况
    time.sleep(Config.ORDER_CHECK_INTERVAL)

    try:
        status = check_order_status(order_id)

        # 如果订单已全部成交
        if status == OrderStatus.Filled:
            logger.info(f"✅ 订单已全部成交 | {order_id}")
            return True

        # 如果订单部分成交
        elif status == OrderStatus.PartialFilled:
            logger.info(f"🟡 订单部分成交 | {order_id}")
            # 取消未成交部分
            trade_ctx.cancel_order(order_id)
            logger.info(f"已取消未成交部分 | {order_id}")
            return False

        # 如果订单未成交
        else:
            # 取消订单
            trade_ctx.cancel_order(order_id)
            logger.info(f"已取消未成交订单 | {order_id} | 状态: {status}")
            return False

    except Exception as e:
        logger.error(f"等待并检查订单状态失败 {order_id}: {e}")
        return False


def do_stock_long(
    symbol: str,
    price: float | None = None,
    is_margin: bool | None = False,
    margin_rate: float | None = None,
    is_validate_order_price_or_qty: bool = True,
):
    """执行做多操作"""
    logger = get_current_app().logger
    logger.info(f"开始做多 | {symbol}")

    if price:
        price_decimal = Decimal(str(price))
        logger.info(f"使用指定价格 | {price_decimal}")
    else:
        price_decimal = get_best_ask_price(symbol)
        logger.info(f"使用市场价格 | {price_decimal}")

    quantity = estimate_max_purchase_quantity(
        symbol, OrderSide.Buy, price_decimal, is_margin, margin_rate
    )

    if is_validate_order_price_or_qty:
        validate_order_price_or_qty(price_decimal, quantity)

    # 提交订单
    order_id = submit_limit_order(symbol, OrderSide.Buy, quantity, price_decimal)
    logger.info(f"限价单已提交 | 订单ID: {order_id}")

    # 等待并检查订单状态
    wait_and_check_order(order_id, symbol)


def do_stock_short(
    symbol: str,
    price: float | None = None,
    is_margin: bool | None = False,
    margin_rate: float | None = None,
    is_validate_order_price_or_qty: bool = True,
):
    """执行做空操作"""
    logger = get_current_app().logger
    logger.info(f"开始做空 | {symbol}")

    if price:
        price_decimal = Decimal(str(price))
        logger.info(f"使用指定价格 | {price_decimal}")
    else:
        price_decimal = get_best_bid_price(symbol)
        logger.info(f"使用市场价格 | {price_decimal}")

    quantity = estimate_max_purchase_quantity(
        symbol, OrderSide.Sell, price_decimal, is_margin, margin_rate
    )

    if is_validate_order_price_or_qty:
        validate_order_price_or_qty(price_decimal, quantity)

    # 提交订单
    order_id = submit_limit_order(symbol, OrderSide.Sell, quantity, price_decimal)
    logger.info(f"限价单已提交 | 订单ID: {order_id}")

    # 等待并检查订单状态
    wait_and_check_order(order_id, symbol)


def do_stock_close(symbol: str, side: str, quantity: int, price: float | None = None):
    logger = get_current_app().logger
    logger.info(f"开始平仓 | {symbol} | {side.upper()} {quantity} 股")

    order_side = OrderSide.Buy if side == "buy" else OrderSide.Sell

    # 如果指定了价格，使用指定价格
    if price:
        target_price = Decimal(str(price))
        logger.info(f"使用指定价格 | {target_price}")
    else:
        # 获取目标价格
        target_price = (
            get_best_bid_price(symbol)
            if order_side == OrderSide.Sell
            else get_best_ask_price(symbol)
        )
        logger.info(f"使用市场价格 | {target_price}")

    # 提交限价单
    order_id = submit_limit_order(
        symbol, order_side, Decimal(str(quantity)), target_price
    )
    logger.info(f"限价平仓单已提交 | 订单ID: {order_id}")

    # 等待并检查订单状态
    if not wait_and_check_order(order_id, symbol):
        # 如果限价单未成交，改用市价单
        logger.info(f"限价单未完全成交，改用市价单平仓 | {symbol}")
        target_price = (
            get_best_bid_price(symbol)
            if order_side == OrderSide.Sell
            else get_best_ask_price(symbol)
        )
        market_order_id = submit_limit_order(
            symbol, order_side, Decimal(str(quantity)), target_price
        )
        logger.info(f"市价平仓单已提交 | 订单ID: {market_order_id}")


def handle_stock_signal(
    symbol: str,
    action: str,
    sentiment: str,
    price: float | None = None,
    is_margin: bool | None = False,
    margin_rate: float | None = None,
):
    """主入口：处理股票信号"""
    logger = get_current_app().logger
    full_symbol = f"{symbol}.US"
    logger.info(f"处理股票信号 | {full_symbol} | {action} {sentiment}")

    current_position = get_current_position_quantity(full_symbol)

    if action == "buy" and sentiment == "long":
        do_stock_long(full_symbol, price, is_margin, margin_rate)
    elif action == "sell" and sentiment == "short":
        do_stock_short(full_symbol, price, is_margin, margin_rate)
    elif sentiment == "flat":
        if current_position != 0:
            logger.info("收到平仓信号，准备平仓")
            close_side = "sell" if current_position > 0 else "buy"
            abs_qty = int(abs(current_position))
            do_stock_close(full_symbol, close_side, abs_qty, price)
        else:
            logger.info("已是空仓，无需平仓")


def handle_option_signal(symbol: str, action: str, sentiment: str):
    """处理期权信号"""
    app = get_current_app()
    logger = app.logger

    full_symbol = f"{symbol}.US"
    logger.info(f"处理股票信号 | {full_symbol} | {action} {sentiment}")

    selected_options = {}
    if (
        action == "buy"
        and sentiment == "long"
        or action == "sell"
        and sentiment == "short"
    ):
        date_list = app.quote_ctx.option_chain_expiry_date_list(full_symbol)
        selected_date = select_nearest_option_date(date_list, symbol)

        logger.info(f"选择的期权合约日期: {selected_date}")
        if selected_date is None:
            logger.info("没有找到合适的期权合约")
            return

        option_list = app.quote_ctx.option_chain_info_by_date(
            full_symbol, selected_date
        )
        # 选择合适的期权
        selected_options = select_best_options(app, full_symbol, option_list)

        if selected_options is None:
            logger.info("没有找到合适的期权合约")
            return

    if action == "buy" and sentiment == "long":
        do_stock_long(selected_options.get("call", {}).get("symbol"), is_validate_order_price_or_qty=False)
    elif action == "sell" and sentiment == "short":
        do_stock_long(selected_options.get("put", {}).get("symbol"), is_validate_order_price_or_qty=False)
    elif sentiment == "flat":
        resp = app.trade_ctx.stock_positions()
        for channel in resp.channels:
            for pos in channel.positions:
                if symbol in pos.symbol:
                    do_stock_close(pos.symbol, "sell", quantity=int(pos.quantity))


def handle_etf_signal(symbol: str, action: str, sentiment: str):
    pass
