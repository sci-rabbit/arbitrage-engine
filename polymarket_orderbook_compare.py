# import asyncio
# from typing import Any, Dict, List
#
# import aiohttp
#
#
# """
# Небольшой тестовый скрипт, который:
# - подключается к Polymarket CLOB WebSocket и получает orderbook по token_id;
# - запрашивает snapshot того же ордербука через HTTP API;
# - сравнивает результаты (грубое сравнение цен/объёмов).
#
# Маркет: id = 1467763
# token_ids:
#   69136365945621600854789649488423522395843457249417452310260493085275775221076
#   93414970502985248153450556501896029172111478688180132916376798785122924666574
# """
#
# TOKEN_IDS: List[str] = [
#     "69136365945621600854789649488423522395843457249417452310260493085275775221076",
#     "93414970502985248153450556501896029172111478688180132916376798785122924666574",
# ]
#
# WS_URL = "wss://ws-subscriptions-clob.polymarket.com/ws/market"
# REST_URL_TEMPLATE = "https://clob.polymarket.com/book?token_id={token_id}"
#
#
# def _normalize_levels(levels: List[Any]) -> List[Dict[str, str]]:
#     """
#     Приводит уровни к виду [{\"price\": str, \"size\": str}, ...].
#     Поддерживает как dict с ключами price/size, так и list/tuple [price, size].
#     """
#     out: List[Dict[str, str]] = []
#     for lvl in levels:
#         if isinstance(lvl, dict):
#             price = lvl.get("price")
#             size = lvl.get("size")
#         elif isinstance(lvl, (list, tuple)) and len(lvl) >= 2:
#             price, size = lvl[0], lvl[1]
#         else:
#             continue
#         try:
#             p = float(price)
#             s = float(size)
#         except (TypeError, ValueError):
#             continue
#         out.append({"price": f"{p:.2f}", "size": f"{s:.2f}"})
#     # сортируем по цене, чтобы можно было сравнивать
#     out.sort(key=lambda x: float(x["price"]))
#     return out
#
#
# async def fetch_ws_orderbooks() -> Dict[str, Dict[str, List[Dict[str, str]]]]:
#     """
#     Подключается к WS и ждёт хотя бы по одному сообщению с bids/asks для каждого token_id.
#     Возвращает словарь {token_id: {\"bids\": [...], \"asks\": [...]}}.
#     """
#     result: Dict[str, Dict[str, List[Dict[str, str]]]] = {
#         tid: {"bids": [], "asks": []} for tid in TOKEN_IDS
#     }
#     pending = set(TOKEN_IDS)
#
#     async with aiohttp.ClientSession() as session:
#         async with session.ws_connect(WS_URL) as ws:
#             sub = {
#                 "type": "market",
#                 "assets_ids": TOKEN_IDS,
#                 "initial_dump": True,
#             }
#             await ws.send_json(sub)
#
#             # ждём до 10 секунд, пока не получим данные по всем токенам
#             try:
#                 while pending:
#                     msg = await ws.receive(timeout=10)
#                     if msg.type == aiohttp.WSMsgType.TEXT:
#                         data = msg.json()
#                         if isinstance(data, list):
#                             for item in data:
#                                 _handle_ws_message(item, result, pending)
#                         else:
#                             _handle_ws_message(data, result, pending)
#                     elif msg.type in (
#                         aiohttp.WSMsgType.CLOSED,
#                         aiohttp.WSMsgType.ERROR,
#                     ):
#                         break
#             except asyncio.TimeoutError:
#                 # просто выходим с тем, что успели собрать
#                 pass
#
#     return result
#
#
# def _handle_ws_message(
#     data: Dict[str, Any],
#     store: Dict[str, Dict[str, List[Dict[str, str]]]],
#     pending: set,
# ) -> None:
#     asset_id = data.get("asset_id")
#     if not asset_id or asset_id not in store:
#         return
#
#     bids = data.get("bids") or []
#     asks = data.get("asks") or []
#
#     if bids or asks:
#         store[asset_id]["bids"] = _normalize_levels(bids)
#         store[asset_id]["asks"] = _normalize_levels(asks)
#         if asset_id in pending:
#             pending.remove(asset_id)
#
#
# async def fetch_rest_orderbooks() -> Dict[str, Dict[str, List[Dict[str, str]]]]:
#     """
#     Забирает snapshot ордербука через REST API Polymarket.
#     Возвращает ту же структуру, что и fetch_ws_orderbooks.
#     """
#     result: Dict[str, Dict[str, List[Dict[str, str]]]] = {}
#     async with aiohttp.ClientSession() as session:
#         for tid in TOKEN_IDS:
#             url = REST_URL_TEMPLATE.format(token_id=tid)
#             async with session.get(url) as resp:
#                 resp.raise_for_status()
#                 data = await resp.json()
#                 # формат аналогичен примеру: bids/asks как массивы уровней
#                 bids = data.get("bids") or []
#                 asks = data.get("asks") or []
#                 result[tid] = {
#                     "bids": _normalize_levels(bids),
#                     "asks": _normalize_levels(asks),
#                 }
#     return result
#
#
# def compare_books(
#     ws_books: Dict[str, Dict[str, List[Dict[str, str]]]],
#     rest_books: Dict[str, Dict[str, List[Dict[str, str]]]],
# ) -> None:
#     """
#     Печатает краткое сравнение для каждого token_id:
#     - количество уровней
#     - первые несколько уровней bids/asks, если они отличаются.
#     """
#     for tid in TOKEN_IDS:
#         print(f"\n=== token_id = {tid} ===")
#         ws = ws_books.get(tid) or {"bids": [], "asks": []}
#         rs = rest_books.get(tid) or {"bids": [], "asks": []}
#
#         print(
#             f"WS:   bids={len(ws['bids'])}, asks={len(ws['asks'])}; "
#             f"REST: bids={len(rs['bids'])}, asks={len(rs['asks'])}"
#         )
#
#         def first_n(levels: List[Dict[str, str]], n: int = 5) -> List[Dict[str, str]]:
#             return levels[:n]
#
#         if ws["bids"] != rs["bids"]:
#             print("  BIDS differ (first 5):")
#             print("    WS  :", first_n(ws["bids"]))
#             print("    REST:", first_n(rs["bids"]))
#         else:
#             print("  BIDS identical (normalized).")
#
#         if ws["asks"] != rs["asks"]:
#             print("  ASKS differ (first 5):")
#             print("    WS  :", first_n(ws["asks"]))
#             print("    REST:", first_n(rs["asks"]))
#         else:
#             print("  ASKS identical (normalized).")
#
#
# async def main() -> None:
#     print("Fetching WS orderbooks...")
#     ws_books = await fetch_ws_orderbooks()
#
#     print("Fetching REST snapshots...")
#     rest_books = await fetch_rest_orderbooks()
#
#     print("Comparing WS vs REST...")
#     compare_books(ws_books, rest_books)
#
#
# if __name__ == "__main__":
#     asyncio.run(main())
#
import bcrypt
print(bcrypt.hashpw(b"12345678", bcrypt.gensalt()).decode())