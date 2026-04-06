from enum import Enum


class AppMode(str, Enum):
    """Runtime mode of the application."""
    PROD = "prod"
    DEV = "dev"
    TEST = "test"


class UserRole(str, Enum):
    """User role and permissions in the system."""
    ADMIN = "admin"
    USER = "user"
    RESEARCHER = "researcher"
    SPONSOR = "sponsor"
    FOUNDER = "founder"
    INVESTOR = "investor"


class TokenType(str, Enum):
    """Purpose of a one-time token stored on a user."""
    VERIFICATION = "verification"
    RESET = "reset"


class InvestorType(str, Enum):
    """Type of investor."""
    VC = "VC"
    ANGEL = "Angel"
    CORPORATE = "Corporate"
    FAMILY_OFFICE = "Family Office"


class ProductSector(str, Enum):
    """High-level sector classification for products."""
    AI_AND_AGENTS = "AI & Agents"
    ROBOTICS = "Robotics"
    BIOTECH = "Biotech"
    CRYPTO_AND_DEFI = "Crypto & DeFi"
    DEVELOPER_TOOLS = "Developer Tools"
    INFRASTRUCTURE = "Infrastructure"
    CLIMATE_AND_ENERGY = "Climate & Energy"


class ProductStage(str, Enum):
    """Funding stage for products."""
    PRE_SEED = "Pre-Seed"
    SEED = "Seed"
    SERIES_A = "Series A"
    SERIES_B = "Series B"


class ProductStatus(str, Enum):
    """Verification/approval status of a product."""
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class PaperStatus(str, Enum):
    """Publication status of a research paper."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


class PaperSourceType(str, Enum):
    """How the paper content is provided."""
    LINK = "link"
    EDITOR = "editor"
