from lib.MyFlask import MyFlask
from utils.bitget_client import BitgetClient

from utils.register import (
    setup_blueprint,
    setup_cors,
    setup_home,
    setup_error_handlers,
    setup_logging,
)


def create_app():
    app = MyFlask(__name__)
    setup_cors(app)
    setup_logging(app)
    setup_home(app)
    setup_error_handlers(app)
    setup_blueprint(app)
    
    # 初始化 Bitget 客户端
    try:
        app.bitget_client = BitgetClient()
        app.logger.info("✅ Bitget API 初始化成功")
    except Exception as e:
        app.logger.error(f"❌ Bitget API 初始化失败: {e}")
        raise
    
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8080, debug=False)
