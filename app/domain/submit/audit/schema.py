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
    """Step 1."""

    name: str
    website: str
    contactName: str
    contactEmail: str
    telegram: str | None
    ecosystem: str
    blockchain: str
    description: str


class Step2(BaseModel):
    """Step 2."""

    codebase: str
    gitLink: str | None
    gitHash: str | None
    gitBranch: str | None
    codebaseZip: StoredFile | None
    listOfSmartContracts: str | None
    contractUpgradeable: str | None
    contractUpgradeableDesc: str | None
    deployed: str | None
    deployedDesc: str | None
    thirdParty: str | None


class Step3(BaseModel):
    """Step 3."""

    whitepaper: str | None
    whitepaperLink: str | None
    whitepaperZip: StoredFile | None
    techDocs: str | None
    techDocsLink: str | None
    techDocsZip: StoredFile | None
    tokenomics: str | None
    tokenomicsLink: str | None
    tokenomicsZip: StoredFile | None
    smartContract: str | None
    smartContractLink: str | None
    smartContractZip: StoredFile | None


class Step4(BaseModel):
    """Step 4."""

    framework: str | None
    test: str | None
    testDesc: str | None
    testnet: str | None
    testnetLink: str | None
    thread: str | None


class AuditSteps(BaseModel):
    """All steps."""

    step1: Step1
    step2: Step2
    step3: Step3
    step4: Step4


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


class AuditOut(BaseModel):
    """All steps."""

    id: str
    steps: AuditSteps
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


# class AuditUpdate(BaseModel):
#     """All steps."""

#     id: str
#     steps: AuditSteps
#     user_privy_id: str


class AuditSubmitSchema(BaseModel):
    """Project audit schema."""

    steps: AuditSteps
    user_privy_id: str | None = None
    state: ReportState = ReportState.SUBMITTED


class StateUpdateSchema(BaseModel):

    state: ReportState


class CommentCreateSchema(BaseModel):
    comment: str
