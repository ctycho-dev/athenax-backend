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
