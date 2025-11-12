import time
from lib.MyFlask import MyFlask, Position, get_current_app
from utils.decorator import timed_api_call


@timed_api_call
def get_account_balance(app: MyFlask):
    return app.trade_ctx.account_balance(currency="USD")


@timed_api_call
def get_stock_positions(app: MyFlask):
    return app.trade_ctx.stock_positions()


def fetch_and_cache_account_info(app: MyFlask):
    with app.app_context():
        """获取并缓存账户现金和持仓"""
        try:
            # 获取资产
            account_info = get_account_balance(app)

            # 限速处理，防止接口报错
            time.sleep(1)

            # 获取持仓
            resp = get_stock_positions(app)

            # 缓存到上下文
            for account in account_info:
                for cash_info in account.cash_infos:
                    if cash_info.currency == "USD":
                        app.total_cash = cash_info.available_cash

            # 缓存到上下文
            positions: list[Position] = []
            for channel in resp.channels:
                for pos in channel.positions:
                    positions.append(Position(pos.symbol, pos.quantity, pos.cost_price))
            app.positions = positions

            # 格式化持仓信息
            if positions:
                position_str = " | ".join(
                    f"{pos.symbol} {pos.quantity} @ {pos.cost_price:.2f}"
                    for pos in positions  # 使用生成器表达式更简洁
                )
            else:
                position_str = "无持仓"

            # 记录日志
            app.logger.info(
                f"✅ 账户数据已更新 | 现金: {app.total_cash:.2f} | 持仓: {position_str}"
            )

        except Exception as e:
            app.logger.error(f"❌ 定时任务失败：获取账户信息异常 | {e}")
