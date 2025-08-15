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
    
    # Authentication fields
    privy_id: Indexed(str, unique=True) | None = None
    email: Indexed(EmailStr, unique=True) | None = None
    hashed_password: str | None = Field(
        None,
        pattern=r"^\$argon2id\$v=\d+\$m=\d+,t=\d+,p=\d+\$.{64}$"  # Enforce Argon2 format
    )
    
    # Security fields
    password_reset_token: str | None = None
    password_reset_expires: datetime | None = None
    email_verified: bool = False
    verification_token: str | None = None
    last_login_at: datetime | None = None
    login_count: int = 0

    # Public profile
    name: str | None = Field(None, description="Full name for profile display")
    username: Indexed(str, unique=True) | None = None
    location: str | None = None
    bio: str | None = None
    profile_image: str | None = None

    # Soacial accounts
    github: str | None = None
    twitter: str | None = None
    linkedin: str | None = None
    instagram: str | None = None
    discord: str | None = None
    
    # Existing fields
    linked_accounts: list[LinkedAccount] = []
    wallets: list[Wallet] = []
    metadata: dict = Field(default_factory=dict)
    role: UserRole = UserRole.USER
    has_accepted_terms: bool = False
    is_guest: bool = False

    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the record was created"
    )
    updated_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the record was last updated"
    )

    class Settings:
        name = "user"
        indexes = [
            "privy_id",
            "email",
            "linked_accounts.subject",
            "linked_accounts.address",
            "linked_accounts.email",
        ]

    # ---- Password Methods (Class-contained security logic) ----
    def set_password(self, password: str):
        """Securely hash and store password with Argon2"""
        if len(password) < 12:
            raise ValueError("Password must be at least 12 characters")
        self.hashed_password = ph.hash(password)
        
    def verify_password(self, password: str) -> bool:
        """Verify password against Argon2 hash"""
        if not self.hashed_password:
            return False
        try:
            return ph.verify(self.hashed_password, password)
        except (exceptions.VerifyMismatchError, exceptions.InvalidHashError):
            return False
            
    def requires_rehash(self) -> bool:
        """Check if hash needs updating (e.g., after algorithm upgrade)"""
        if not self.hashed_password:
            return False
        return ph.check_needs_rehash(self.hashed_password)
