import requests
import time
from datetime import datetime

# 你的两个服务地址和目标网站
ENDPOINTS = {
    "tradingview": "https://www.tradingview.com",
    "longport": "https://open.longportapp.com"
}

def measure_latency(url, timeout=10):
    try:
        start = time.time()
        resp = requests.get(url, timeout=timeout)
        end = time.time()
        # 返回状态码和延迟（毫秒）
        return resp.status_code, int((end - start) * 1000)
    except Exception as e:
        return None, str(e)

def check_all_sites():
    results = {}
    for name, url in ENDPOINTS.items():
        status, latency = measure_latency(url)
        results[name] = {"status": status, "latency_ms": latency}
        print(f"{datetime.now().strftime('%H:%M:%S')} | {name:12} | {status} | {latency} ms")