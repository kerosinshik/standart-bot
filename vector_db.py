"""
Модуль для работы с ChromaDB и векторными эмбеддингами
"""
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from typing import List, Dict
import os


class VectorDatabase:
    def __init__(self, db_path: str = "./data/chroma_db", collection_name: str = "documents"):
        """
        Инициализация ChromaDB и модели эмбеддингов

        Args:
            db_path: путь к папке с базой данных
            collection_name: название коллекции
        """
        self.db_path = db_path
        self.collection_name = collection_name

        # Создаем директорию если не существует
        os.makedirs(db_path, exist_ok=True)

        # Инициализируем ChromaDB
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(anonymized_telemetry=False)
        )

        # Используем специализированную модель для русского языка
        # Оптимизирована для семантического поиска по русским текстам
        print("Загрузка модели эмбеддингов для русского языка...")
        # Принудительно используем CPU чтобы избежать OOM на MPS
        import torch
        device = 'cpu'  # Всегда используем CPU для больших объемов
        self.embedding_model = SentenceTransformer('cointegrated/rubert-tiny2', device=device)
        print(f"Модель загружена на {device}!")

        # Получаем или создаем коллекцию
        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        """Получает существующую коллекцию или создает новую"""
        try:
            # Пытаемся получить существующую
            collection = self.client.get_collection(name=self.collection_name)
            print(f"Загружена существующая коллекция '{self.collection_name}'")
        except:
            # Создаем новую
            collection = self.client.create_collection(
                name=self.collection_name,
                metadata={"description": "Нормативные документы"}
            )
            print(f"Создана новая коллекция '{self.collection_name}'")

        return collection

    def create_embeddings(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Создает эмбеддинги для списка текстов с batch processing

        Args:
            texts: список текстов
            batch_size: размер батча для модели (по умолчанию 32)

        Returns:
            List[List[float]]: список векторов эмбеддингов
        """
        # Если текстов мало, обрабатываем сразу
        if len(texts) <= batch_size:
            embeddings = self.embedding_model.encode(texts, show_progress_bar=True, batch_size=batch_size)
            return embeddings.tolist()

        # Для больших объемов - батчами
        all_embeddings = []
        for i in range(0, len(texts), batch_size):
            batch_texts = texts[i:i + batch_size]
            batch_embeddings = self.embedding_model.encode(batch_texts, show_progress_bar=False, batch_size=batch_size)
            all_embeddings.extend(batch_embeddings.tolist())

        return all_embeddings

    def add_documents(self, chunks: List[Dict[str, any]], batch_size: int = 200):
        """
        Добавляет документы в ChromaDB с batch processing для больших объемов

        Args:
            chunks: список чанков с текстом и метаданными
            batch_size: размер батча для обработки (по умолчанию 200)
        """
        if not chunks:
            print("Нет чанков для добавления")
            return

        total_chunks = len(chunks)
        print(f"Создание эмбеддингов для {total_chunks} чанков (батчами по {batch_size})...")

        # Обрабатываем чанки батчами
        for i in range(0, total_chunks, batch_size):
            batch = chunks[i:i + batch_size]
            batch_num = (i // batch_size) + 1
            total_batches = (total_chunks + batch_size - 1) // batch_size

            print(f"Обработка батча {batch_num}/{total_batches} ({len(batch)} чанков)...")

            # Извлекаем тексты и метаданные для текущего батча
            texts = [chunk['text'] for chunk in batch]
            ids = [chunk['id'] for chunk in batch]
            metadatas = [
                {
                    'document': chunk['document'],
                    'page': chunk['page'],
                    'metadata': chunk['metadata'],
                    'chunk_type': chunk.get('chunk_type', 'regular'),  # table, glossary или regular
                    'term': chunk.get('term', ''),  # для глоссарных чанков
                    'table_index': chunk.get('table_index', -1)  # для табличных чанков
                }
                for chunk in batch
            ]

            # Создаем эмбеддинги для батча
            embeddings = self.create_embeddings(texts)

            # Добавляем батч в ChromaDB
            self.collection.add(
                embeddings=embeddings,
                documents=texts,
                ids=ids,
                metadatas=metadatas
            )

        print(f"✓ Добавлено {total_chunks} чанков в базу данных")

    def get_all_documents(self) -> List[str]:
        """
        Возвращает список всех уникальных документов в базе

        Returns:
            List[str]: список названий документов
        """
        result = self.collection.get()
        if not result or not result['metadatas']:
            return []

        documents = set()
        for metadata in result['metadatas']:
            if 'document' in metadata:
                documents.add(metadata['document'])

        return sorted(list(documents))

    def search(self, query: str, n_results: int = 5) -> Dict:
        """
        Ищет релевантные чанки по запросу

        Args:
            query: поисковый запрос
            n_results: количество результатов

        Returns:
            Dict: результаты поиска с текстами и метаданными
        """
        # Создаем эмбеддинг для запроса
        query_embedding = self.embedding_model.encode([query])[0].tolist()

        # Ищем в ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results
        )

        return results

    def get_context_for_query(self, query: str, n_results: int = 5) -> tuple[str, List[str]]:
        """
        Получает контекст для запроса и список источников

        Args:
            query: вопрос пользователя
            n_results: количество чанков для контекста

        Returns:
            tuple: (контекст для AI, список источников)
        """
        # Увеличиваем количество результатов для keyword boost и приоритизации таблиц
        # Берем больше кандидатов чтобы найти релевантные табличные чанки
        search_results = self.search(query, n_results * 4)

        # Извлекаем ключевые слова из вопроса
        keywords = self._extract_keywords(query)

        # Перераспределяем результаты с учетом keyword matching
        results = self._rerank_with_keywords(search_results, keywords, n_results)

        if not results['documents'] or not results['documents'][0]:
            return "", []

        # Формируем контекст из найденных чанков
        context_parts = []
        sources = []
        seen_sources = set()  # Для отслеживания уникальных источников

        # Извлекаем ключевые термины из вопроса для поиска определений
        definition_keywords = self._extract_definition_keywords(query)

        # Если вопрос про определение (что такое, определение), ищем в глоссарии
        if definition_keywords:
            glossary_chunk = self._find_glossary_definition(definition_keywords)
            if glossary_chunk:
                # Добавляем определение первым
                context_parts.append(f"[ОПРЕДЕЛЕНИЕ из глоссария: {glossary_chunk['metadata']}]\n{glossary_chunk['text']}\n")
                if glossary_chunk['metadata'] not in seen_sources:
                    sources.append(glossary_chunk['metadata'])
                    seen_sources.add(glossary_chunk['metadata'])

        for i, (doc, metadata) in enumerate(zip(results['documents'][0], results['metadatas'][0])):
            source_info = metadata['metadata']
            context_parts.append(f"[Источник {i+1}: {source_info}]\n{doc}\n")

            # Добавляем источник только если его еще нет
            if source_info not in seen_sources:
                sources.append(source_info)
                seen_sources.add(source_info)

        context = "\n".join(context_parts)

        return context, sources

    def _extract_keywords(self, query: str) -> List[str]:
        """Извлекает ключевые слова из вопроса для boost'а"""
        import re
        query_lower = query.lower()

        # Убираем стоп-слова
        stop_words = {'какой', 'какая', 'какое', 'какие', 'что', 'где', 'когда', 'как', 'почему',
                      'есть', 'это', 'или', 'для', 'при', 'код', 'номер', 'название'}

        # Разбиваем на слова
        words = re.findall(r'\b[а-яёa-z]{3,}\b', query_lower)

        # Фильтруем стоп-слова
        keywords = [w for w in words if w not in stop_words]

        return keywords

    def _rerank_with_keywords(self, search_results: Dict, keywords: List[str], n_results: int) -> Dict:
        """Переранжирует результаты с учетом keyword matching"""
        if not search_results['documents'] or not search_results['documents'][0]:
            return search_results

        # Создаем список результатов с весами
        scored_results = []

        for i, (doc_id, doc, metadata, distance) in enumerate(zip(
            search_results['ids'][0],
            search_results['documents'][0],
            search_results['metadatas'][0],
            search_results['distances'][0]
        )):
            doc_lower = doc.lower()

            # Считаем сколько ключевых слов найдено
            # Используем нечеткое сравнение: если корень слова (первые 4-5 букв) совпадает
            keyword_matches = 0
            for kw in keywords:
                # Берем корень слова (минимум 4 буквы)
                stem_length = min(len(kw), max(4, int(len(kw) * 0.7)))
                kw_stem = kw[:stem_length]

                # Проверяем есть ли слово с таким корнем в документе
                if kw_stem in doc_lower:
                    keyword_matches += 1

            # Boost: если есть keyword match, уменьшаем distance (улучшаем рейтинг)
            # Сильный boost для keyword matching (важно для табличных данных)
            boost_per_keyword = 0.5

            # Двойной boost для табличных чанков (они содержат критически важные данные)
            if metadata.get('chunk_type') == 'table':
                boost_per_keyword = 1.0

            boost = keyword_matches * boost_per_keyword
            adjusted_distance = distance - boost

            scored_results.append({
                'id': doc_id,
                'document': doc,
                'metadata': metadata,
                'distance': adjusted_distance,
                'original_distance': distance,
                'keyword_matches': keyword_matches
            })

        # Жёсткий приоритет: глоссарий и таблицы с keyword match идут ВСЕГДА первыми
        # Это первоисточники точных данных
        high_priority = []  # Глоссарий и таблицы с keyword match
        regular_results = []  # Всё остальное

        for result in scored_results:
            chunk_type = result['metadata'].get('chunk_type', 'regular')

            # Глоссарий или таблица с keyword match - максимальный приоритет
            if result['keyword_matches'] > 0 and chunk_type in ['glossary', 'table']:
                high_priority.append(result)
            else:
                regular_results.append(result)

        # Сортируем каждую группу по distance
        high_priority.sort(key=lambda x: x['distance'])
        regular_results.sort(key=lambda x: x['distance'])

        # Объединяем: СНАЧАЛА глоссарий/таблицы, ПОТОМ остальное
        sorted_results = high_priority + regular_results

        # Берем топ n_results
        top_results = sorted_results[:n_results]

        # Формируем результат в формате ChromaDB
        return {
            'ids': [[r['id'] for r in top_results]],
            'documents': [[r['document'] for r in top_results]],
            'metadatas': [[r['metadata'] for r in top_results]],
            'distances': [[r['distance'] for r in top_results]]
        }

    def _extract_definition_keywords(self, query: str) -> str:
        """Извлекает ключевое слово если вопрос про определение"""
        query_lower = query.lower()

        # Проверяем паттерны вопросов про определения
        if any(pattern in query_lower for pattern in ['что такое', 'определение', 'что означает', 'что значит']):
            # Извлекаем термин после паттерна
            for pattern in ['что такое ', 'определение ', 'что означает ', 'что значит ']:
                if pattern in query_lower:
                    term = query_lower.split(pattern)[-1].strip('? ').split()[0:3]  # Берем 1-3 слова
                    return ' '.join(term)
        return ""

    def _find_glossary_definition(self, keyword: str) -> dict:
        """Ищет определение термина среди глоссарных чанков"""
        # Получаем все документы
        all_docs = self.collection.get()

        # Ищем среди глоссарных чанков
        for doc_id, doc, metadata in zip(all_docs['ids'], all_docs['documents'], all_docs['metadatas']):
            # Проверяем что это глоссарный чанк
            if metadata.get('chunk_type') == 'glossary':
                # Проверяем что ключевое слово есть в термине
                term = metadata.get('term', '')
                if keyword in term or term in keyword:
                    return {
                        'text': doc,
                        'metadata': metadata['metadata']
                    }

        return None

    def direct_search(self, query: str, n_results: int = 5) -> tuple[str, List[str]]:
        """
        Прямой поиск по ключевым словам без векторного поиска

        Args:
            query: поисковый запрос
            n_results: максимальное количество результатов

        Returns:
            tuple: (контекст для AI, список источников)
        """
        # Извлекаем ключевые слова
        keywords = self._extract_keywords(query)

        if not keywords:
            return "", []

        # Получаем все чанки
        all_docs = self.collection.get()

        # Ищем чанки с keyword match
        matches = []

        for doc_id, doc, metadata in zip(all_docs['ids'], all_docs['documents'], all_docs['metadatas']):
            doc_lower = doc.lower()

            # Считаем совпадения ключевых слов
            match_count = 0
            for kw in keywords:
                stem_length = min(len(kw), max(4, int(len(kw) * 0.7)))
                kw_stem = kw[:stem_length]

                if kw_stem in doc_lower:
                    match_count += 1

            if match_count > 0:
                chunk_type = metadata.get('chunk_type', 'regular')

                # Приоритет: глоссарий/таблицы важнее
                priority = 0
                if chunk_type == 'glossary':
                    priority = 1000
                elif chunk_type == 'table':
                    priority = 900

                score = match_count * 100 + priority

                matches.append({
                    'id': doc_id,
                    'text': doc,
                    'metadata': metadata,
                    'score': score,
                    'match_count': match_count
                })

        # Сортируем по score (больше = лучше)
        matches.sort(key=lambda x: x['score'], reverse=True)

        # Берём топ n_results
        top_matches = matches[:n_results]

        if not top_matches:
            return "", []

        # Формируем контекст
        context_parts = []
        sources = []
        seen_sources = set()

        for i, match in enumerate(top_matches, 1):
            source_info = match['metadata']['metadata']
            context_parts.append(f"[Источник {i}: {source_info}]\n{match['text']}\n")

            if source_info not in seen_sources:
                sources.append(source_info)
                seen_sources.add(source_info)

        context = "\n".join(context_parts)

        return context, sources

    def clear_collection(self):
        """Очищает коллекцию (полезно для переиндексации)"""
        self.client.delete_collection(name=self.collection_name)
        self.collection = self._get_or_create_collection()
        print("Коллекция очищена")

    def get_collection_count(self) -> int:
        """Возвращает количество чанков в коллекции"""
        return self.collection.count()

    def get_unique_documents_count(self) -> int:
        """Возвращает количество уникальных документов"""
        try:
            # Получаем все метаданные
            results = self.collection.get()
            if not results or not results.get('metadatas'):
                return 0

            # Собираем уникальные имена документов
            unique_docs = set()
            for metadata in results['metadatas']:
                if 'document' in metadata:
                    unique_docs.add(metadata['document'])

            return len(unique_docs)
        except:
            return 0
