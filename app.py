from lib.MyFlask import MyFlask

from utils.register import (
    setup_blueprint,
    setup_cors,
    setup_home,
    setup_error_handlers,
    setup_logging,
    setup_scheduled_tasks,
)


def create_app():
    app = MyFlask(__name__)
    setup_cors(app)
    setup_logging(app)
    setup_home(app)
    setup_error_handlers(app)
    setup_blueprint(app)
    setup_scheduled_tasks(app)
    app.logger.info("✅ Longport SDK 初始化成功")
    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=8080, debug=False)
