from core.database import context_manager_get_ro_session
from sqlalchemy import text


async def find_top5_cross_platform_fast():
    sql = text(
        """
        WITH ann_candidates AS (
            SELECT
                a.id                     AS a_id,
                a.platform               AS a_platform,
                a.platform_market_id     AS a_market_id,
                a.title                  AS a_title,
                a.normalized_title       AS a_normalized_title,
                a.semantic_text          AS a_semantic_text,
                a.description            AS a_description,
                a.embedding              AS a_embedding,
                a.semantic_embedding     AS a_semantic_embedding,

                b.id                     AS b_id,
                b.platform               AS b_platform,
                b.platform_market_id     AS b_market_id,
                b.title                  AS b_title,
                b.normalized_title       AS b_normalized_title,
                b.semantic_text          AS b_semantic_text,
                b.description            AS b_description,
                b.embedding              AS b_embedding,
                b.semantic_embedding     AS b_semantic_embedding,

                (a.embedding <-> b.embedding) AS min_distance
            FROM markets a
                     JOIN LATERAL (
                SELECT
                    id,
                    platform,
                    platform_market_id,
                    title,
                    normalized_title,
                    semantic_text,
                    description,
                    embedding,
                    semantic_embedding
                FROM markets b
                WHERE b.platform <> a.platform
                  AND b.embedding IS NOT NULL
                ORDER BY b.embedding <-> a.embedding
                    LIMIT :pair_limit
            ) b ON true
        WHERE a.embedding IS NOT NULL
            ),

            ranked AS (
        SELECT *,
            ROW_NUMBER() OVER (
            PARTITION BY b_id
            ORDER BY min_distance ASC
            ) AS rn_b
        FROM ann_candidates
            )

        SELECT
            a_id,
            a_platform,
            a_market_id,
            a_title,
            a_normalized_title,
            a_semantic_text,
            a_description,
            a_embedding,
            a_semantic_embedding,

            b_id,
            b_platform,
            b_market_id,
            b_title,
            b_normalized_title,
            b_semantic_text,
            b_description,
            b_embedding,
            b_semantic_embedding,

            min_distance
        FROM ranked
        WHERE rn_b = 1                          -- 🔒 один b → одна пара
          AND min_distance <= :max_distance
          AND a_id < b_id                      -- убирает зеркала
          AND NOT EXISTS (
            SELECT 1
            FROM pairs p
            WHERE p.market_ids @> to_jsonb(ARRAY[a_market_id, b_market_id])
              AND p.market_ids <@ to_jsonb(ARRAY[a_market_id, b_market_id])
        )
        ORDER BY min_distance ASC
            LIMIT :limit
        OFFSET :offset;
        """
    )

    async with context_manager_get_ro_session() as session:
        rows = (
            (
                await session.execute(
                    sql,
                    {
                        "limit": 30000,
                        "offset": 0,
                        "max_distance": 0.3,
                        "pair_limit": 1,
                    },
                )
            )
            .mappings()
            .all()
        )

    count = 0
    for r in rows:
        if r is not None:
            count += 1
            print(f"COUNT:{count} Distance: {r['min_distance']:.5f}")
            print(f"{r['a_platform']} — {r['a_title']}")
            print(f"{r['b_platform']} — {r['b_title']}")
            print("-" * 70)
    print(count)
    return rows

#
# async def fetch_ws(session, text):
#     # POST /encode
#     async with session.post("http://localhost/encode", json={"texts": text}) as resp:
#         data = await resp.json()
#         task_id = data["task_id"]
#
#     # Подключаемся к WebSocket
#     async with session.ws_connect(f"ws://localhost/ws/{task_id}") as ws:
#         msg = await ws.receive_json()
#
#     return msg
#
#
# async def fill_null_embedding():
#     async with aiohttp.ClientSession() as aio_session:
#         async with get_rw_session() as session:
#             query = (
#                 select(Market)
#                 .where(Market.embedding == None)
#                 .where(Market.description_embedding == None)
#             )
#             result = await session.execute(query)
#             list_markets = list(result.scalars().all())
#             for market in list_markets:
#                 emb = await fetch_ws(
#                     session=aio_session,
#                     text=[market.normalized_title, market.description],
#                 )
#                 res_emb = emb.get("embeddings")
#                 market.embedding = res_emb[0]
#                 market.description_embedding = res_emb[1]
#
#
# async def get_all_raws():
#     async with get_ro_session() as session:
#         result = await session.stream_scalars(select(Market))
#
#         with open("data.jsonl", "a", encoding="utf-8") as f:
#             async for market in result:
#                 f.write(json.dumps(market.raw, ensure_ascii=False) + "\n")
#
#
# text = """Will Microsoft be the largest company in the world by market cap on December 31?
# this market will resolve to ""yes"" if microsoft is the largest company in the world by market cap on december 31, 2025, as of market close. otherwise, this market will resolve to ""no"".
#
# the resolution source for this market will be a consensus of credible reporting.
# This is a market on predicting which company will be the largest by market capitalization on December 31, 2025."""
#
#
# async def main():
#     async with aiohttp.ClientSession() as session:
#         print(await fetch_ws(session, text))

#
# async def fetch_arbitrage_data(session: aiohttp.ClientSession, url: str) -> List[Any]:
#     """
#     Делает GET-запрос к указанному URL и возвращает распарсенные JSON-данные.
#     """
#     try:
#         async with session.get(url) as response:
#             # Проверяем статус ответа. Если это 4xx или 5xx, выбросит исключение.
#             response.raise_for_status()
#
#             # Получаем JSON. aiohttp.ClientResponse.json() сам парсит.
#             data = await response.json()
#             return data
#
#     except aiohttp.ClientResponseError as e:
#         print(f"HTTP error occurred: {e.status} - {e.message}")
#     except aiohttp.ClientConnectionError as e:
#         print(f"Connection error occurred: {e}")
#     except orjson.JSONDecodeError: # aiohttp.ClientResponse.json() может вернуть это, если что-то пошло не так
#         print("Failed to decode JSON response.")
#     except Exception as e:
#         print(f"An unexpected error occurred: {e}")
#
#     return [] # Возвращаем пустой список в случае любой ошибки
#
# async def main():
#     api_url = "http://2d64e8622bc1.vps.myjino.ru:81/"
#
#     # Используем aiohttp.ClientSession для управления подключениями
#     async with aiohttp.ClientSession() as session:
#         arbitrage_data = await fetch_arbitrage_data(session, api_url)
#         if arbitrage_data:
#             print(
#                 f"Successfully fetched {len(arbitrage_data)} arbitrage opportunities."
#             )
#             print(arbitrage_data)
#             # Если нужно, можно распарсить данные в Pydantic модели
#             # try:
#             #     validated_data: List[ArbitrageResult] = [ArbitrageResult(**item) for item in arbitrage_data]
#             #     print(f"Validated {len(validated_data)} results.")
#             # except Exception as e:
#             #     print(f"Failed to validate data: {e}")
#             #     validated_data = [] # Или обработать ошибку иначе
#         else:
#             print("No arbitrage data found or an error occurred.")

#
import asyncio
import statistics
import time
from collections import Counter

import aiohttp

API_URL = "http://2d64e8622bc1.vps.myjino.ru:8001/arbitrage/scan_cache"
REQUESTS_COUNT = 1000
# Размер батча: меньше память, видно прогресс; None = один большой gather
BATCH_SIZE = 100
# Считать тело ответа (True) или только status (False). False сильно экономит память и время.
READ_BODY = False
# Лимит одновременных соединений (0 = без лимита). После настройки nginx (worker_connections) можно поднимать до 2k–10k.
MAX_CONCURRENT = 20


async def fetch_one(
    session: aiohttp.ClientSession,
    url: str,
    read_body: bool,
    semaphore: asyncio.Semaphore | None,
) -> tuple[bool, float, int | None, str | None, str | None]:
    """Возвращает (успех, время_в_сек, статус_код, тип_исключения или None, текст_исключения или None)."""
    async def _do():
        t0 = time.perf_counter()
        try:
            async with session.get(url) as resp:
                status = resp.status
                if read_body:
                    await resp.read()
                else:
                    await resp.release()  # не качаем тело — быстрее и меньше нагрузка
                return status < 400, time.perf_counter() - t0, status, None, None
        except Exception as e:
            return False, time.perf_counter() - t0, None, type(e).__name__, str(e)

    if semaphore:
        async with semaphore:
            return await _do()
    return await _do()


async def main():
    connector = aiohttp.TCPConnector(limit=MAX_CONCURRENT or 1000)
    semaphore = asyncio.Semaphore(MAX_CONCURRENT) if MAX_CONCURRENT else None

    total_start = time.perf_counter()
    success_count = 0
    response_times: list[float] = []
    status_codes: list[int] = []
    exceptions: list[str] = []
    first_exc_message: str | None = None

    async with aiohttp.ClientSession(connector=connector) as session:
        # прогрев в той же сессии, чтобы не закрывать connector до основного прогона
        await fetch_one(session, API_URL, READ_BODY, semaphore)
        if BATCH_SIZE is None:
            tasks = [
                fetch_one(session, API_URL, READ_BODY, semaphore)
                for _ in range(REQUESTS_COUNT)
            ]
            results = await asyncio.gather(*tasks, return_exceptions=True)
            for r in results:
                if isinstance(r, Exception):
                    exceptions.append(type(r).__name__)
                    if first_exc_message is None:
                        first_exc_message = str(r)
                    continue
                ok, elapsed, status, exc, exc_msg = r
                if exc:
                    exceptions.append(exc)
                    if first_exc_message is None:
                        first_exc_message = exc_msg
                if ok:
                    success_count += 1
                if status is not None:
                    status_codes.append(status)
                response_times.append(elapsed)
        else:
            for batch_start in range(0, REQUESTS_COUNT, BATCH_SIZE):
                batch_end = min(batch_start + BATCH_SIZE, REQUESTS_COUNT)
                n = batch_end - batch_start
                tasks = [
                    fetch_one(session, API_URL, READ_BODY, semaphore)
                    for _ in range(n)
                ]
                results = await asyncio.gather(*tasks, return_exceptions=True)
                for r in results:
                    if isinstance(r, Exception):
                        exceptions.append(type(r).__name__)
                        if first_exc_message is None:
                            first_exc_message = str(r)
                        continue
                    ok, elapsed, status, exc, exc_msg = r
                    if exc:
                        exceptions.append(exc)
                        if first_exc_message is None:
                            first_exc_message = exc_msg
                    if ok:
                        success_count += 1
                    if status is not None:
                        status_codes.append(status)
                    response_times.append(elapsed)
                print(f"  batch {batch_end}/{REQUESTS_COUNT}  RPS so far: {len(response_times) / (time.perf_counter() - total_start):.0f}")

    total_elapsed = time.perf_counter() - total_start

    print()
    print(f"Total requests:    {REQUESTS_COUNT}")
    print(f"Successful (2xx):  {success_count}")
    print(f"Total time:        {total_elapsed:.2f} s")
    print(f"RPS (overall):     {REQUESTS_COUNT / total_elapsed:.2f}")
    if response_times:
        response_times.sort()
        print(f"Response time (s): min={min(response_times):.3f}  max={max(response_times):.3f}  avg={statistics.mean(response_times):.3f}")
        print(f"  p50={response_times[len(response_times)//2]:.3f}  p95={response_times[int(len(response_times)*0.95)]:.3f}  p99={response_times[int(len(response_times)*0.99)]:.3f}")
    if status_codes:
        print(f"Status codes:      {dict(Counter(status_codes))}")
    if exceptions:
        print(f"Exceptions (all):  {dict(Counter(exceptions))}")
        if first_exc_message:
            print(f"First exception:   {first_exc_message[:200]}")
        print("  -> 0 successful: все запросы падают до ответа (сеть/сервер/SSL). См. тип выше.")


if __name__ == "__main__":
    asyncio.run(main())

