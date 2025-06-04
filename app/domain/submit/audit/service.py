# services/submit/audit.py
from app.domain.submit.audit.schema import (
    AuditSubmitSchema,
    Comment
)
from app.domain.user.schema import UserOut
from app.domain.user.model import User
from app.domain.submit.audit.repository import AuditRepository
from app.exceptions import NotFoundError
from app.enums.enums import ReportState



class AuditService:
    """
    Service layer for handling business logic related to audit operations.
    """

    def __init__(self, repo: AuditRepository, user: User):
        """
        Initialize the AuditService with a repository and an optional user context.
        
        Args:
            repo (AuditRepository): Repository for audit DB operations.
            user (UserOut): Currently authenticated user.
        """
        self.repo = repo
        self.user = user

    async def get_all(self):
        """
        Retrieve all audit records.

        Returns:
            List[AuditOut]: List of all audits.
        """
        return await self.repo.get_all()

    async def get_by_user(self):
        """
        Retrieve audits belonging to the current user.

        Raises:
            ValueError: If user context is not provided.

        Returns:
            List[AuditOut]: List of user-specific audits.
        """
        if not self.user:
            raise ValueError("User context required")
        return await self.repo.get_by_user(self.user.privy_id)
    
    async def get_by_state(self, state: str):
        """
        Retrieve all audit records.

        Returns:
            List[AuditOut]: List of all audits.
        """
        return await self.repo.get_by_state(state)

    async def get_by_id(self, audit_id: str):
        """
        Retrieve a single audit by its ID.

        Args:
            audit_id (str): The audit's UUID.

        Raises:
            NotFoundError: If audit is not found.

        Returns:
            AuditOut: The audit object.
        """
        audit = await self.repo.get_by_id(audit_id)
        if not audit:
            raise NotFoundError(f"Audit with ID {audit_id} not found")
        return audit

    async def create(self, data: AuditSubmitSchema):
        """
        Create a new audit entry.

        Args:
            data (AuditSubmitSchema): Data for the new audit.

        Raises:
            ValueError: If user context is not available.

        Returns:
            AuditOut: The created audit.
        """
        if not self.user:
            raise ValueError("User context required")
        data.user_privy_id = self.user.privy_id
        return await self.repo.create(entity=data, current_user=self.user)

    async def update(self, audit_id: str, data: AuditSubmitSchema):
        """
        Update an existing audit if the user is authorized.

        Args:
            audit_id (str): UUID of the audit to update.
            data (AuditSubmitSchema): New audit data.

        Raises:
            NotFoundError: If audit is not found.
            PermissionError: If user is not the owner.

        Returns:
            AuditOut: The updated audit.
        """
        audit = await self.repo.get_by_id(audit_id)
        if not audit:
            raise NotFoundError("Audit not found")
        if audit.user_privy_id != self.user.privy_id:
            raise PermissionError("Not authorized to update this audit")
        
        data.state = ReportState.CHECKING
        
        return await self.repo.update(audit_id, data, current_user=self.user)
    
    async def add_comment(self, audit_id: str, data: str):
        """
        Update an existing audit if the user is authorized.

        Args:
            audit_id (str): UUID of the audit to update.
            data (AuditSubmitSchema): New audit data.

        Raises:
            NotFoundError: If audit is not found.
            PermissionError: If user is not the owner.

        Returns:
            AuditOut: The updated audit.
        """
        comment = Comment(
            role=self.user.role,
            content=data
        )
        audit = await self.repo.add_comment(
            audit_id,
            comment=comment,
            current_user=self.user
        )
        if not audit:
            raise NotFoundError("Audit not found")
