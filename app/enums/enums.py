from enum import Enum


class AppMode(str, Enum):
    """App mode."""

    PROD = "prod"
    DEV = "dev"
    TEST = "test"


class UserRole(str, Enum):
    """Enum representing possible user roles in the system.

    Attributes:
        ADMIN: Administrator role with full privileges.
        BD: Business Development role with specific privileges.
        USER: Regular user role with basic privileges.
    """
    ADMIN = "admin"
    BD = "bd"
    USER = 'user'


class WalletChains(str, Enum):
    """Enum representing supported blockchain networks for wallets.

    Attributes:
        ETH: Ethereum blockchain.
        SOL: Solana blockchain.
    """
    ETH = "eth"
    SOL = "sol"


class AuthProvider(str, Enum):
    """Enum representing authentication providers supported by the system.

    Attributes:
        GOOGLE: Google OAuth provider.
        DISCORD: Discord OAuth provider.
        TWITTER: Twitter OAuth provider.
        EMAIL: Email-based authentication.
    """
    GOOGLE = "google_oauth"
    DISCORD = "discord_oauth"
    TWITTER = "twitter_oauth"
    EMAIL = "email"
    WALLET = "wallet"


class ReportState(str, Enum):
    """Enum representing the possible states of a report."""

    SUBMITTED = 'Submitted'
    CHECKING = 'Checking'
    WRITING = 'Writing'
    UPDATE_INFO = 'Update Info'
    COMPLETED = 'Completed'
    REJECTED = 'Rejected'

    @classmethod
    def get_default(cls) -> 'ReportState':
        """Returns the default state (SUBMITTED)."""
        return cls.SUBMITTED
