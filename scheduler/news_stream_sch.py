# -*- coding: utf-8 -*-

import json
import requests
from config import Config
from lib.MyFlask import MyFlask
from utils.msg import send_text

seen_news_ids = set()


def fetch_news_only_for_warmup(app: MyFlask):
    with app.app_context():
        """
        启动时预热函数：只拉取最新新闻 ID 并加入 seen_news_ids
        不做 AI 分析、不发通知
        """
        app.logger.info("📈 开始执行新闻预热（warm-up），加载最新新闻 ID...")

        with app.app_context():
            news_headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
            }
            try:
                response = requests.post(
                    "https://m.lbkrs.com/api/forward/content/stock_flash/posts",
                    json={
                        "market": "US",
                        "limit": 20,
                        "next_params": {},
                        "important_only": True,
                        "counter_ids": [],
                        "slug": "stock_flash",
                        "has_derivatives": True,
                        "filter_pins": False,
                        "marquee": False,
                    },
                    headers=news_headers,
                    timeout=10,
                )
                if response.status_code != 200:
                    app.logger.error(
                        f"预热请求失败: {response.status_code}, {response.text}"
                    )
                    return

                raw_news = response.json().get("data", {}).get("articles", [])
                new_count = 0
                for item in raw_news:
                    news_id = item["id"]
                    if news_id not in seen_news_ids:
                        seen_news_ids.add(news_id)
                        new_count += 1

                app.logger.info(
                    f"✅ 预热完成，共加载 {len(raw_news)} 条新闻，去重后新增 {new_count} 个 ID 到 seen_news_ids"
                )

            except Exception as e:
                app.logger.error(f"预热过程中发生异常: {e}")


def fetch_and_analyze_news_fundamentals(app: MyFlask) -> str:
    app.logger.info(f"基本面分析定时任务开始运行✅")
    with app.app_context():

        api_key = Config.MODELSCOPE_API_KEY
        if not api_key:
            raise RuntimeError("MODELSCOPE_API_KEY 未设置")

        news_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36"
        }
        news_response = requests.post(
            "https://m.lbkrs.com/api/forward/content/stock_flash/posts",
            json={
                "market": "US",
                "limit": 20,
                "next_params": {},
                "important_only": True,
                "counter_ids": [],
                "slug": "stock_flash",
                "has_derivatives": True,
                "filter_pins": False,
                "marquee": False,
            },
            headers=news_headers,
        )
        if news_response.status_code != 200:
            raise Exception(f"NEWS 请求失败: {news_response.text}")

        news_input = ""
        raw_news = news_response.json().get("data", {}).get("articles", [])

        if len(raw_news) <= 0:
            news_input = "近期暂无新闻"
        else:
            filtered_news = []
            for news_item in raw_news:
                if news_item["id"] in seen_news_ids:
                    continue
                seen_news_ids.add(news_item["id"])
                filtered_news.append(news_item)
            if len(filtered_news) <= 0:
                return "暂无新闻"

            news_input = ""
            for item in filtered_news:
                relatedSymbols = ",".join(
                    item2.split("/")[-1] + ".US"
                    for item2 in item.get("counter_ids", [])
                    if item2.split("/")[1] == "US"
                )
                title = item.get("title")

                news_input += "(" + relatedSymbols + ")\n"
                if title:
                    news_input += item.get("title")
                    news_input += "\n"
                news_input += item.get("description_html")
                news_input += "\n\n"

        system_prompt = f"""
        你是一个专业的美股财经分析师，具备CFA级别的分析能力。请从以下新闻内容中，严格识别并提取**真正影响公司基本面**的信息。

        📌 判断标准：只有当信息属于以下 **12 类实质性变化之一**，且有具体事实支撑时，才视为“影响基本面”。否则应归类为非基本面信息。

        🔹 【影响基本面的12类情形】
            1. 财务表现变化：实际财报数据（收入、利润、毛利率、现金流等）或重大盈利预测调整。
            2. 重大资本运作：并购、分拆、私有化、退市、大规模增发/回购等。
            3. 核心业务运营变动：工厂投产/关闭、供应链中断、产能扩张、重大合同签订或丢失。
            4. 产品生命周期事件：新产品上市并开始贡献收入、核心技术突破、关键产品退市。
            5. 管理层与战略转向：高管变更伴随公司战略方向调整（如转型AI、退出某市场）。
            6. 监管与法律后果：被SEC/FDA/FTC等机构处罚、诉讼败诉导致重大赔偿或经营限制。
            7. 市场竞争格局变化：主要竞争对手发生重大变故，或本公司市场份额显著提升/流失。
            8. 客户与渠道重大变动：获得/失去大客户、进入关键分销渠道或政府采购名单。
            9. 技术或知识产权进展：核心专利获批或失效、关键技术被绕开、遭遇侵权诉讼。
            10. 债务与融资能力变化：信用评级下调至垃圾级、再融资失败、利率重设大幅增加财务成本。
            11. ESG事件 → 仅限造成实质经济损失者：如自然灾害损毁设施、罢工导致停产、碳税增加年成本超5%。
            12. 宏观因素 → 必须明确传导机制到该公司：例如利率上升导致其贷款成本剧增、汇率波动使其海外收入大幅缩水。

        🚫 【明确排除项｜不构成基本面变化】
            - 股价波动（如“今日上涨8%”）
            - 分析师评级或目标价调整
            - 市场情绪、投资者热议、社交媒体言论
            - 宏观经济评论（无具体传导路径）
            - 未证实的传闻或CEO个人观点表达
            - 纯粹ESG舆论争议（无实际罚款或客户流失）
            - 技术图表信号（如突破均线）

        输出要求：
            - 输出必须为**合法 JSON 数组**，不得包含任何额外说明或文本。
            - 不要推测、不要外推、不要添加原文未提及的信息。只基于给定内容做客观判断。
            - 输出时，只考虑基本面变化的新闻，若处于排除项之中，请忽略该新闻不作回答。
            - 若所有新闻中均未提及任何可能影响公司基本面的事件，请返回空数组：[]

        JSON 格式如下：
        [
            {{
                "stock_codes": "股票代码列表（没有则为[]）",
                "event_type": "从上述1-12中选择最匹配的一项编号",
                "summary": "简要说明为何此项构成基本面变化",
                "impact": "正面 / 负面",
                "suggested_action": "观望 / 逢低布局 / 追高 / 做空"
            }}
        ]

        新闻内容如下：
        {news_input}
        """

        data = {
            "model": "Qwen/Qwen3-235B-A22B-Instruct-2507",
            "messages": [{"role": "user", "content": system_prompt}],
            "stream": False,
        }

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        response = requests.post(
            "https://api-inference.modelscope.cn/v1/chat/completions",
            json=data,
            headers=headers,
        )

        if response.status_code != 200:
            raise Exception(f"AI 请求失败: {response.text}")

        result = response.json()
        res = result["choices"][0]["message"]["content"]
        
        try:
            arr = json.loads(res)
            if len(arr) > 0:
                for msg in arr:
                    stock_codes = ",".join(msg.get("stock_codes", []))
                    summary = msg.get("summary")
                    impact = msg.get("impact")
                    suggested_action = msg.get("suggested_action")
                    icon = (
                        "📈" if impact == "正面" else "📉" if impact == "负面" else "⏸️"
                    )
                    send_text(
                        subject="新闻分析",
                        body=f"【{stock_codes}】{ icon }：\n\n{summary}\n\n（可以考虑：{suggested_action}）",
                        enable_email=False # 只发送到 QQ 群
                    )
        except Exception as e:
            app.logger.error(e)
        return res
