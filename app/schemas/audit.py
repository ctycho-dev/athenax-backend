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
    """Step 1."""

    name: str
    website: str
    contactName: str
    contactEmail: str
    telegram: Optional[str]
    ecosystem: str
    blockchain: str
    description: str


class Step2(BaseModel):
    """Step 2."""

    codebase: str
    gitLink: Optional[str] = None
    gitHash: Optional[str] = None
    gitBranch: Optional[str] = None
    codebaseZip: Optional[StoredFile] = None
    listOfSmartContracts: Optional[str] = None
    contractUpgradeable: Optional[str] = None
    contractUpgradeableDesc: Optional[str] = None
    deployed: Optional[str] = None
    deployedDesc: Optional[str] = None
    thirdParty: Optional[str] = None


class Step3(BaseModel):
    """Step 3."""

    whitepaper: Optional[str] = None
    whitepaperLink: Optional[str] = None
    whitepaperZip: Optional[StoredFile] = None
    techDocs: Optional[str] = None
    techDocsLink: Optional[str] = None
    techDocsZip: Optional[StoredFile] = None
    tokenomics: Optional[str] = None
    tokenomicsLink: Optional[str] = None
    tokenomicsZip: Optional[StoredFile] = None
    smartContract: Optional[str] = None
    smartContractLink: Optional[str] = None
    smartContractZip: Optional[StoredFile] = None


class Step4(BaseModel):
    """Step 4."""

    framework: Optional[str] = None
    test: Optional[str] = None
    testDesc: Optional[str] = None
    testnet: Optional[str] = None
    testnetLink: Optional[str] = None
    thread: Optional[str] = None


class AuditSteps(BaseModel):
    """All steps."""

    step1: Step1
    step2: Step2
    step3: Step3
    step4: Step4


class AuditOut(BaseModel):
    """All steps."""

    id: str
    steps: AuditSteps
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


# class AuditUpdate(BaseModel):
#     """All steps."""

#     id: str
#     steps: AuditSteps
#     user_privy_id: str


class AuditFormSchema(BaseModel):
    """Project audit schema."""

    steps: AuditSteps
    user_privy_id: Optional[str] = None
