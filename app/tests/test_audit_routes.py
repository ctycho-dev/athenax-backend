# import pytest
# from datetime import datetime
# from httpx import AsyncClient

# from app.main import app
# from app.domain.user.model import User
# from app.enums.enums import UserRole, ReportState
# from app.domain.submit.audit.model import AuditSubmit
# from app.domain.submit.audit.service import AuditService
# from app.domain.submit.audit.repository import AuditRepository
# from app.core.dependencies import get_current_user, get_audit_service


# # --- Utility: Create user if missing ---
# async def create_test_user_if_not_exists() -> User:
#     privy_id = "did:privy:cm9flrb6n00gcld0mu1dyny0c"
#     user = await User.find_one(User.privy_id == privy_id)
#     if user:
#         return user

#     user = User(
#         privy_id=privy_id,
#         role=UserRole.BD,
#         email_verified=True,
#         linked_accounts=[
#             {
#                 "type": "google_oauth",
#                 "subject": "115614841313059665956",
#                 "email": "ctycho23@gmail.com",
#                 "name": "Ilnur"
#             },
#             {
#                 "type": "email",
#                 "address": "ctycho23@gmail.com"
#             }
#         ],
#         created_at=datetime.utcnow(),
#         updated_at=datetime.utcnow()
#     )
#     await user.insert()
#     return user


# # --- Utility: Create audit if missing ---
# async def create_test_audit(user: User) -> AuditSubmit:
#     existing = await AuditSubmit.find_one(
#         AuditSubmit.user_privy_id == user.privy_id,
#         AuditSubmit.state == ReportState.UPDATE_INFO
#     )
#     if existing:
#         return existing

#     audit = AuditSubmit(
#         user_privy_id=user.privy_id,
#         created_by=user,
#         updated_by=user,
#         state=ReportState.UPDATE_INFO,
#         created_at=datetime.utcnow(),
#         updated_at=datetime.utcnow(),
#         steps={
#             "step1": {
#                 "name": "sui",
#                 "website": "sui@gmail.co",
#                 "contactName": "name",
#                 "contactEmail": "na@mail.ri",
#                 "telegram": "",
#                 "ecosystem": "DeFi",
#                 "blockchain": "Bitcoin",
#                 "description": "ok"
#             },
#             "step2": {
#                 "codebase": "github",
#                 "gitLink": "ok",
#                 "gitHash": "ok",
#                 "gitBranch": "ok",
#                 "listOfSmartContracts": "ok",
#                 "contractUpgradeable": "no",
#                 "deployed": "no",
#                 "thirdParty": "ok"
#             },
#             "step3": {
#                 "whitepaper": "none",
#                 "techDocs": "none",
#                 "tokenomics": "none",
#                 "smartContract": "none"
#             },
#             "step4": {
#                 "framework": "ok",
#                 "test": "no",
#                 "thread": "ok"
#             }
#         },
#         comments=[
#             {
#                 "role": user.role,
#                 "content": "hello",
#                 "created_at": datetime.utcnow()
#             },
#             {
#                 "role": user.role,
#                 "content": "today",
#                 "created_at": datetime.utcnow()
#             }
#         ]
#     )
#     await audit.insert()
#     return audit


# # --- Fixture: User and Audit ---
# @pytest.fixture
# async def test_user_and_audit():
#     user = await create_test_user_if_not_exists()
#     audit = await create_test_audit(user)
#     return user, audit


# # --- Override get_current_user ---
# @pytest.fixture(autouse=True)
# def override_auth(test_user_and_audit):
#     user, _ = test_user_and_audit

#     async def _override():
#         return user

#     app.dependency_overrides[get_current_user] = _override


# # --- Override get_audit_service ---
# @pytest.fixture(autouse=True)
# def override_service(test_user_and_audit):
#     user, _ = test_user_and_audit
#     repo = AuditRepository()

#     def _override():
#         return AuditService(repo=repo, user=user)

#     app.dependency_overrides[get_audit_service] = _override


# # --- HTTP client ---
# @pytest.fixture
# async def client():
#     async with AsyncClient(app=app, base_url="http://test") as ac:
#         yield ac


# # --- Endpoint Tests ---

# # @pytest.mark.asyncio
# # async def test_get_audits_by_user(client):
# #     response = await client.get("/submit/audit/user/")
# #     assert response.status_code == 200
# #     data = response.json()
# #     assert isinstance(data, list)
# #     assert len(data) >= 1
# #     assert data[0]["user_privy_id"] == "did:privy:cm9flrb6n00gcld0mu1dyny0c"


# # @pytest.mark.asyncio
# # async def test_create_audit(client):
# #     payload = {
# #         "title": "New Audit",
# #         "description": "Security Review",
# #         "category": "Tech",
# #         "data": {"risk": "medium"}
# #     }

# #     response = await client.post("/submit/audit/", json=payload)
# #     assert response.status_code == 200
# #     assert response.json() == {"success": True}
