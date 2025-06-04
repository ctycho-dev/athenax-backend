from uuid import uuid4
from urllib.parse import quote
import boto3
from botocore.client import Config
from fastapi import UploadFile, HTTPException

from app.domain.submit.audit.schema import StoredFile
from app.core.config import settings
from app.core.logger import get_logger


logger = get_logger()


class CloudflareR2Service:
    def __init__(self):
        self.s3_client = None
        self._access_key = settings.R2_ACCESS_KEY
        self._secret_key = settings.R2_SECRET_KEY
        self.endpoint = settings.R2_ENDPOINT  # e.g. https://<accountid>.r2.cloudflarestorage.com
        # self.public_base_url = settings.R2_PUBLIC_BASE_URL  # e.g. https://cdn.yourdomain.com or https://<bucket>.<accountid>.r2.cloudflarestorage.com

    def connect(self):
        """Initialize the S3 client connection"""
        try:
            self.s3_client = boto3.client(
                's3',
                endpoint_url=self.endpoint,
                aws_access_key_id=self._access_key,
                aws_secret_access_key=self._secret_key,
                config=Config(
                    signature_version='s3v4',
                    s3={'addressing_style': 'virtual'},
                    retries={'max_attempts': 3}
                )
            )
            self.s3_client.list_buckets()
            return True
        except Exception as e:
            logger.error('Failed to connect to Cloudflare R2: %s', e)
            raise ConnectionError(f"Failed to connect to Cloudflare R2: {str(e)}") from e

    def is_connected(self) -> bool:
        return self.s3_client is not None

    def disconnect(self):
        self.s3_client = None

    def make_public_url(self, bucket: str, key: str) -> str:
        """Generate a public R2 URL (if using a custom domain or public bucket setup)"""
        # https://e2ea033a11dc6b7bad6b706b95bd375f.r2.cloudflarestorage.com/articles/cec2bbff-7634-4889-9683-b4f66ece85c2-dummy-2.jpg
        return f'https://e2ea033a11dc6b7bad6b706b95bd375f.r2.cloudflarestorage.com/{bucket}/{quote(key, safe='')}'
        # return f"{self.endpoint}/{quote(key, safe='')}"

    def make_temporary_url(self, bucket: str, key: str, expires_in: int = 604800) -> str:
        """Generate a temporary presigned URL"""
        if not self.is_connected():
            self.connect()
        return self.s3_client.generate_presigned_url(
            'get_object',
            Params={'Bucket': bucket, 'Key': key},
            ExpiresIn=expires_in
        )

    def upload_file(self, file: UploadFile, bucket: str, make_public: bool = True) -> StoredFile:
        """Upload a file to Cloudflare R2"""
        if not self.is_connected():
            self.connect()
        try:
            key = f"{uuid4()}-{file.filename}"
            extra_args = {'ContentType': file.content_type}
            self.s3_client.upload_fileobj(file.file, bucket, key, ExtraArgs=extra_args)

            return StoredFile(
                bucket=bucket,
                key=key,
                original_filename=file.filename or 'default',
                content_type=file.content_type or 'application/octet-stream',
                url=self.make_public_url(bucket, key) if make_public else self.make_temporary_url(bucket, key)
            )
        except Exception as e:
            logger.error("Upload to Cloudflare R2 failed: %s", e)
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    def get_file(self, bucket: str, key: str):
        if not self.is_connected():
            self.connect()
        return self.s3_client.get_object(Bucket=bucket, Key=key)


r2_service = CloudflareR2Service()
