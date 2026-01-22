"""
Сервис для работы с S3 (MinIO): загрузка, скачивание, presigned URL, состояние задач.
"""
import json
import logging
from datetime import datetime
from typing import Optional, BinaryIO
import boto3
from botocore.exceptions import ClientError, BotoCoreError
from botocore.config import Config

from src.config import config

logger = logging.getLogger(__name__)

# Глобальный клиент S3 (создается при первом использовании)
_s3_client: Optional[boto3.client] = None


def get_s3_client() -> boto3.client:
    """
    Получить или создать клиент boto3 для S3.
    
    Returns:
        boto3 S3 клиент с настройками из конфига
    """
    global _s3_client
    
    if _s3_client is None:
        s3_config = Config(
            signature_version='s3v4',
            s3={
                'addressing_style': 'path' if config.S3_FORCE_PATH_STYLE else 'auto'
            }
        )
        
        _s3_client = boto3.client(
            's3',
            endpoint_url=config.S3_ENDPOINT_URL,
            aws_access_key_id=config.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=config.AWS_SECRET_ACCESS_KEY,
            use_ssl=config.S3_USE_SSL,
            config=s3_config
        )
        
        # Проверка доступности и создание бакета при необходимости
        try:
            _s3_client.head_bucket(Bucket=config.S3_BUCKET)
            logger.info(f"Бакет {config.S3_BUCKET} доступен")
        except ClientError as e:
            error_code = e.response.get('Error', {}).get('Code', '')
            if error_code == '404':
                logger.info(f"Бакет {config.S3_BUCKET} не найден, создаю...")
                try:
                    _s3_client.create_bucket(Bucket=config.S3_BUCKET)
                    logger.info(f"Бакет {config.S3_BUCKET} создан")
                except ClientError as create_error:
                    logger.error(f"Не удалось создать бакет: {create_error}")
                    raise
            else:
                logger.error(f"Ошибка при проверке бакета: {e}")
                raise
    
    return _s3_client


def upload_to_s3(
    bucket: str,
    key: str,
    data: bytes,
    content_type: str = "application/octet-stream"
) -> None:
    """
    Загрузить данные в S3.
    
    Args:
        bucket: Имя бакета
        key: Ключ (путь) объекта
        data: Данные для загрузки (bytes)
        content_type: MIME-тип контента
    """
    client = get_s3_client()
    
    try:
        client.put_object(
            Bucket=bucket,
            Key=key,
            Body=data,
            ContentType=content_type
        )
        logger.info(f"Файл загружен в S3: {bucket}/{key}")
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Ошибка при загрузке в S3 {bucket}/{key}: {e}")
        raise


def download_from_s3(bucket: str, key: str) -> bytes:
    """
    Скачать данные из S3.
    
    Args:
        bucket: Имя бакета
        key: Ключ (путь) объекта
        
    Returns:
        Данные файла (bytes)
    """
    client = get_s3_client()
    
    try:
        response = client.get_object(Bucket=bucket, Key=key)
        data = response['Body'].read()
        logger.info(f"Файл скачан из S3: {bucket}/{key}, размер: {len(data)} байт")
        return data
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == 'NoSuchKey':
            logger.warning(f"Файл не найден в S3: {bucket}/{key}")
        else:
            logger.error(f"Ошибка при скачивании из S3 {bucket}/{key}: {e}")
        raise


def generate_presigned_url(
    bucket: str,
    key: str,
    expires_in: Optional[int] = None
) -> str:
    """
    Сгенерировать presigned URL для доступа к объекту.
    
    Args:
        bucket: Имя бакета
        key: Ключ (путь) объекта
        expires_in: Время жизни URL в секундах (по умолчанию из конфига)
        
    Returns:
        Presigned URL
    """
    client = get_s3_client()
    
    if expires_in is None:
        expires_in = config.S3_PRESIGN_EXPIRES_SECONDS
    
    try:
        url = client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expires_in
        )
        logger.debug(f"Сгенерирован presigned URL для {bucket}/{key}, TTL: {expires_in}с")
        return url
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Ошибка при генерации presigned URL для {bucket}/{key}: {e}")
        raise


def save_task_state(prediction_id: str, state: dict) -> None:
    """
    Сохранить состояние задачи в S3 как JSON.
    
    Args:
        prediction_id: ID предсказания (используется в ключе)
        state: Словарь с состоянием задачи
    """
    key = f"tasks/{prediction_id}.json"
    
    # Кастомный encoder для datetime объектов (на случай, если они все еще есть)
    def json_serializer(obj):
        if isinstance(obj, datetime):
            return obj.isoformat() + "Z"
        raise TypeError(f"Type {type(obj)} not serializable")
    
    json_data = json.dumps(state, ensure_ascii=False, indent=2, default=json_serializer)
    
    upload_to_s3(
        bucket=config.S3_BUCKET,
        key=key,
        data=json_data.encode('utf-8'),
        content_type="application/json; charset=utf-8"
    )


def load_task_state(prediction_id: str) -> Optional[dict]:
    """
    Загрузить состояние задачи из S3.
    
    Args:
        prediction_id: ID предсказания
        
    Returns:
        Словарь с состоянием задачи или None если не найдено
    """
    key = f"tasks/{prediction_id}.json"
    
    try:
        data = download_from_s3(bucket=config.S3_BUCKET, key=key)
        state = json.loads(data.decode('utf-8'))
        logger.info(f"Состояние задачи загружено: {prediction_id}")
        return state
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', '')
        if error_code == 'NoSuchKey':
            logger.warning(f"Состояние задачи не найдено: {prediction_id}")
            return None
        logger.error(f"Ошибка при загрузке состояния задачи {prediction_id}: {e}")
        raise


def delete_object(bucket: str, key: str) -> None:
    """
    Удалить объект из S3.
    
    Args:
        bucket: Имя бакета
        key: Ключ (путь) объекта
    """
    client = get_s3_client()
    
    try:
        client.delete_object(Bucket=bucket, Key=key)
        logger.info(f"Объект удален из S3: {bucket}/{key}")
    except (ClientError, BotoCoreError) as e:
        logger.error(f"Ошибка при удалении объекта {bucket}/{key}: {e}")
        raise
