import time
from functools import wraps
from lib.MyFlask import get_current_app

def timed_api_call(func):
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            duration = time.time() - start_time
            get_current_app().logger.info(
                f"📊 API调用完成 | {func.__name__} | 耗时: {duration:.3f}s"
            )
            return result
        except Exception as e:
            duration = time.time() - start_time
            get_current_app().logger.error(
                f"🚨 API调用失败 | {func.__name__} | 耗时: {duration:.3f}s | 错误: {e}"
            )
            raise
    return wrapper