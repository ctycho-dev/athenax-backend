from uuid import (
    uuid4,
    UUID
)
from datetime import datetime
from pydantic import (
    BaseModel,
    ConfigDict,
    field_serializer,
    Field
)
from app.enums.enums import (
    ReportState,
    UserRole
)
from app.infrastructure.storage.schema import StoredFile


class Step1(BaseModel):
    """Basic project information"""
    name: str
    tagline: str
    launchDate: str
    contactEmail: str
    primaryContactName: str
    primaryContactRole: str
    twitter: str | None
    discord: str | None
    telegram: str | None
    github: str | None


class Step2(BaseModel):
    """Team and governance information"""
    foundersAndCoreTeam: str
    advisors: str
    orgStructure: str
    governance: str


class Step3(BaseModel):
    """Product and technical information"""
    productDesc: str
    useCases: str
    techArchitecture: str | None
    integrations: str


class Step4(BaseModel):
    """Token information"""
    tokenDetails: str
    utilities: str
    supply: str
    distribution: str
    emission: str


class Step5(BaseModel):
    """Financial information"""
    funding: str
    revenue: str
    treasury: str
    runway: str


class Step6(BaseModel):
    """Metrics and community information"""
    metrics: str
    tvl: str
    partnerships: str
    community: str


class Step7(BaseModel):
    """Legal and compliance information"""
    legalEntity: str
    compliance: str
    audits: str


class Step8(BaseModel):
    """Risk management information"""
    risks: str
    strategies: str


class Step9(BaseModel):
    """Media and brand information"""
    mediaCoverage: str
    communityContent: str
    brand: str
    brandLink: str | None
    brandZip: StoredFile | None


class Step10(BaseModel):
    """Documentation and materials"""
    whitepaper: str
    whitepaperLink: str | None
    whitepaperZip: StoredFile | None
    faq: str
    faqLink: str | None
    faqZip: StoredFile | None
    materials: str
    materialsLink: str | None
    materialsZip: StoredFile | None


class ResearchSteps(BaseModel):
    """All steps."""

    step1: Step1
    step2: Step2
    step3: Step3
    step4: Step4
    step5: Step5
    step6: Step6
    step7: Step7
    step8: Step8
    step9: Step9
    step10: Step10


class Comment(BaseModel):
    """"""
    id: UUID = Field(
        default_factory=uuid4,
        description="Unique identifier."
    )
    role: UserRole = UserRole.USER
    content: str
    created_at: datetime = Field(
        default_factory=datetime.now,
        description="Timestamp when the record was created"
    )


class ResearchOut(BaseModel):
    """All steps."""

    id: str
    steps: ResearchSteps
    state: ReportState
    comments: list[Comment] | None
    user_privy_id: str
    created_at: datetime
    updated_at: datetime

    @field_serializer('created_at')
    def serialize_created_at(self, created_at: datetime) -> str:
        """Convert `created_at` to ISO 8601 string during serialization."""
        return created_at.isoformat()
    
    @field_serializer('updated_at')
    def serialize_updated_at(self, updated_at: datetime) -> str:
        """Convert `updated_at` to ISO 8601 string during serialization."""
        return updated_at.isoformat()

    model_config = ConfigDict(from_attributes=True)


class ResearchSubmitSchema(BaseModel):
    """Project audit schema."""

    steps: ResearchSteps
    user_privy_id: str | None = None
    state: ReportState = ReportState.SUBMITTED


class StateUpdateSchema(BaseModel):

    state: ReportState


class CommentCreateSchema(BaseModel):
    comment: str