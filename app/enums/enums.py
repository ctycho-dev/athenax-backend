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


class ProductStage(str, Enum):
    """Funding stage for products."""
    PRE_SEED = "Pre-Seed"
    SEED = "Seed"
    SERIES_A = "Series A"
    SERIES_B = "Series B"


class VerificationStatus(str, Enum):
    """Shared pending/approved/rejected values for admin verification."""
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


ProductStatus = VerificationStatus


class PaperStatus(str, Enum):
    """Publication status of a research paper."""
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"


PaperVerificationStatus = VerificationStatus


class PaperSourceType(str, Enum):
    """How the paper content is provided."""
    LINK = "link"
    EDITOR = "editor"


class ProductSortBy(str, Enum):
    """Sort order for product list endpoints."""
    NEWEST = "newest"
    TOP = "top"


class ProductDateFilter(str, Enum):
    """Time window filter for product list endpoints."""
    TODAY = "today"
    THIS_WEEK = "this_week"
    THIS_MONTH = "this_month"
    THIS_YEAR = "this_year"
