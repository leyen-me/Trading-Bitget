from typing import cast
from flask import Flask
from flask import current_app
from utils.bitget_client import BitgetClient


class MyFlask(Flask):
    """
    自定义的 Flask 对象，用于保存全局变量
    """
    bitget_client: BitgetClient = None

    def _get_current_object(self) -> "MyFlask":
        return (
            super()._get_current_object()  # pyright: ignore[reportAttributeAccessIssue]
        )


def get_current_app() -> MyFlask:
    return cast(MyFlask, current_app)
