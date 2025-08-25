from typing import Literal
from pydantic import BaseModel, Field, ConfigDict, field_serializer
from datetime import datetime


AccountType = Literal["Publisher", "Project", "Personal use"]
OrganizationType = Literal["Startup", "Lab", "Corporate"]


# ---------- PROFILE: CREATE / UPDATE / OUT ----------

class ProfileCreate(BaseModel):
    """
    Create a Profile during onboarding (minimal required: account_type + username).
    """
    user_id: str | None = None
    account_type: AccountType
    username: str | None = None

    # public display
    name: str | None = None
    location: str | None = None
    bio: str | None = None
    profile_image: str | None = None
    display_role: str | None = None

    # socials
    github: str | None = None
    twitter: str | None = None
    linkedin: str | None = None
    instagram: str | None = None
    discord: str | None = None
    google_scholar: str | None = None
    orcid: str | None = None
    researchgate: str | None = None
    website: str | None = None
    cmc_cg: str | None = None

    # publisher
    organization_name: str | None = None
    institution_name: str | None = None
    verification_status: bool = False

    # project
    organization_type: OrganizationType | None = None
    mission: str | None = None
    team_size: int | None = Field(default=None, ge=1)
    founded_year: int | None = None

    # personal
    current_affiliation: str | None = None
    interests: list[str] = Field(default_factory=list)


class ProfileUpdate(BaseModel):
    """
    PATCH-style updates for Profile only.
    All fields optional. Arrays replace by default (idempotent PUT semantics).
    """
    # public display
    account_type: AccountType | None = None
    username: str | None = None
    name: str | None = None
    location: str | None = None
    bio: str | None = None
    profile_image: str | None = None

    # display roles (replace list)
    display_role: str | None

    # socials (replace list)
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

    # publisher
    organization_name: str | None = None
    institution_name: str | None = None
    verification_status: bool | None = None

    # project
    organization_type: OrganizationType | None
    mission: str | None
    team_size: int | None
    founded_year: int | None

    # personal
    current_affiliation: str | None
    interests: list[str]


class ProfileOut(BaseModel):

    id: str
    user_id: str
    account_type: AccountType

    # public display
    username: str | None
    name: str | None
    location: str | None
    bio: str | None
    profile_image: str | None
    display_role: str

    # socials
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

    # publisher
    organization_name: str | None
    institution_name: str | None
    verification_status: bool

    # project
    organization_type: OrganizationType | None
    mission: str | None
    team_size: int | None
    founded_year: int | None

    # personal
    current_affiliation: str | None
    interests: list[str]

    created_at: datetime = Field(default_factory=datetime.now)

    @field_serializer("created_at")
    def _ser_created_at(self, v: datetime) -> str:
        return v.isoformat()

    model_config = ConfigDict(from_attributes=True)
