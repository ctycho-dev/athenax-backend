from typing import Optional
from datetime import datetime
from pydantic import BaseModel, ConfigDict, field_serializer
from app.enums.enums import ReportState

class StoredFile(BaseModel):
    """File schema."""

    bucket: str
    key: str
    original_filename: str
    content_type: str


class Step1(BaseModel):
    """Basic project information"""
    name: str
    tagline: str
    launchDate: str
    contactEmail: str
    primaryContactName: str
    primaryContactRole: str
    twitter: Optional[str] = None
    discord: Optional[str] = None
    telegram: Optional[str] = None
    github: Optional[str] = None


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
    techArchitecture: Optional[str] = None
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
    brandLink: Optional[str] = None
    brandZip: Optional[StoredFile] = None


class Step10(BaseModel):
    """Documentation and materials"""
    whitepaper: str
    whitepaperLink: Optional[str] = None
    whitepaperZip: Optional[StoredFile] = None
    faq: str
    faqLink: Optional[str] = None
    faqZip: Optional[StoredFile] = None
    materials: str
    materialsLink: Optional[str] = None
    materialsZip: Optional[StoredFile] = None


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


class ResearchOut(BaseModel):
    """All steps."""

    id: str
    steps: ResearchSteps
    state: ReportState
    admin_comment: Optional[str]
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


class ResearchFormSchema(BaseModel):
    """Project audit schema."""

    steps: ResearchSteps
    user_privy_id: Optional[str] = None
