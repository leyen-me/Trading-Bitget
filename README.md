# 🚀 Trading Bitget

> 🧠 基于 **Python + Bitget API** 的高性能自动化交易服务，通过 **TradingView Webhook** 实现合约做多 / 做空策略的全自动执行。

<div align="center">

[![Python](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](./LICENSE)
[![TradingView](https://img.shields.io/badge/TradingView-Webhook-blue?logo=tradingview)](https://www.tradingview.com/)
[![Bitget](https://img.shields.io/badge/Bitget-Contract-FF6B00)](https://www.bitget.com/)

</div>

---

## 🧩 项目简介

Trading Bitget 实现了从 **TradingView 信号 → Bitget 合约实盘下单** 的完整链路。专注于加密货币合约交易，适用于趋势跟踪、均值回归、突破等多种量化策略。

### 🔧 功能特性

| 功能               | 说明                                    |
| :----------------- | :-------------------------------------- |
| ✅ 自动交易执行    | 从 TradingView 信号到 Bitget 合约下单  |
| ✅ 限价单下单      | 使用盘口买一 / 卖一价提交限价订单       |
| ✅ 智能仓位控制    | 默认半仓，可配置比例                    |
| ✅ 异步 & 重试机制 | 异步执行、自动重试、未成交订单自动取消  |
| ✅ 安全机制        | 接口加密 + 敏感信息隔离                 |

---

## 📚 目录

- [📊 核心功能](#-核心功能)
- [📡 Webhook 协议](#-webhook-信号协议)
- [⚙️ 环境配置](#️-环境配置)
- [🚀 快速启动](#-快速启动)
- [🌐 API 接口](#-api-接口)
- [🤝 贡献与反馈](#-贡献与反馈)
- [📄 许可证](#-许可证)

---

## 📊 核心功能

| 功能         | 描述                                |
| :----------- | :---------------------------------- |
| Webhook 接收 | 监听 TradingView 信号               |
| 自动交易     | 执行 Bitget 合约下单逻辑            |
| 信号组合     | `buy+long`, `sell+short`, `flat` 等 |
| 高可靠性     | 自动重试 + 异步执行                 |
| 日志追踪     | 完整交易日志                        |

---

## 📡 Webhook 信号协议

TradingView → Webhook 请求示例：

```json
{
  "action": "buy",
  "sentiment": "long",
  "ticker": "TSLA",
  "token": "1234"
}
```

### 字段说明

| 字段              | 可选值                   | 含义                     |
| :---------------- | :----------------------- | :----------------------- |
| `action`          | `buy`, `sell`            | 交易动作                 |
| `sentiment`       | `long`, `short`, `flat`  | 市场观点                 |
| `ticker`          | 如 `BTCUSDT`             | 合约交易对符号           |
| `price`           | 数值                     | 可传 TradingView 当前价  |
| `stop_loss_price` | 数值                     | 可传止损价               |

### 行为映射表

| action | sentiment | 行为描述       |
| :----- | :-------- | :------------- |
| buy    | long      | 做多（买入）   |
| sell   | short     | 做空（卖出）   |
| buy    | flat      | 平空仓（回补） |
| sell   | flat      | 平多仓（卖出） |

---

## ⚙️ 环境配置

<details>
<summary>点击展开环境变量说明</summary>

| 环境变量                 | 默认值  | 说明                   |
| :----------------------- | :------ | :--------------------- |
| `BITGET_API_KEY`         | —       | Bitget API Key         |
| `BITGET_SECRET_KEY`      | —       | Bitget Secret Key      |
| `BITGET_PASSPHRASE`      | —       | Bitget Passphrase      |
| `WEBHOOK_EXPECTED_TOKEN` | `1234`  | 接口加密令牌           |
| `MAX_PURCHASE_RATIO`     | `0.5`   | 最大买入比例           |
| ...                      | ...     | 更多请查看 `config.py` |

</details>

---

## 均值回归

回归的本质是价格对价值中枢的引力作用。当市场因情绪、流动性或短期消息推动价格远离其统计均衡位（如均线、布林带中轨），过度抛售或追涨导致失衡，反向力量将逐步积聚。一旦动能衰竭，价格倾向于向均值靠拢。  

均值回归并非逆势抄底，而是捕捉“超调后的修复概率”。它依赖于市场短期记忆性和波动收敛特性——极端不会持续，修正终将到来。在关键支撑/阻力区、移动平均线、密集成交区附近，常聚集大量限价单与算法做市指令。当价格快速击穿这些区域后无力维持，会触发反向订单流，形成“反弹瀑布”，加速回归进程。真正有效的回归需要“确认”——包括缩量企稳、指标背离（如RSI）、K线形态反转（锤子线、吞没）等。假信号之所以频繁，正是因为缺乏结构支撑，仅为噪音扰动。  

均值回归本质上是“对抗惯性”的尝试，但并非每一次回调都成功。成功的交易者接受“被趋势碾压是常态”，通过小仓试错、严格止损和高盈亏比，在震荡中积累优势。价格永远在平衡与失衡之间摆动。过度即是机会，冷静即是利润。多数人害怕低点，追逐高点，因而错失最佳买点。回归思维要求逆向而行：在恐慌中寻找价值，在狂热中退出游戏。先知先觉者利用群体非理性入场；后知后觉者在反弹中途才醒悟。市场本质是不确定的，但均值提供了一个锚。它不是预测底部，而是识别极端，并对概率做出反应。`strategy/Ultimate_RSI.pine`

## 突破交易（趋势交易）

突破的本质是市场供需关系发生根本性转变，当价格长期在某一区间震荡（如支撑/阻力区间），多空双方处于动态平衡。一旦价格有效突破关键位，意味着一方力量压倒另一方，新的趋势可能形成。

突破往往伴随着重要信息的释放（如财报、政策、宏观数据）或市场情绪的累积。当价格突破关键位置时，它成为一种“信号”，被市场参与者广泛识别并响应，从而形成集体行动，推动趋势延续。关键价位附近通常聚集大量止损单和挂单（如机构订单、算法交易指令）。突破会触发这些隐藏订单，形成“流动性瀑布”，加剧价格运动。当价格突破前高时，空头止损被激活，同时追涨买盘涌入，形成正反馈。真正的突破需要“确认”——包括幅度（大实体）、时间（收盘站稳）、成交量放大等。假突破（False Breakout）之所以存在，正是因为缺乏这些确认要素，反映出市场试探性行为。

突破交易本质上是“捕捉拐点”的尝试，但并非每一次突破都成功。成功的交易者接受“失败是系统的一部分”，通过风险控制（如止损）和盈亏比管理，在长期中实现正期望值。趋势即惯性，价格一旦突破原有平衡，倾向于继续运动。突破代表趋势的启动，而趋势具有惯性。顺势而为，是对市场能量的尊重。多数人倾向于“等待确认”，导致突破初期参与度低，随后才逐步跟风。突破反映了人类认知的滞后性：人们往往在事实显现后才承认变化。先知先觉者利用这种滞后，在突破初期入场；后知后觉者在趋势中期追涨。市场本质是不确定的，但人类本能寻求确定性。它不是预测未来，而是对当下做出反应。`strategy/TSLL_5MIN_SUPERTREND_V5.pine`

---

## 🚀 快速启动

```bash
# 1️⃣ 安装依赖
pip install -r requirements.txt

# 2️⃣ 配置环境变量
export BITGET_API_KEY="xxx"
export BITGET_SECRET_KEY="xxx"
export BITGET_PASSPHRASE="xxx"

# 3️⃣ 启动服务
python app.py
```

> 🌍 默认运行在 `http://0.0.0.0:8080`

---

## 🌐 API 接口

### `POST /api/webhook`

接收 TradingView 信号并触发交易逻辑。

```bash
curl -X POST http://localhost:8080/api/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "action": "buy",
    "sentiment": "long",
    "ticker": "BTCUSDT",
    "token": "1234"
  }'
```

---

## 🤝 贡献与反馈

💡 欢迎提交 Issue 或 Pull Request
📬 如有疑问，请通过 Issues 或邮件联系作者

---

## 📄 许可证

本项目基于 **MIT License** 开源发布。

---

<div align="center">

Made with ❤️ for Traders
✨ Powering automated contract trading on Bitget ✨

</div>
