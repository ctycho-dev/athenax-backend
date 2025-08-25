import os
from datetime import datetime
from typing import Optional
from beanie import Document, Indexed
from pydantic import Field, EmailStr, field_validator
from argon2 import PasswordHasher, exceptions
from app.enums.enums import UserRole
from app.domain.user.schema import (
    LinkedAccount,
    Wallet
)


# Initialize Argon2 with production-grade parameters
ph = PasswordHasher(
    time_cost=3,        # 3 iterations (adjust based on your server's capacity)
    memory_cost=65536,  # 64MB memory usage
    parallelism=4,      # 4 parallel threads
    hash_len=32,        # 32-byte hash output
    salt_len=16         # 16-byte salt
)


class User(Document):
    """Enhanced user model supporting both Privy and email/password auth"""
    
    # Privy identity (and optional email if you collect it)
    privy_id: Indexed(str, unique=True) | None = None
    email: Indexed(EmailStr, unique=True) | None = None
    
    # Usage / telemetry
    last_login_at: datetime | None = None
    login_count: int = 0

    # Existing
    linked_accounts: list[LinkedAccount] = []
    wallets: list[Wallet] = []
    metadata: dict = Field(default_factory=dict)
    
    # System roles (authorization)
    role: UserRole = UserRole.USER

    # Product flags
    has_accepted_terms: bool = False
    is_guest: bool = False

    # Onboarded
    account_type: str | None = None
    has_profile: bool = False

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "user"
        indexes = [
            "privy_id",
            "email",
            "linked_accounts.subject",
            "linked_accounts.address",
            "linked_accounts.email",
        ]

    # # Public profile
    # name: str | None = Field(None, description="Full name for profile display")
    # username: Indexed(str, unique=True) | None = None
    # location: str | None = None
    # bio: str | None = None
    # profile_image: str | None = None

    # # Soacial accounts
    # github: str | None = None
    # twitter: str | None = None
    # linkedin: str | None = None
    # instagram: str | None = None
    # discord: str | None = None