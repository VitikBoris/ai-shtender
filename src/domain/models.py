"""
Domain модели: TaskState, статусы, режимы бота.
"""
from enum import Enum
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class TaskStatus(str, Enum):
    """Статусы задачи обработки."""
    QUEUED = "queued"
    PROCESSING = "processing"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELED = "canceled"


class BotMode(str, Enum):
    """Режимы работы бота."""
    PROCESS_PHOTO = "process_photo"
    FRAME = "frame"


class TaskState(BaseModel):
    """Состояние задачи обработки изображения (хранится в S3)."""
    
    prediction_id: str = Field(..., description="ID предсказания от Replicate")
    chat_id: int = Field(..., description="ID чата в Telegram")
    user_id: int = Field(..., description="ID пользователя в Telegram")
    mode: BotMode = Field(default=BotMode.PROCESS_PHOTO, description="Режим обработки")
    input_s3_key: str = Field(..., description="Ключ входного изображения в S3")
    status: TaskStatus = Field(default=TaskStatus.QUEUED, description="Текущий статус")
    created_at: datetime = Field(default_factory=datetime.utcnow, description="Время создания")
    updated_at: datetime = Field(default_factory=datetime.utcnow, description="Время последнего обновления")
    
    # Опциональные поля для расширенной информации
    telegram: Optional[dict] = Field(None, description="Информация о Telegram сообщении")
    input: Optional[dict] = Field(None, description="Детали входного файла")
    replicate: Optional[dict] = Field(None, description="Информация о Replicate запросе")
    result: Optional[dict] = Field(None, description="Результат обработки")
    error: Optional[dict] = Field(None, description="Информация об ошибке")
    
    class Config:
        """Конфигурация Pydantic модели."""
        use_enum_values = True
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z"
        }
    
    def update_status(self, new_status: TaskStatus):
        """Обновить статус задачи."""
        self.status = new_status
        self.updated_at = datetime.utcnow()
    
    def to_dict(self) -> dict:
        """Преобразовать в словарь для сохранения в JSON."""
        # Совместимость с Pydantic v1 и v2
        if hasattr(self, 'model_dump'):
            data = self.model_dump(exclude_none=True, mode='json')
        else:
            data = self.dict(exclude_none=True)
        
        # Конвертировать datetime в строки для JSON сериализации
        if "created_at" in data and isinstance(data["created_at"], datetime):
            data["created_at"] = data["created_at"].isoformat() + "Z"
        if "updated_at" in data and isinstance(data["updated_at"], datetime):
            data["updated_at"] = data["updated_at"].isoformat() + "Z"
        
        return data
    
    @classmethod
    def from_dict(cls, data: dict) -> "TaskState":
        """Создать из словаря (при загрузке из S3)."""
        # Преобразование строк в datetime
        if "created_at" in data and isinstance(data["created_at"], str):
            data["created_at"] = datetime.fromisoformat(data["created_at"].replace("Z", "+00:00"))
        if "updated_at" in data and isinstance(data["updated_at"], str):
            data["updated_at"] = datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00"))
        return cls(**data)
