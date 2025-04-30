from datetime import datetime
from beanie import Document, Indexed
from pydantic import Field
from app.enums.enums import UserRole
from app.schemas.user import LinkedAccount, Wallet


class User(Document):
    """Main user document model representing a system user.
    
    Attributes:
        privy_id: Unique identifier from Privy (indexed).
        linked_accounts: list of linked authentication accounts.
        wallets: list of associated cryptocurrency wallets.
        created_at: Timestamp when user was created.
        metadata: Additional user metadata as key-value pairs.
        role: User's role in the system.
        has_accepted_terms: Whether user accepted terms of service.
        is_guest: Whether user is a guest account.
        
    Class Settings:
        name: MongoDB collection name.
        indexes: list of fields to index for faster queries.
    """
    privy_id: Indexed(str, unique=True)
    linked_accounts: list[LinkedAccount] = []
    # wallets: list[Wallet] = []
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: dict = Field(default_factory=dict)
    role: UserRole = UserRole.USER
    has_accepted_terms: bool = False
    is_guest: bool = False

    class Settings:
        name = "user"
        indexes = [
            "linked_accounts.subject",
            "linked_accounts.address",
            "linked_accounts.email",
        ]