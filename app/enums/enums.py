from enum import Enum


class AppMode(str, Enum):
    """Runtime mode of the application."""
    PROD = "prod"
    DEV = "dev"
    TEST = "test"


class UserRole(str, Enum):
    """User role and permissions in the system."""
    USER = "user"
    RESEARCHER = "researcher"
    SPONSOR = "sponsor"
    BUILDER = "builder"


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
