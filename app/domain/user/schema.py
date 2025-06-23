from typing import Optional
from pydantic import BaseModel, EmailStr, ConfigDict, field_serializer
from datetime import datetime
from pydantic import Field, EmailStr

from app.enums.enums import UserRole, WalletChains, AuthProvider


class VerificationInfo(BaseModel):
    """Model containing verification timestamps for accounts or wallets.
    
    Attributes:
        verified_at: When the verification was last performed.
        first_verified_at: When the verification was first performed.
        latest_verified_at: The most recent verification time.
    """
    verified_at: datetime
    first_verified_at: datetime
    latest_verified_at: datetime


class LinkedAccount(BaseModel):
    """Model representing a linked authentication account for a user.
    
    Attributes:
        type: The authentication provider type.
        subject: Unique identifier from OAuth provider (optional).
        address: Email address (for email auth, optional).
        username: Discord username (optional).
        name: Full name from Google (optional).
        email: Email from OAuth provider (optional).
        verified_at: When the verification was last performed.
        first_verified_at: When the verification was first performed.
        latest_verified_at: The most recent verification time.
        primary: Whether this is the primary linked account.
    """
    type: AuthProvider
    subject: Optional[str] = None  # For OAuth providers
    address: Optional[str] = None  # For email
    username: Optional[str] = None  # For Discord
    name: Optional[str] = None  # For Google
    email: Optional[EmailStr] = None
    primary: bool = False
    chainType: Optional[str] = None
    connectorType: Optional[str] = None
    walletClientType: Optional[str] = None


class Wallet(BaseModel):
    """Document model representing a user's cryptocurrency wallet.
    
    Attributes:
        address: The wallet address.
        chain: The blockchain network the wallet is on.
        verified: Whether the wallet is verified.
        primary: Whether this is the user's primary wallet.
        verification: Wallet verification information (optional).
    """
    
    address: str
    chain: WalletChains
    verified: bool = False
    primary: bool = False
    verification: Optional[VerificationInfo] = None


class UserCreate(BaseModel):
    """
    Schema for creating a new user.

    Attributes:
        email (EmailStr): The user's email address.
        password (str): The user's password.
    """
    privy_id: str
    linked_accounts: list[LinkedAccount] = []
    # wallets: list[Wallet] = []
    # created_at: datetime = Field(default_factory=datetime.now)
    metadata: dict = Field(default_factory=dict)
    role: UserRole = UserRole.USER
    has_accepted_terms: bool = False
    is_guest: bool = False


class UserOut(BaseModel):
    """
    Schema for returning user details.

    Attributes:
        id (int): The user's unique identifier.
        email (EmailStr): The user's email address.
        created_at (datetime): The timestamp when the user was created.
    """
    id: str
    privy_id: str
    linked_accounts: Optional[list[LinkedAccount]]
    # wallets: Optional[list[Wallet]]
    role: UserRole
    has_accepted_terms: bool
    is_guest: bool
    created_at: datetime

    @field_serializer('created_at')
    def serialize_dt(self, created_at: datetime):
        """Convert `created_at` to ISO 8601 string during the validation process."""
        return created_at.isoformat()

    model_config = ConfigDict(from_attributes=True)

