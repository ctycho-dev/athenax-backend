from uuid import uuid4
import boto3
from botocore.client import Config
from fastapi import UploadFile, HTTPException

from app.core.config import settings


class UserService:
    def __init__(self):


user_service = UserService()
