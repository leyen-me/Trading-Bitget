# wsgi.py
from app import create_app

# 创建应用实例，供 Gunicorn 使用
application = create_app()