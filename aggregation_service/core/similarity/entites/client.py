from rapidfuzz import fuzz

from core.similarity.entites.hf_gates import extract_entities_hf
from core.similarity.entites.parser import extract_entities, extract_persons, extract_tickers

# Пороги fuzzy-matching для entity matching
NER_ENTITY_FUZZY_THRESHOLD = 80   # мин. схожесть для совпадения NER-сущностей
FIRST_TOKEN_FUZZY_THRESHOLD = 70  # мин. схожесть первого значимого токена
PERSON_FUZZY_THRESHOLD = 80       # мин. схожесть для совпадения персон
MIN_ENTITY_OVERLAP = 1            # мин. кол-во общих сущностей для валидной пары
MAX_PERSON_WORDS = 3              # макс. слов в имени персоны (эвристика)

verbs_prepositions = {
    "be",
    "before",
    "after",
    "stay",
    "above",
    "below",
    "in",
    "on",
    "at",
    "will",
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec",
}

# Только 4 слова в начале заголовка — не субъект (вопрос/артикль). Без списков предикатов.
_FIRST_TOKEN_SKIP = {"will", "the", "a", "an"}

def _first_substantive_token(text: str) -> str:
    """Первый токен, не входящий в _FIRST_TOKEN_SKIP (субъект/тикер)."""
    for word in text.lower().replace("?", "").split():
        clean = "".join(c for c in word if c.isalnum() or c == ".")
        if clean and clean not in _FIRST_TOKEN_SKIP:
            return clean
    return ""

def _ner_entities_match(ents_a: list, ents_b: list, threshold: int = NER_ENTITY_FUZZY_THRESHOLD) -> bool:
    """Есть ли хотя бы одна пара сущностей одного типа с fuzzy >= threshold."""
    for (e1, t1) in ents_a:
        for (e2, t2) in ents_b:
            if t1 == t2 and fuzz.ratio(e1, e2) >= threshold:
                return True
    return False

def share_key_entities(a: str, b: str) -> bool:
    if extract_tickers(a) != extract_tickers(b):
        return False

    # Когда в обоих есть NER-сущности (ORG/PER/LOC) — требуем хотя бы одно совпадение
    try:
        ents_a = extract_entities_hf(a)
        ents_b = extract_entities_hf(b)
        if ents_a and ents_b:
            if not _ner_entities_match(ents_a, ents_b):
                return False
    except Exception:
        pass

    # Универсальная проверка по первому значимому токену (без списков предикатов)
    tok_a = _first_substantive_token(a)
    tok_b = _first_substantive_token(b)
    if tok_a and tok_b and fuzz.ratio(tok_a, tok_b) < FIRST_TOKEN_FUZZY_THRESHOLD:
        return False

    ea = extract_entities(a)
    eb = extract_entities(b)

    if not ea or not eb:
        return True  # не знаем → не режем

    overlap = ea & eb
    return len(overlap) >= MIN_ENTITY_OVERLAP


def same_person(a_text: str, b_text: str) -> bool:
    """
    Проверяет, что в обоих текстах не упоминаются разные персоны.
    Если персон нет вообще (или они не найдены надежно) - возвращает True.
    """
    pa = extract_persons(a_text)
    pb = extract_persons(b_text)

    # Если персон нет в обоих текстах - не режем (не знаем)
    if not pa and not pb:
        return True


    # Проверяем, действительно ли это персоны через NER
    # Если извлечённые "персоны" на самом деле не являются персонами по NER - не режем
    try:

        # Получаем реальные персоны через NER
        ner_a = extract_entities_hf(a_text)
        ner_b = extract_entities_hf(b_text)

        # Фильтруем только PER (Person) сущности
        persons_ner_a = {ent[0].lower() for ent in ner_a if ent[1] == "PER"}
        persons_ner_b = {ent[0].lower() for ent in ner_b if ent[1] == "PER"}

        # Если NER не нашёл персон в обоих текстах - считаем что персон нет
        if not persons_ner_a and not persons_ner_b:
            return True


        # Проверяем пересечение реальных персон (через NER)
        # Используем fuzzy matching, так как NER может вернуть разные варианты


        for person_a in persons_ner_a:
            for person_b in persons_ner_b:
                # Если нашли похожие персоны - это одна и та же персона
                if fuzz.token_sort_ratio(person_a, person_b) >= PERSON_FUZZY_THRESHOLD:
                    return True

        # Если персоны найдены, но они разные - режем
        return False

    except Exception:
        # Если NER недоступен, используем старую логику
        # Но проверяем, что извлечённые "персоны" не выглядят как фразы
        # Простая эвристика: персоны обычно содержат только буквы и пробелы,
        # и не содержат предлоги/глаголы в начале
        def looks_like_person(phrase: str) -> bool:
            words = phrase.split()
            if len(words) > MAX_PERSON_WORDS:
                return False
            # Проверяем, что первое слово не глагол/предлог
            first_word = words[0] if words else ""
            if first_word in verbs_prepositions:
                return False
            return True

        pa_filtered = {p for p in pa if looks_like_person(p)}
        pb_filtered = {p for p in pb if looks_like_person(p)}

        # Если после фильтрации персон нет - считаем что персон нет
        if not pa_filtered and not pb_filtered:
            return True

        if not pa_filtered or not pb_filtered:
            return True

        # Проверяем пересечение отфильтрованных персон
        return len(pa_filtered & pb_filtered) > 0


if __name__ == "__main__":
    a_text = "Will Keith Ellison be the Democratic nominee for Senate in Minnesota?"
    b_text = "Will Keith Ellison be the Democratic nominee for Governor in Minnesota?"
    print(same_person(a_text, b_text))
