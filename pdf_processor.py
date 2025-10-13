"""
Модуль для обработки PDF документов и создания чанков
"""
import PyPDF2
import pdfplumber
from typing import List, Dict
import re


class PDFProcessor:
    def __init__(self, chunk_size: int = 800, chunk_overlap: int = 200):
        """
        Args:
            chunk_size: размер чанка в символах
            chunk_overlap: перекрытие между чанками для сохранения контекста
        """
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap

    def extract_text_from_pdf(self, pdf_path: str) -> List[Dict[str, any]]:
        """
        Извлекает текст из PDF с сохранением информации о страницах

        Returns:
            List[Dict]: список словарей с текстом и номером страницы
        """
        pages_data = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_num, page in enumerate(pdf.pages, start=1):
                    text = page.extract_text()
                    if text and text.strip():
                        # Очистка текста от лишних пробелов и переносов
                        text = self._clean_text(text)
                        pages_data.append({
                            'text': text,
                            'page': page_num,
                            'document': pdf_path.split('/')[-1]
                        })
        except Exception as e:
            print(f"Ошибка при обработке {pdf_path}: {e}")
            # Fallback на PyPDF2
            pages_data = self._extract_with_pypdf2(pdf_path)

        return pages_data

    def _extract_with_pypdf2(self, pdf_path: str) -> List[Dict[str, any]]:
        """Альтернативный метод извлечения текста через PyPDF2"""
        pages_data = []

        try:
            with open(pdf_path, 'rb') as file:
                pdf_reader = PyPDF2.PdfReader(file)
                for page_num, page in enumerate(pdf_reader.pages, start=1):
                    text = page.extract_text()
                    if text and text.strip():
                        text = self._clean_text(text)
                        pages_data.append({
                            'text': text,
                            'page': page_num,
                            'document': pdf_path.split('/')[-1]
                        })
        except Exception as e:
            print(f"Ошибка PyPDF2 при обработке {pdf_path}: {e}")

        return pages_data

    def _clean_text(self, text: str) -> str:
        """Очистка текста от лишних символов"""
        # Удаляем множественные пробелы
        text = re.sub(r'\s+', ' ', text)
        # Удаляем пробелы в начале и конце
        text = text.strip()
        return text

    def create_chunks(self, pages_data: List[Dict[str, any]], global_chunk_id: int = 0) -> List[Dict[str, any]]:
        """
        Разбивает текст на чанки с перекрытием

        Args:
            pages_data: данные страниц
            global_chunk_id: начальный ID для чанков (для уникальности между документами)

        Returns:
            List[Dict]: список чанков с метаданными
        """
        chunks = []
        chunk_id = global_chunk_id

        for page_data in pages_data:
            text = page_data['text']
            page_num = page_data['page']
            document_name = page_data['document']

            # Разбиваем текст на предложения для более осмысленных чанков
            sentences = self._split_into_sentences(text)

            current_chunk = ""
            current_length = 0

            for sentence in sentences:
                sentence_length = len(sentence)

                # Если добавление предложения превысит размер чанка
                if current_length + sentence_length > self.chunk_size and current_chunk:
                    # Сохраняем текущий чанк
                    chunks.append({
                        'id': f'chunk_{chunk_id}',
                        'text': current_chunk.strip(),
                        'page': page_num,
                        'document': document_name,
                        'metadata': f"{document_name}, стр. {page_num}"
                    })
                    chunk_id += 1

                    # Начинаем новый чанк с перекрытием
                    # Берем последние N символов для контекста
                    overlap_text = current_chunk[-self.chunk_overlap:] if len(current_chunk) > self.chunk_overlap else current_chunk
                    current_chunk = overlap_text + " " + sentence
                    current_length = len(current_chunk)
                else:
                    current_chunk += " " + sentence
                    current_length += sentence_length + 1

            # Сохраняем последний чанк страницы
            if current_chunk.strip():
                chunks.append({
                    'id': f'chunk_{chunk_id}',
                    'text': current_chunk.strip(),
                    'page': page_num,
                    'document': document_name,
                    'metadata': f"{document_name}, стр. {page_num}"
                })
                chunk_id += 1

        return chunks

    def _split_into_sentences(self, text: str) -> List[str]:
        """Разбивает текст на предложения"""
        # Простое разбиение по точке, вопросительному и восклицательному знакам
        sentences = re.split(r'(?<=[.!?])\s+', text)
        return [s for s in sentences if s.strip()]

    def _extract_tables(self, pages_data: List[Dict[str, any]], start_id: int = 0) -> List[Dict[str, any]]:
        """
        Извлекает табличные данные из страниц по паттернам

        Args:
            pages_data: данные страниц с текстом
            start_id: начальный ID для чанков (для уникальности)

        Returns:
            List[Dict]: список чанков с табличными данными
        """
        table_chunks = []
        chunk_id = start_id

        # Паттерны для определения табличных страниц
        # Страницы с кодами веществ (E-коды)
        table_patterns = [
            r'Е\d{3,4}',  # E-коды (E951, E420 и т.д.)
            r'\d+\s*мг/доза',  # Дозировки
            r'\d+\s*г/доза',  # Дозировки в граммах
        ]

        for page_data in pages_data:
            text = page_data['text']
            page_num = page_data['page']
            document_name = page_data['document']

            # Проверяем есть ли табличные паттерны
            has_table_data = any(re.search(pattern, text) for pattern in table_patterns)

            if not has_table_data:
                continue

            # Ищем строки с табличными данными (содержат E-коды)
            lines = text.split('\n')
            table_lines = []

            for line in lines:
                # Проверяем наличие E-кода или дозировки
                if re.search(r'Е\d{3,4}|E\d{3,4}|\d+\s*(мг|г)/доза', line):
                    table_lines.append(line.strip())

            if not table_lines:
                continue

            # Форматируем табличные данные
            formatted_text = f"[ТАБЛИЦА со страницы {page_num} - Вспомогательные вещества]\n\n"
            formatted_text += "\n".join(table_lines)

            # Создаем чанк
            table_chunks.append({
                'id': f'table_{chunk_id}',
                'text': formatted_text,
                'page': page_num,
                'document': document_name,
                'metadata': f"{document_name}, стр. {page_num}, таблица вспомогательных веществ",
                'chunk_type': 'table'
            })
            chunk_id += 1

            print(f"  → Извлечена таблица на стр. {page_num} ({len(table_lines)} строк)")

        if table_chunks:
            print(f"  ✓ Извлечено {len(table_chunks)} табличных чанков")

        return table_chunks

    def _format_table_for_ai(self, table: List[List[str]], page_num: int) -> str:
        """
        Форматирует таблицу в текст, удобный для AI

        Args:
            table: двумерный массив строк таблицы
            page_num: номер страницы

        Returns:
            str: отформатированный текст таблицы
        """
        if not table or len(table) < 2:
            return ""

        # Убираем пустые строки и очищаем данные
        cleaned_table = []
        for row in table:
            if not row or all(not cell or not str(cell).strip() for cell in row):
                continue
            cleaned_row = [str(cell).strip() if cell else "" for cell in row]
            cleaned_table.append(cleaned_row)

        if len(cleaned_table) < 2:
            return ""

        # Первая строка - заголовки (если есть)
        headers = cleaned_table[0]
        data_rows = cleaned_table[1:]

        # Форматируем: каждая строка = отдельная запись с указанием полей
        formatted_lines = [f"[ТАБЛИЦА со страницы {page_num}]\n"]

        for row in data_rows:
            # Создаем читаемую запись
            row_parts = []
            for i, cell in enumerate(row):
                if not cell:
                    continue
                # Если есть заголовок, используем его
                if i < len(headers) and headers[i]:
                    row_parts.append(f"{headers[i]}: {cell}")
                else:
                    row_parts.append(cell)

            if row_parts:
                formatted_lines.append(" | ".join(row_parts))

        return "\n".join(formatted_lines)

    def _extract_glossary_definitions(self, pages_data: List[Dict[str, any]], start_id: int = 0) -> List[Dict[str, any]]:
        """
        Извлекает определения из раздела 'Определения'

        ПРИМЕЧАНИЕ: Из-за водяных знаков КонсультантПлюс в PDF, которые разрывают текст определений,
        полное извлечение глоссария невозможно. Полагаемся на обычные чанки с увеличенным overlap.

        Args:
            pages_data: данные страниц PDF
            start_id: начальный ID для чанков (для уникальности)

        Returns:
            List[Dict]: список чанков с определениями (может быть пустым из-за проблем с PDF)
        """
        # Отключаем глоссарий парсер - он не работает корректно с водяными знаками
        # Определения будут найдены через обычный векторный поиск с увеличенным overlap
        return []

    def process_pdf(self, pdf_path: str) -> List[Dict[str, any]]:
        """
        Полный цикл обработки PDF: извлечение текста → создание чанков

        Returns:
            List[Dict]: готовые чанки для индексации (обычные + глоссарий)
        """
        print(f"Обработка {pdf_path}...")
        pages_data = self.extract_text_from_pdf(pdf_path)

        if not pages_data:
            print(f"Не удалось извлечь текст из {pdf_path}")
            return []

        print(f"Извлечено {len(pages_data)} страниц")

        # Извлекаем определения из глоссария
        glossary_chunks = self._extract_glossary_definitions(pages_data)

        # Создаем обычные чанки
        chunks = self.create_chunks(pages_data)
        print(f"Создано {len(chunks)} обычных чанков")

        # Объединяем: сначала глоссарий, потом обычные чанки
        all_chunks = glossary_chunks + chunks

        return all_chunks
