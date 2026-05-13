"""
Тестовый модуль для проверки MarketSimilarityService.
Позволяет передать два текста и получить результат similarity.
"""

import os
import sys
import time
import warnings
from pathlib import Path
from sentence_transformers import SentenceTransformer
from services.similarity_service.service import MarketSimilarityService 
from services.similarity_service.channels.title import TitleChannel
from services.similarity_service.channels.semantic import SemanticChannel
from core import Market

# Подавляем предупреждения HuggingFace о токене (не критично для тестов)
warnings.filterwarnings('ignore', message='.*HF_TOKEN.*')

# Глобальная модель для переиспользования (загружается один раз)
_model = None

def check_model_cache(model_name: str = 'all-mpnet-base-v2'):
    """Проверяет, есть ли модель в кэше HuggingFace."""
    try:
        # Стандартные пути к кэшу HuggingFace
        home = Path.home()
        possible_cache_dirs = [
            home / ".cache" / "huggingface" / "hub",
            home / ".cache" / "huggingface" / "transformers",
        ]
        
        # Также проверяем через переменную окружения
        if "HF_HOME" in os.environ:
            possible_cache_dirs.insert(0, Path(os.environ["HF_HOME"]) / "hub")
        
        print(f"\n🔍 Проверка кэша модели: sentence-transformers/{model_name}")
        
        for cache_dir in possible_cache_dirs:
            if not cache_dir.exists():
                continue
            
            # Ищем модель в кэше (может быть в разных форматах)
            search_patterns = [
                f"**/models--sentence-transformers--{model_name.replace('-', '--')}",
                f"**/*{model_name}*",
                f"**/sentence-transformers/{model_name}",
            ]
            
            for pattern in search_patterns:
                model_paths = list(cache_dir.glob(pattern))
                if model_paths:
                    # Нашли модель
                    model_path = model_paths[0]
                    total_size = 0
                    file_count = 0
                    for f in model_path.rglob('*'):
                        if f.is_file():
                            total_size += f.stat().st_size
                            file_count += 1
                    
                    size_mb = total_size / (1024 * 1024)
                    print(f"   ✅ Найдено в кэше: {model_path.name}")
                    print(f"      Размер: {size_mb:.1f} MB ({file_count} файлов)")
                    print(f"      Путь: {model_path}")
                    return True
        
        print(f"   ❌ Модель не найдена в кэше")
        print(f"      Проверенные директории:")
        for cd in possible_cache_dirs:
            status = "✅ существует" if cd.exists() else "❌ не существует"
            print(f"         - {cd}: {status}")
        return False
        
    except Exception as e:
        print(f"   ⚠️  Ошибка при проверке кэша: {e}")
        import traceback
        traceback.print_exc()
        return False

def get_model():
    """Lazy loading модели для ускорения запуска."""
    global _model
    if _model is None:
        model_name = 'all-mpnet-base-v2'
        
        print("\n" + "=" * 80)
        print("📦 Загрузка модели SentenceTransformer")
        print("=" * 80)
        
        # Проверяем кэш
        in_cache = check_model_cache(model_name)
        
        if in_cache:
            print("\n⏳ Загрузка из кэша (должно быть быстро)...")
        else:
            print("\n📥 Скачивание модели из интернета...")
            print("   ⚠️  Это может занять 1-3 минуты при первом запуске!")
            print("   Размер: ~420 MB")
            print("   Модель: sentence-transformers/all-mpnet-base-v2")
            print("   Пожалуйста, подождите...")
        
        print("\n⏳ Инициализация модели...")
        print("   ⚠️  Это может занять 15-60 секунд даже из кэша!")
        print("   (Модель ~420MB загружается в оперативную память)")
        sys.stdout.flush()
        start_time = time.time()
        
        try:
            # Запускаем таймер в отдельном потоке, чтобы видеть что процесс идёт
            import threading
            
            timer_active = [True]
            
            def show_timer():
                """Показывает таймер каждые 5 секунд."""
                last_time = 0
                while timer_active[0]:
                    elapsed = time.time() - start_time
                    if elapsed - last_time >= 5:
                        print(f"   ⏱️  Прошло {elapsed:.0f} секунд... (подождите, модель загружается)")
                        sys.stdout.flush()
                        last_time = elapsed
                    time.sleep(1)
            
            timer_thread = threading.Thread(target=show_timer, daemon=True)
            timer_thread.start()
            
            print("   Загрузка SentenceTransformer...")
            sys.stdout.flush()
            
            # Здесь может зависнуть - это нормально для больших моделей
            _model = SentenceTransformer(model_name)
            
            timer_active[0] = False
            elapsed = time.time() - start_time
            
            print(f"\n✅ Модель загружена успешно!")
            print(f"   Время: {elapsed:.1f} секунд ({elapsed/60:.1f} минут)")
            
            # Проверяем размер модели
            if hasattr(_model, 'get_sentence_embedding_dimension'):
                dim = _model.get_sentence_embedding_dimension()
                print(f"   Размерность embedding: {dim}")
            
            print("=" * 80 + "\n")
            
        except Exception as e:
            print(f"\n❌ Ошибка при загрузке модели: {e}")
            print("\nВозможные причины:")
            print("  1. Нет интернета для скачивания модели")
            print("  2. Недостаточно места на диске")
            print("  3. Проблемы с доступом к HuggingFace Hub")
            raise
    
    return _model

def create_mock_market(title: str, description: str = None) -> Market:
    """
    Создает mock объект Market с нужными атрибутами для тестирования.
    
    Args:
        title: Заголовок маркета
        description: Описание маркета (опционально)
    
    Returns:
        Market объект с заполненными атрибутами
    """
    model = get_model()
    
    # Генерируем embeddings
    print(f"Генерация embedding для: {title[:50]}...")
    embedding = model.encode(title, normalize_embeddings=True).tolist()
    semantic_text = title + " " + (description or "")
    semantic_embedding = model.encode(semantic_text, normalize_embeddings=True).tolist()
    print("Embeddings сгенерированы.")
    
    # Создаем Market объект
    # Используем hash для генерации уникального id
    market_id = abs(hash(title)) % (10 ** 9)  # Положительное число для id
    
    market = Market(
        id=market_id,
        platform="test",
        platform_market_id=f"test_{hash(title)}",
        event_id="test_event",
        category="test",
        title=title,
        normalized_title=title.lower().strip(),
        description=description or "",
        semantic_text=semantic_text,
        embedding=embedding,
        semantic_embedding=semantic_embedding,
        raw={},
        is_binary=True,
        token_ids=[],
    )
    return market


def test_hard_gate_detailed(a_text: str, b_text: str, a_description: str = None, b_description: str = None):
    """
    Детальная диагностика hard_gate - проверяет каждый слой отдельно.
    """
    from core.similarity.entites.client import same_person, share_key_entities
    from core.similarity.numeric.client import get_numeric_result
    from core.similarity.temporal.client import get_temporal_similarity
    from core.similarity.entites.parser import extract_entities, extract_tickers, extract_persons
    
    print("\n" + "=" * 80)
    print("🔍 ДЕТАЛЬНАЯ ДИАГНОСТИКА HARD GATE")
    print("=" * 80)
    
    # Создаем mock маркеты
    market_a = create_mock_market(a_text, a_description)
    market_b = create_mock_market(b_text, b_description)
    
    text_a = market_a.normalized_title + " " + (market_a.description or "")
    text_b = market_b.normalized_title + " " + (market_b.description or "")
    
    print(f"\nТекст A: {a_text}")
    print(f"Текст B: {b_text}")
    print(f"\nNormalized A: {market_a.normalized_title}")
    print(f"Normalized B: {market_b.normalized_title}")
    
    results = {}
    
    # 1. Person disambiguation
    print("\n" + "-" * 80)
    print("1️⃣  ПРОВЕРКА: Person disambiguation (same_person)")
    print("-" * 80)
    try:
        persons_a = extract_persons(text_a)
        persons_b = extract_persons(text_b)
        same_person_result = same_person(text_a, text_b)
        
        print(f"   Извлечённые персоны из A: {persons_a}")
        print(f"   Извлечённые персоны из B: {persons_b}")
        print(f"   Пересечение: {persons_a & persons_b if persons_a and persons_b else set()}")
        print(f"   ✅ Результат: {same_person_result}")
        
        results['same_person'] = {
            'passed': same_person_result,
            'persons_a': persons_a,
            'persons_b': persons_b,
        }
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        results['same_person'] = {'passed': False, 'error': str(e)}
    
    # 2. Entity anchors
    print("\n" + "-" * 80)
    print("2️⃣  ПРОВЕРКА: Entity anchors (share_key_entities)")
    print("-" * 80)
    try:
        entities_a = extract_entities(market_a.normalized_title)
        entities_b = extract_entities(market_b.normalized_title)
        tickers_a = extract_tickers(market_a.normalized_title)
        tickers_b = extract_tickers(market_b.normalized_title)
        share_entities_result = share_key_entities(market_a.normalized_title, market_b.normalized_title)
        
        print(f"   Извлечённые entities из A: {entities_a}")
        print(f"   Извлечённые entities из B: {entities_b}")
        print(f"   Пересечение entities: {entities_a & entities_b if entities_a and entities_b else set()}")
        print(f"   Количество общих entities: {len(entities_a & entities_b) if entities_a and entities_b else 0}")
        print(f"   Требуется минимум: 2")
        print(f"   Tickers A: {tickers_a}")
        print(f"   Tickers B: {tickers_b}")
        print(f"   Tickers совпадают: {tickers_a == tickers_b}")
        print(f"   ✅ Результат: {share_entities_result}")
        
        results['share_key_entities'] = {
            'passed': share_entities_result,
            'entities_a': entities_a,
            'entities_b': entities_b,
            'overlap': entities_a & entities_b if entities_a and entities_b else set(),
        }
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        results['share_key_entities'] = {'passed': False, 'error': str(e)}
    
    # 3. Numeric contradiction
    print("\n" + "-" * 80)
    print("3️⃣  ПРОВЕРКА: Numeric contradiction")
    print("-" * 80)
    try:
        numeric = get_numeric_result(market_a.normalized_title, market_b.normalized_title)
        numeric_conflict = numeric.get("numeric_conflict", False)
        
        print(f"   Numeric constraints A: {numeric.get('numeric_a', [])}")
        print(f"   Numeric constraints B: {numeric.get('numeric_b', [])}")
        print(f"   Numeric context match: {numeric.get('numeric_context_match', False)}")
        print(f"   ❌ Numeric conflict: {numeric_conflict}")
        print(f"   ✅ Результат: {not numeric_conflict}")
        
        results['numeric'] = {
            'passed': not numeric_conflict,
            'numeric_conflict': numeric_conflict,
            'numeric_a': numeric.get('numeric_a', []),
            'numeric_b': numeric.get('numeric_b', []),
        }
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        results['numeric'] = {'passed': False, 'error': str(e)}
    
    # 4. Temporal contradiction
    print("\n" + "-" * 80)
    print("4️⃣  ПРОВЕРКА: Temporal contradiction")
    print("-" * 80)
    try:
        temporal = get_temporal_similarity(market_a.normalized_title, market_b.normalized_title)
        temporal_score = temporal.get("temporal", 0.0)
        interval_a = temporal.get("interval_a")
        interval_b = temporal.get("interval_b")
        
        print(f"   Temporal interval A: {interval_a}")
        print(f"   Temporal interval B: {interval_b}")
        print(f"   Temporal score: {temporal_score}")
        print(f"   Требуется: > 0.0")
        print(f"   ✅ Результат: {temporal_score > 0.0}")
        
        # Дополнительная информация о парсинге
        from core.similarity.temporal.parser import parse_temporal
        parsed_a = parse_temporal(market_a.normalized_title)
        parsed_b = parse_temporal(market_b.normalized_title)
        print(f"   Парсинг A напрямую: {parsed_a}")
        print(f"   Парсинг B напрямую: {parsed_b}")
        
        results['temporal'] = {
            'passed': temporal_score > 0.0,
            'temporal_score': temporal_score,
            'interval_a': interval_a,
            'interval_b': interval_b,
        }
    except Exception as e:
        print(f"   ❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
        results['temporal'] = {'passed': False, 'error': str(e)}
    
    # Итоговый результат
    print("\n" + "=" * 80)
    print("📊 ИТОГОВЫЙ РЕЗУЛЬТАТ HARD GATE")
    print("=" * 80)
    
    all_passed = all(r.get('passed', False) for r in results.values())
    
    print(f"\n1. Person disambiguation:     {'✅ PASS' if results.get('same_person', {}).get('passed') else '❌ FAIL'}")
    print(f"2. Entity anchors:            {'✅ PASS' if results.get('share_key_entities', {}).get('passed') else '❌ FAIL'}")
    print(f"3. Numeric (no conflict):     {'✅ PASS' if results.get('numeric', {}).get('passed') else '❌ FAIL'}")
    print(f"4. Temporal (score > 0):      {'✅ PASS' if results.get('temporal', {}).get('passed') else '❌ FAIL'}")
    print(f"\n{'✅ HARD GATE ПРОЙДЕН' if all_passed else '❌ HARD GATE НЕ ПРОЙДЕН'}")
    print("=" * 80 + "\n")
    
    return results


def test_similarity(a_text: str, b_text: str, a_description: str = None, b_description: str = None):
    """
    Тестирует similarity между двумя текстами.
    
    Args:
        a_text: Первый заголовок
        b_text: Второй заголовок
        a_description: Описание первого маркета (опционально)
        b_description: Описание второго маркета (опционально)
    
    Returns:
        Результат similarity или None
    """
    print("\nСоздание mock маркетов...")
    # Создаем mock маркеты
    market_a = create_mock_market(a_text, a_description)
    market_b = create_mock_market(b_text, b_description)
    
    print("Инициализация MarketSimilarityService...")
    # Создаем mock репозиторий (не используется в compute_similarity)
    class MockRepo:
        pass
    
    # Инициализируем сервис
    service = MarketSimilarityService(
        repo=MockRepo(),
        channels=[TitleChannel(), SemanticChannel()],
        threshold=0.7,
        max_distance=0.7,
        top_n_per_a=1,
    )
    
    print("Вычисление similarity...")
    # Вычисляем similarity
    result = service.compute_similarity(market_a, market_b)
    print("Готово!")
    
    return result


if __name__ == "__main__":
    try:
        # Тестовые данные
        a_text = "Will the spot price of Solana be above $150.00 before Jan 1, 2027 at 12:00 AM ET?"
        b_text = "Will the price of Solana be above $150 on January 19?"
        
        # Сначала делаем детальную диагностику hard_gate
        gate_results = test_hard_gate_detailed(a_text, b_text)
        
        print("\n" + "=" * 80)
        print("Тестирование MarketSimilarityService")
        print("=" * 80)
        print(f"\nТекст A: {a_text}")
        print(f"Текст B: {b_text}\n")
        print("-" * 80)
        
        result = test_similarity(a_text, b_text)
    
        if result:
            print("\n✅ Результат similarity:")
            print(f"  Final Score: {result['final_score']}")
            print(f"  Cross Encoder: {result['cross_encoder']}")
            print(f"  HF Entity Score: {result['hf_entity_score']}")
            print(f"  Channels:")
            for channel_name, score in result['channels'].items():
                print(f"    - {channel_name}: {score}")
        else:
            print("\n❌ Similarity не найдена (результат None)")
            print("Возможные причины:")
            print("  - Hard gate не пройден")
            print("  - Cross encoder score ниже threshold")
            print("  - Channel scores = 0")
        
        print("\n" + "=" * 80)
    except Exception as e:
        print(f"\n❌ Ошибка при выполнении: {e}")
        import traceback
        traceback.print_exc()

