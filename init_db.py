#!/usr/bin/env python3
"""
Скрипт для инициализации базы данных
Обрабатывает PDF файлы из папки documents/ и индексирует их в ChromaDB
"""
import os
import sys
import glob
from pdf_processor import PDFProcessor
from vector_db import VectorDatabase


def main():
    print("=" * 60)
    print("Инициализация базы данных документов")
    print("=" * 60)

    # Папка с PDF документами
    documents_folder = "./documents"

    # Проверяем существование папки
    if not os.path.exists(documents_folder):
        print(f"\n⚠️  Папка {documents_folder} не найдена!")
        print(f"Создаю папку...")
        os.makedirs(documents_folder)
        print(f"\n✓ Папка создана: {documents_folder}")
        print(f"Поместите PDF файлы в эту папку и запустите скрипт снова")
        return

    # Ищем PDF файлы
    pdf_files = glob.glob(os.path.join(documents_folder, "*.pdf"))

    if not pdf_files:
        print(f"\n⚠️  PDF файлы не найдены в папке {documents_folder}")
        print(f"Поместите PDF файлы в эту папку и запустите скрипт снова")
        return

    print(f"\nНайдено PDF файлов: {len(pdf_files)}")
    for pdf_file in pdf_files:
        print(f"  - {os.path.basename(pdf_file)}")

    # Проверяем флаг --yes
    auto_confirm = '--yes' in sys.argv or '-y' in sys.argv

    if not auto_confirm:
        # Спрашиваем подтверждение
        print("\n" + "=" * 60)
        response = input("Начать индексацию? (y/n): ").strip().lower()

        if response != 'y':
            print("Отменено")
            return
    else:
        print("\n" + "=" * 60)
        print("Автоматическое подтверждение (флаг --yes)")
        print("=" * 60)

    print("\n" + "=" * 60)
    print("ЭТАП 1: Обработка PDF файлов")
    print("=" * 60)

    # Инициализируем процессор PDF
    # Максимальный overlap (800) = 100% размера чанка, чтобы гарантированно захватить длинные определения
    # разбитые водяными знаками между страницами
    processor = PDFProcessor(chunk_size=800, chunk_overlap=800)

    # Обрабатываем все PDF
    all_chunks = []
    global_chunk_counter = 0  # Глобальный счетчик для уникальных ID

    for pdf_file in pdf_files:
        print(f"\n📄 {os.path.basename(pdf_file)}")

        # Извлекаем текст
        pages_data = processor.extract_text_from_pdf(pdf_file)
        if not pages_data:
            print(f"⚠️  Не удалось извлечь текст из файла")
            continue

        print(f"Извлечено {len(pages_data)} страниц")

        # Извлекаем таблицы из текста (с глобальным ID)
        table_chunks = processor._extract_tables(pages_data, global_chunk_counter)
        global_chunk_counter += len(table_chunks)

        # Извлекаем определения из глоссария (с глобальным ID)
        glossary_chunks = processor._extract_glossary_definitions(pages_data, global_chunk_counter)
        global_chunk_counter += len(glossary_chunks)

        # Создаем обычные чанки с глобальным счетчиком
        chunks = processor.create_chunks(pages_data, global_chunk_counter)
        global_chunk_counter += len(chunks)

        # Объединяем: таблицы + глоссарий + обычные чанки
        # Таблицы первыми - самые структурированные данные
        document_chunks = table_chunks + glossary_chunks + chunks

        if document_chunks:
            all_chunks.extend(document_chunks)
            print(f"Создано {len(chunks)} обычных чанков + {len(glossary_chunks)} глоссарных + {len(table_chunks)} табличных")
            print(f"✓ Готово: {len(document_chunks)} чанков")
        else:
            print(f"⚠️  Не удалось создать чанки")

    if not all_chunks:
        print("\n❌ Не удалось извлечь текст из PDF файлов")
        return

    print(f"\n✓ Всего обработано чанков: {len(all_chunks)}")

    print("\n" + "=" * 60)
    print("ЭТАП 2: Создание эмбеддингов и индексация")
    print("=" * 60)

    # Инициализируем векторную БД
    vector_db = VectorDatabase()

    # Очищаем старую коллекцию если есть
    if vector_db.get_collection_count() > 0:
        print(f"\n⚠️  В базе данных уже есть {vector_db.get_collection_count()} документов")

        if auto_confirm:
            vector_db.clear_collection()
            print("✓ База данных очищена (автоматически)")
        else:
            response = input("Очистить базу данных и начать заново? (y/n): ").strip().lower()

            if response == 'y':
                vector_db.clear_collection()
                print("✓ База данных очищена")
            else:
                print("Отменено")
                return

    # Добавляем документы в базу
    print("\nСоздание эмбеддингов (это может занять несколько минут)...")
    vector_db.add_documents(all_chunks)

    print("\n" + "=" * 60)
    print("✓ ГОТОВО!")
    print("=" * 60)
    print(f"Индексировано документов: {len(pdf_files)}")
    print(f"Всего чанков в базе: {vector_db.get_collection_count()}")
    print(f"\nТеперь можно запустить сервер:")
    print(f"  python main.py")
    print("=" * 60)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nПрервано пользователем")
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        import traceback
        traceback.print_exc()
