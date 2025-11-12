from dataclasses import dataclass
from typing import cast
from decimal import Decimal

from flask import Flask
from flask import current_app
from longport.openapi import TradeContext, QuoteContext
from longport.openapi import Config as LongPortConfig


@dataclass
class Position:
    symbol: str
    quantity: Decimal
    cost_price: Decimal


@dataclass
class DepthData:
    ask: Decimal | None
    bid: Decimal | None


class MyFlask(Flask):
    """
    自定义的 Flask 对象，用于保存全局变量，和类型提示
    """
    trade_ctx: TradeContext = TradeContext(LongPortConfig.from_env())
    quote_ctx: QuoteContext = QuoteContext(LongPortConfig.from_env())
    depth_cache: dict[str, DepthData] = {}
    total_cash = Decimal(0)
    positions: list[Position] = []
    today_options: list[str] = []

    def _get_normalize_symbol(self, symbol: str) -> str:
        corrections = {"TSLL.US": "TSLA.US", "TSLQ.US": "TSLA.US"}
        return corrections.get(symbol, symbol)

    def _get_current_object(self) -> "MyFlask":
        return (
            super()._get_current_object()  # pyright: ignore[reportAttributeAccessIssue]
        )


def get_current_app() -> MyFlask:
    return cast(MyFlask, current_app)
