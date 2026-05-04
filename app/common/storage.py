import uuid
import aioboto3
from botocore.exceptions import BotoCoreError, ClientError

from app.core.config import settings
from app.exceptions.exceptions import ExternalServiceError

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/gif"}
MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


class R2StorageService:
    def __init__(self) -> None:
        self._session = aioboto3.Session()

    def build_storage_key(self, product_id: int, filename: str) -> str:
        safe_name = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]
        return f"products/{product_id}/{uuid.uuid4().hex}_{safe_name}"

    def build_url(self, key: str) -> str:
        return f"{settings.r2.cdn_base_url.rstrip('/')}/{key}"

    async def upload_file(self, key: str, data: bytes, content_type: str) -> None:
        try:
            async with self._session.client(  # type: ignore[attr-defined]
                "s3",
                endpoint_url=settings.r2.endpoint,
                aws_access_key_id=settings.r2.access_key,
                aws_secret_access_key=settings.r2.secret_key,
                region_name="auto",
            ) as s3:
                await s3.put_object(
                    Bucket=settings.r2.bucket,
                    Key=key,
                    Body=data,
                    ContentType=content_type,
                )
        except (BotoCoreError, ClientError) as exc:
            raise ExternalServiceError(f"File upload failed: {exc}") from exc
