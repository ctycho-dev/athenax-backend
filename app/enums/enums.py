from enum import Enum


class UserRole(str, Enum):
    """User role and permissions in the system."""
    ADMIN = "admin"
    USER = "user"
    RESEARCHER = "researcher"
    SPONSOR = "sponsor"
    FOUNDER = "founder"
    INVESTOR = "investor"
    BD = "bd"  # business development; mirrors admin for all current functionality
    SYSTEM = "system"  # owns records created by internal services; never logs in


# Email of the seeded system user that owns records created via internal endpoints.
# Shared by the seeding migration and the runtime get_system_user lookup.
SYSTEM_USER_EMAIL = "system@athenax.internal"


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
    PRE_SEED          = "Pre-Seed"
    SEED              = "Seed"
    SERIES_A          = "Series A"
    SERIES_B          = "Series B"
    LAUNCHED           = "Launched"
    BETA               = "Beta"
    ACTIVE             = "Active"
    ACTIVE_DEVELOPMENT = "Active Development"
    ACQUIRED           = "Acquired / Operating"


class VerificationStatus(str, Enum):
    """Shared pending/approved/rejected values for admin verification."""
    PENDING  = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


ProductStatus = VerificationStatus
PaperVerificationStatus = VerificationStatus


class PaperSourceType(str, Enum):
    """How the paper content is provided."""
    LINK = "link"
    EDITOR = "editor"


class ProductSortBy(str, Enum):
    """Sort order for product list endpoints."""
    NEWEST = "newest"
    OLDEST = "oldest"
    TOP = "top"


class ProductDateFilter(str, Enum):
    """Time window filter for product list endpoints."""
    TODAY = "today"
    THIS_WEEK = "this_week"
    THIS_MONTH = "this_month"
    RECENT = "recent"
    THIS_YEAR = "this_year"


class ProductLinkType(str, Enum):
    WEBSITE = "website"
    GITHUB  = "github"
    TWITTER = "twitter"
    DOCS    = "docs"
    DEMO    = "demo"
    DISCORD = "discord"
    LINKEDIN  = "linkedin"
    YOUTUBE   = "youtube"
    INSTAGRAM = "instagram"
    OTHER     = "other"


class ProductMediaType(str, Enum):
    IMAGE         = "image"
    VIDEO_HOSTED  = "video_hosted"
    VIDEO_YOUTUBE = "video_youtube"


class BountyStatus(str, Enum):
    OPEN      = "open"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


TeamMemberStatus = VerificationStatus


class ContentStatus(str, Enum):
    DRAFT     = "draft"
    PUBLISHED = "published"
    ARCHIVED  = "archived"


ArticleStatus = ContentStatus
BroadcastStatus = ContentStatus
PaperStatus = ContentStatus


class ContentType(str, Enum):
    WHITEPAPER  = "whitepaper"
    LIVESTREAM  = "livestream"
    ROUNDTABLE  = "roundtable"


ArticleType = ContentType
BroadcastType = ContentType
