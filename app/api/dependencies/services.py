from fastapi import Depends
from app.domain.user.repository import UserRepository
from app.domain.user.service import UserService
from app.infrastructure.email.service import EmailService
from app.domain.university.repository import UniversityRepository
from app.domain.university.service import UniversityService
from app.domain.lab.repository import LabRepository
from app.domain.lab.service import LabService


# -------------------------
# Repository Factories
# -------------------------
def get_user_repo() -> UserRepository:
    return UserRepository()


def get_email_service() -> EmailService:
    return EmailService()


def get_university_repo() -> UniversityRepository:
    return UniversityRepository()


def get_lab_repo() -> LabRepository:
    return LabRepository()


# -------------------------
# Services
# -------------------------
def get_user_service(
    repo: UserRepository = Depends(get_user_repo),
    email_service: EmailService = Depends(get_email_service),
) -> UserService:
    return UserService(repo=repo, email_service=email_service)


def get_university_service(
    repo: UniversityRepository = Depends(get_university_repo),
) -> UniversityService:
    return UniversityService(repo=repo)


def get_lab_service(
    repo: LabRepository = Depends(get_lab_repo),
    university_repo: UniversityRepository = Depends(get_university_repo),
) -> LabService:
    return LabService(repo=repo, university_repo=university_repo)
