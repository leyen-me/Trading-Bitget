import logging
from logging import Formatter
from flask import jsonify, send_from_directory
from flask_cors import CORS
from lib.MyFlask import MyFlask
from routes.webhook import webhook_bp


def setup_logging(app: MyFlask) -> None:

    # --- 自定义日志格式 ---
    log_level = None
    if not app.debug and not app.testing:
        log_level = logging.INFO
    else:
        log_level = logging.DEBUG

    # --- 清除默认的 handler（避免重复日志）---
    app.logger.handlers.clear()

    # --- 创建一个控制台 handler ---
    handler = logging.StreamHandler()
    handler.setLevel(log_level)

    # --- 定义格式：包含时间、日志级别、文件名/函数名、消息 ---
    # in %(module)s.%(funcName)s:%(lineno)d
    formatter = Formatter(
        "[%(asctime)s] %(levelname)s : %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    handler.setFormatter(formatter)

    app.logger.addHandler(handler)
    app.logger.setLevel(log_level)


def setup_cors(app: MyFlask):
    CORS(app)


def setup_home(app: MyFlask):
    @app.route("/")
    def serve_html():
        return send_from_directory("static", "index.html")


def setup_error_handlers(app: MyFlask):
    @app.errorhandler(404)
    def not_found(e):
        app.logger.error(f"404错误: {e}")
        return jsonify({"status": "error", "message": "资源未找到", "code": 404}), 404


def setup_blueprint(app: MyFlask):
    app.register_blueprint(blueprint=webhook_bp, url_prefix="/api")
