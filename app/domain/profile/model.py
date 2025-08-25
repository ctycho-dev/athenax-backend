from beanie import Document, Indexed, PydanticObjectId
from pydantic import Field
from datetime import datetime
from typing import Optional
from app.domain.profile.schema import AccountType, OrganizationType


class Profile(Document):
    """
    Public profile + type-specific details used in onboarding, profile page, and article bylines.
    """
    user_id: Indexed(PydanticObjectId, unique=True)  

    # --- Core public fields you listed ---
    name: Optional[str] = Field(None, description="Full name for profile display")
    username: Indexed(str, unique=True) | None = None
    location: str | None = None
    bio: Optional[str] = None
    profile_image: str | None = None
    display_role: str | None = None
    account_type: AccountType
    
    # --- Socials ---
    github: str | None
    twitter: str | None
    linkedin: str | None
    instagram: str | None
    discord: str | None
    google_scholar: str | None
    orcid: str | None
    researchgate: str | None
    website: str | None
    cmc_cg: str | None

    # --- Publisher ---
    organization_name: str | None
    institution_name: str | None
    verification_status: bool = False

    # --- Project ---
    organization_type: OrganizationType | None
    mission: str | None
    team_size: int | None
    founded_year: int | None

    # --- Personal ---
    current_affiliation: str | None
    interests: list[str] = Field(default_factory=list)

    created_at: datetime = Field(default_factory=datetime.now)
    updated_at: datetime = Field(default_factory=datetime.now)

    class Settings:
        name = "profile"
        indexes = ["user_id", "username", "account_type"]
