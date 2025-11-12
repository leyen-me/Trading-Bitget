import hmac
import hashlib
import base64
import time
import json
import requests
from typing import Optional, Dict, Any
from config import Config


class BitgetClient:
    """Bitget API 客户端，处理签名和请求"""
    
    def __init__(self):
        self.api_key = Config.BITGET_API_KEY
        self.secret_key = Config.BITGET_SECRET_KEY
        self.passphrase = Config.BITGET_PASSPHRASE
        self.base_url = Config.BITGET_BASE_URL
        
        if not all([self.api_key, self.secret_key, self.passphrase]):
            raise ValueError("Bitget API 配置不完整，请设置 BITGET_API_KEY, BITGET_SECRET_KEY, BITGET_PASSPHRASE")
    
    def _sign(self, timestamp: str, method: str, request_path: str, body: str = "") -> str:
        """生成 HMAC SHA256 签名"""
        message = timestamp + method + request_path + body
        mac = hmac.new(
            bytes(self.secret_key, encoding='utf8'),
            bytes(message, encoding='utf8'),
            digestmod=hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode()
    
    def _get_headers(self, method: str, request_path: str, body: str = "") -> Dict[str, str]:
        """获取请求头"""
        timestamp = str(int(time.time() * 1000))
        sign = self._sign(timestamp, method, request_path, body)        
        
        return {
            "ACCESS-KEY": self.api_key,
            "ACCESS-SIGN": sign,
            "ACCESS-TIMESTAMP": timestamp,
            "ACCESS-PASSPHRASE": self.passphrase,
            "Content-Type": "application/json",
            "locale": "en-US"
        }
    
    def _request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """发送请求"""
        request_path = endpoint
        body = ""
        
        # 构建查询字符串
        if method == "GET" and params:
            query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
            request_path = f"{endpoint}?{query_string}"
        elif method in ["POST", "PUT"] and data:
            body = json.dumps(data, separators=(',', ':'))
        
        # 签名时使用完整路径（包含查询参数）
        url = f"{self.base_url}{request_path}"
        headers = self._get_headers(method, request_path, body)
        
        
        try:
            if method == "GET":
                response = requests.get(url, headers=headers)
            elif method == "POST":
                response = requests.post(url, headers=headers, json=data)
            elif method == "PUT":
                response = requests.put(url, headers=headers, json=data)
            elif method == "DELETE":
                response = requests.delete(url, headers=headers)
            else:
                raise ValueError(f"不支持的 HTTP 方法: {method}")
            
            response.raise_for_status()
            result = response.json()
            
            if result.get("code") != "00000":
                raise Exception(f"Bitget API 错误: {result.get('msg', '未知错误')}")
            
            return result.get("data", result)
        except requests.exceptions.RequestException as e:
            # 延迟导入避免循环导入
            from lib.MyFlask import get_current_app
            get_current_app().logger.error(f"Bitget API 请求失败: {e}")
            raise
    
    def get_account_info(self, product_type: str = "umcbl") -> Dict[str, Any]:
        """
        获取账户信息
        
        Args:
            product_type: 产品线类型，可选值：
                - umcbl: USDT专业合约（默认）
                - dmcbl: 混合合约
                - cmcbl: USDC专业合约
                - sumcbl: USDT专业合约模拟盘
                - sdmcbl: 混合合约模拟盘
                - scmcbl: USDC专业合约模拟盘
        """
        return self._request("GET", "/api/mix/v1/account/accounts", params={
            "productType": product_type
        })
    
    def get_position(self, symbol: str, margin_coin: str = "USDT") -> Dict[str, Any]:
        """获取单个合约仓位信息"""
        return self._request("GET", f"/api/mix/v1/position/singlePosition-v2", params={
            "symbol": symbol,
            "marginCoin": margin_coin
        })
    
    def get_all_positions(self, product_type: str = "umcbl", margin_coin: str = "USDT") -> Dict[str, Any]:
        """获取全部合约仓位信息"""
        return self._request("GET", f"/api/mix/v1/position/allPosition-v2", params={
            "productType": product_type,
            "marginCoin": margin_coin
        })
    
    def get_ticker(self, symbol: str) -> Dict[str, Any]:
        """获取单个Ticker行情"""
        return self._request("GET", f"/api/mix/v1/market/ticker", params={
            "symbol": symbol
        })
    
    def get_depth(self, symbol: str, limit: int = 5) -> Dict[str, Any]:
        """获取深度行情"""
        return self._request("GET", f"/api/mix/v1/market/depth", params={
            "symbol": symbol,
            "limit": limit
        })
    
    def place_order(
        self,
        symbol: str,
        side: str,  # "open_long", "open_short", "close_long", "close_short"
        order_type: str,  # "limit", "market"
        size: str,
        price: Optional[str] = None,
        product_type: str = "umcbl",
        margin_coin: str = "USDT",
        margin_mode: str = "isolated",  # "isolated" or "crossed"
        leverage: Optional[str] = None,
    ) -> Dict[str, Any]:
        """下单"""
        data = {
            "symbol": symbol,
            "marginCoin": margin_coin,
            "side": side,
            "orderType": order_type,
            "size": str(size),
        }
        
        if order_type == "limit" and price:
            data["price"] = str(price)
        
        # 如果指定了杠杆，添加到请求中
        if leverage:
            data["leverage"] = leverage
        
        return self._request("POST", "/api/mix/v1/order/placeOrder", data=data)
    
    def cancel_order(self, symbol: str, order_id: str, product_type: str = "USDT-FUTURES") -> Dict[str, Any]:
        """撤单"""
        return self._request("POST", "/api/mix/v1/order/cancel-order", data={
            "symbol": symbol,
            "orderId": order_id,
            "productType": product_type
        })
    
    def get_current_orders(self, symbol: str, product_type: str = "USDT-FUTURES") -> Dict[str, Any]:
        """获取当前委托"""
        return self._request("GET", "/api/mix/v1/order/current", params={
            "symbol": symbol,
            "productType": product_type
        })
    
    def get_order_detail(self, symbol: str, order_id: str, product_type: str = "USDT-FUTURES") -> Dict[str, Any]:
        """获取订单详情"""
        return self._request("GET", "/api/mix/v1/order/detail", params={
            "symbol": symbol,
            "orderId": order_id,
            "productType": product_type
        })
    
    def get_openable_size(
        self, 
        symbol: str,
        margin_coin: str,
        open_price: str,
        open_amount: str,
        leverage: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        获取可开数量
        
        Args:
            symbol: 产品ID，必须大写，如 "SBTCSUSDT_SUMCBL"
            margin_coin: 保证金币种，如 "SUSDT" 或 "USDT"
            open_price: 开仓价格
            open_amount: 开仓金额
            leverage: 杠杆倍数（可选，默认20）
        
        Returns:
            Dict: 包含 openCount 的响应数据
        """
        data = {
            "symbol": symbol.upper(),  # 确保大写
            "marginCoin": margin_coin,
            "openPrice": open_price,
            "openAmount": open_amount
        }
        
        if leverage:
            data["leverage"] = leverage
        
        return self._request("POST", "/api/mix/v1/account/open-count", data=data)
    
    def set_leverage(
        self,
        symbol: str,
        leverage: str,
        margin_coin: str = "USDT",
    ) -> Dict[str, Any]:
        """设置杠杆倍数"""
        return self._request("POST", "/api/mix/v1/account/setLeverage", data={
            "symbol": symbol,
            "marginCoin": margin_coin,
            "leverage": leverage,
        })