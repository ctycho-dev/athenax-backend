from uuid import uuid4
from urllib.parse import quote
import boto3
from botocore.client import Config
from fastapi import UploadFile, HTTPException

from app.domain.submit.audit.schema import StoredFile
from app.core.config import settings
from app.core.logger import get_logger


logger = get_logger()


class StorjService:
    def __init__(self):
        self.s3_client = None
        self._access_key = settings.STORJ_ACCESS_KEY
        self._secret_key = settings.STORJ_SECRET_KEY
        self.endpoint = settings.STORJ_ENDPOINT
        
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
            logger.error('Failed to connect to Storj: %s', e)
            raise ConnectionError(f"Failed to connect to Storj: {str(e)}") from e

    def disconnect(self):
        """Clean up the S3 client"""
        if self.s3_client:
            self.s3_client = None

    def is_connected(self) -> bool:
        """Check if the client is connected"""
        return self.s3_client is not None

    def make_permanent_url(self, bucket: str, key: str) -> str:
        """Generate a permanent public URL"""
        return f"https://link.storjshare.io/raw/{self._access_key}/{bucket}/{quote(key, safe='')}"

    def make_temporary_url(self, bucket: str, key: str, expires_in: int = 604800) -> str:
        """Generate a temporary presigned URL"""
        if not self.is_connected():
            self.connect()
        if not self.is_connected():
            raise ConnectionError("Not connected to Storj")
        
        return self.s3_client.generate_presigned_url(
            'get_object',
            Params={
                'Bucket': bucket,
                'Key': key
            },
            ExpiresIn=expires_in
        )

    def upload_file(
        self,
        file: UploadFile,
        bucket: str,
        make_public: bool = True
    ) -> StoredFile:
        """Upload a file to Storj"""
        if not self.is_connected():
            self.connect()
        if not self.is_connected():
            raise ConnectionError("Not connected to Storj")
        try:
            key = f'{uuid4()}:{file.filename}'
            # Upload file
            self.s3_client.upload_fileobj(
                file.file,
                bucket,
                key,
                ExtraArgs={
                    'ContentType': file.content_type,
                    # This is the key difference for Storj:
                    'ACL': 'public-read' if make_public else 'private'
                }
            )

            return StoredFile(
                bucket=bucket,
                key=key,
                original_filename=file.filename if file.filename else 'default',
                content_type=file.content_type if file.content_type else 'application/txt',
                url=self.make_permanent_url(bucket, key)
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")

    def get_storj_file(self, bucket: str, key: str):
        """Common method to get file from Storj"""
        if not self.is_connected():
            self.connect()
        if not self.is_connected():
            raise ConnectionError("Not connected to Storj")
        return self.s3_client.get_object(Bucket=bucket, Key=key)


storj_service = StorjService()
