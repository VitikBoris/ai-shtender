#!/bin/bash
# Скрипт для инициализации MinIO бакета (Linux/Mac)

echo "Инициализация MinIO бакета..."

# Запустить скрипт Python
python3 scripts/init_minio.py

if [ $? -eq 0 ]; then
    echo "✅ MinIO инициализирован успешно"
    echo "Консоль MinIO: http://localhost:9001 (minioadmin/minioadmin)"
else
    echo "❌ Ошибка при инициализации MinIO"
    exit 1
fi
