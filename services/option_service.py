from lib.MyFlask import MyFlask
from datetime import datetime, timedelta
from longport.openapi import StrikePriceInfo, OptionQuote

from utils.decorator import timed_api_call

@timed_api_call
def select_nearest_option_date(date_list, symbol: str | None = None):
    """
    根据标的配置来选择期权合约日期：
    - QQQ：优先选择到期时间大于等于1天的最近日期
    - 其他标的：根据当前所处周几选择本周或下周的期权（保留原有逻辑）
    """
    if not date_list:
        return None

    # 获取当前日期
    today = datetime.now().date()
    weekday = today.weekday()  # 周一为0，周日为6
    sorted_dates = sorted(date_list)
    base_symbol = symbol.split(".")[0].upper() if symbol else None

    if base_symbol == "QQQ":
        future_dates = [date for date in sorted_dates if date >= today]
        for date in future_dates:
            if (date - today).days >= 1:
                return date
        if future_dates:
            return future_dates[0]
        return min(
            sorted_dates,
            key=lambda d: abs((d - today).days),
        )

    # 确定目标周
    if weekday < 2:  # 周一、周二（0, 1）
        # 选择本周期权，找到本周剩余天数中最接近的日期
        target_week_start = today - timedelta(days=weekday)
        target_week_end = target_week_start + timedelta(days=6)
    else:  # 周三、周四、周五（2, 3, 4）
        # 选择下周期权，找到下周的日期
        days_until_monday = (7 - weekday) % 7
        next_week_start = today + timedelta(days=days_until_monday)
        target_week_end = next_week_start + timedelta(days=6)
        target_week_start = next_week_start

    # 在日期列表中查找最接近目标周的日期
    # 过滤出在目标周范围内的日期
    dates_in_target_week = [
        date for date in sorted_dates if target_week_start <= date <= target_week_end
    ]

    if dates_in_target_week:
        # 如果目标周内有期权到期，则选择最早的那个
        return min(dates_in_target_week)
    else:
        # 如果目标周内没有期权到期，则选择最近的一个未来日期
        future_dates = [date for date in sorted_dates if date >= today]
        if future_dates:
            return min(future_dates)
        else:
            # 如果没有未来的日期，则返回最近的日期
            return min(sorted_dates, key=lambda d: abs((d - today).days))

@timed_api_call
def select_best_options(app: MyFlask, stock_symbol: str, option_list: list[StrikePriceInfo]):
    """
    根据TradingView日内交易策略选择最佳的call和put期权
    选择标准：
    1. 选择平值附近的期权（ATM），因为它们对价格变化最敏感且有较好的流动性
    2. 考虑隐含波动率，选择相对较低的IV以降低时间价值衰减风险
    3. 考虑成交量和持仓量，确保有足够的流动性
    4. 对于日内交易，选择到期时间适中的期权（不要太短也不要太长）
    """
    # 获取标的股票的当前价格
    quote = app.quote_ctx.quote([stock_symbol])
    current_price = float(quote[0].last_done)
    print(f"标的股票当前价格: {current_price}")

    # 筛选出有效的期权（有call和put的）
    valid_options = [opt for opt in option_list if opt.call_symbol and opt.put_symbol]

    if not valid_options:
        print("没有找到有效的期权")
        return None

    # 获取期权的实时报价信息
    option_symbols = []
    for opt in valid_options:
        if opt.call_symbol:
            option_symbols.append(opt.call_symbol)
        if opt.put_symbol:
            option_symbols.append(opt.put_symbol)

    # 分批获取期权报价（避免超过API限制）
    batch_size = 500
    option_quotes = {}
    for i in range(0, len(option_symbols), batch_size):
        batch = option_symbols[i : i + batch_size]
        try:
            quotes: list[OptionQuote] = app.quote_ctx.option_quote(batch)
            for quote in quotes:
                option_quotes[quote.symbol] = quote
        except Exception as e:
            print(f"获取期权报价失败: {e}")

    # 计算每个期权的评分
    call_options = []
    put_options = []

    for opt in valid_options:
        # 处理call期权
        if opt.call_symbol and opt.call_symbol in option_quotes:
            call_quote = option_quotes[opt.call_symbol]
            call_score = calculate_option_score(call_quote, current_price, "C")
            call_options.append(
                {
                    "symbol": opt.call_symbol,
                    "strike_price": float(opt.price),
                    "quote": call_quote,
                    "score": call_score,
                }
            )

        # 处理put期权
        if opt.put_symbol and opt.put_symbol in option_quotes:
            put_quote = option_quotes[opt.put_symbol]
            put_score = calculate_option_score(put_quote, current_price, "P")
            put_options.append(
                {
                    "symbol": opt.put_symbol,
                    "strike_price": float(opt.price),
                    "quote": put_quote,
                    "score": put_score,
                }
            )

    # 根据评分排序
    call_options.sort(key=lambda x: x["score"], reverse=True)
    put_options.sort(key=lambda x: x["score"], reverse=True)

    # 选择最佳的call和put
    best_call = call_options[0] if call_options else None
    best_put = put_options[0] if put_options else None

    return {"call": best_call, "put": best_put, "current_price": current_price}


def calculate_option_score(option_quote: OptionQuote, current_price, option_type):
    """
    计算期权评分，用于选择最佳期权
    评分标准：
    1. 接近平值（权重40%）
    2. 隐含波动率适中（权重30%）
    3. 流动性好（权重30%）
    """
    try:
        strike_price_str = option_quote.strike_price
        implied_volatility_str = option_quote.implied_volatility
        open_interest = option_quote.open_interest
        volume = option_quote.volume

        # 转换数据类型
        strike_price = float(strike_price_str) if strike_price_str else 0
        implied_volatility = (
            float(implied_volatility_str) if implied_volatility_str else 0
        )

        # 1. 平值程度评分（越接近平值越好）
        if current_price <= 0 or strike_price <= 0:
            atm_score = 0
        else:
            # 计算与当前价格的距离
            distance_to_atm = abs(strike_price - current_price) / current_price
            if distance_to_atm <= 0.02:  # 2%以内
                atm_score = 1.0
            elif distance_to_atm <= 0.05:  # 5%以内
                atm_score = 0.8
            else:
                atm_score = max(0, 1 - distance_to_atm)

        # 2. 隐含波动率评分（适中的IV更好）
        # 一般来说，较低的IV更好，但也不能太低
        if 0.2 <= implied_volatility <= 0.5:
            iv_score = 1.0
        elif 0.15 <= implied_volatility <= 0.6:
            iv_score = 0.8
        else:
            iv_score = 0.5

        # 3. 流动性评分（持仓量和成交量）
        liquidity_score = min(1.0, (open_interest + volume) / 10000)

        # 综合评分（移除了到期时间评分）
        total_score = atm_score * 0.4 + iv_score * 0.3 + liquidity_score * 0.3

        return total_score
    except Exception as e:
        print(f"计算期权评分失败: {e}")
        return 0
