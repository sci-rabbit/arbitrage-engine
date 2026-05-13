# import asyncio
#
# import aiohttp
#
# from core.config import settings
# from core.orderbook_formatters.kalshi_formatter import format_kalshi_orderbook
#
#
# def dollars_fp_to_cents(entries):
#     """
#     [['0.0100', '200.00'], ...] -> [[1, 200.0], ...]  (цены в центах)
#     """
#     out = []
#     for price_str, size_str in entries or []:
#         try:
#             price_cents = int(round(float(price_str) * 100))
#             size = float(size_str)
#             out.append([price_cents, size])
#         except (TypeError, ValueError):
#             continue
#     return out
#
#
# async def test_kalshi_ws(ticker: str):
#     """
#     Тестовый коннект к Kalshi WebSocket для одного тикера.
#     Подписывается на orderbook_delta и выводит несколько нормализованных снапшотов.
#     """
#     url = settings.kalshi.ws_url
#     # path в подписи должен совпадать с реальным WS‑путём
#     headers = settings.kalshi.get_headers(method="GET", path="/trade-api/ws/v2")
#
#     async with aiohttp.ClientSession() as session:
#         async with session.ws_connect(url, headers=headers) as ws:
#             sub_msg = {
#                 "id": 1,
#                 "cmd": "subscribe",
#                 "params": {
#                     "channels": ["orderbook_delta"],
#                     "market_tickers": [ticker],
#                 },
#             }
#             await ws.send_json(sub_msg)
#             print("Subscribed to", ticker)
#
#             seen = 0
#             async for msg in ws:
#                 if msg.type != aiohttp.WSMsgType.TEXT:
#                     continue
#                 data = msg.json()
#                 msg_type = data.get("type")
#                 if msg_type not in ("orderbook_snapshot", "orderbook_delta"):
#                     continue
#
#                 print("\n=== WS message ===")
#                 print("type:", msg_type)
#
#                 if msg_type == "orderbook_snapshot":
#                     inner = data.get("msg") or {}
#                     yes_fp = inner.get("yes_dollars_fp") or []
#                     no_fp = inner.get("no_dollars_fp") or []
#
#                     api_like = {
#                         "orderbook": {
#                             "yes": dollars_fp_to_cents(yes_fp),
#                             "no": dollars_fp_to_cents(no_fp),
#                         }
#                     }
#                     formatted = format_kalshi_orderbook(api_like)
#                     print("Formatted snapshot:")
#                     print(formatted)
#                 else:
#                     # дельты можно просто смотреть сырыми
#                     print("Delta payload:", data)
#
#                 seen += 1
#                 if seen >= 10:
#                     print("Seen 10 messages, closing")
#                     break
#
#
# if __name__ == "__main__":
#     asyncio.run(test_kalshi_ws("KXBRPRES-26-LULA"))


import asyncio
import aiohttp

from core.config import settings
from core.orderbook_formatters.predictfun_formatter import format_predictfun_orderbook


async def test_predictfun_ws(market_id: str):
    """
    Тестовый коннект к Predict.fun WebSocket для одного marketId.
    Подписывается на predictOrderbook/{marketId} и печатает сырые и нормализованные ордербуки.
    """
    url = settings.predict_fun.ws_url  # wss://ws.predict.fun/ws
    api_key = settings.predict_fun.api_key

    async with aiohttp.ClientSession(
        headers={"x-api-key": api_key} if api_key else {},
    ) as session:
        async with session.ws_connect(url) as ws:
            topic = f"predictOrderbook/{market_id}"
            sub_msg = {
                "method": "subscribe",
                "requestId": 1,
                "params": [topic],
            }
            await ws.send_json(sub_msg)
            print("Subscribed to", topic)

            seen = 0
            async for msg in ws:
                if msg.type != aiohttp.WSMsgType.TEXT:
                    continue
                data = msg.json()
                if data.get("type") != "M":
                    continue
                if data.get("topic") != topic:
                    continue

                payload = data.get("data") or {}
                wrapped = {"success": True, "data": payload}
                formatted = format_predictfun_orderbook(wrapped)

                print("\n=== WS message (normalized for DB) ===")
                if formatted is None:
                    print("formatted: None")
                else:
                    print("yes_asks:", formatted["yes"]["asks"])
                    print("no_asks:", formatted["no"]["asks"])

                seen += 1
                if seen >= 5000:
                    print("Seen 5 messages, closing")
                    break


if __name__ == "__main__":
    # подставь реальный marketId Predict.fun, который у тебя есть в БД (platform_market_id)
    asyncio.run(test_predictfun_ws("5122"))