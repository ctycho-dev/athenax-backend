from fastapi import Depends
from app.domain.user.repository import (
    UserRepository,
    InvestorProfileRepository,
    ResearcherProfileRepository,
    SponsorProfileRepository,
    UserCategoryRepository,
)
from app.domain.user.service import UserService
from app.infrastructure.email.service import EmailService
from app.domain.university.repository import UniversityRepository
from app.domain.university.service import UniversityService
from app.domain.category.repository import CategoryRepository
from app.domain.category.service import CategoryService
from app.domain.lab.repository import LabRepository
from app.domain.lab.service import LabService
from app.domain.paper.repository import PaperRepository
from app.domain.paper.service import PaperService
from app.domain.product.repository import (
    CommentRepository, ProductRepository,
    ProductLinkRepository, ProductMediaRepository, ProductTeamRepository,
    ProductBackerRepository, ProductVoiceRepository, BountyRepository,
)
from app.domain.product.service import ProductService


# -------------------------
# Repository Factories
# -------------------------
def get_user_repo() -> UserRepository:
    return UserRepository()


def get_email_service() -> EmailService:
    return EmailService()


def get_university_repo() -> UniversityRepository:
    return UniversityRepository()


def get_category_repo() -> CategoryRepository:
    return CategoryRepository()


def get_lab_repo() -> LabRepository:
    return LabRepository()


def get_investor_profile_repo() -> InvestorProfileRepository:
    return InvestorProfileRepository()


def get_researcher_profile_repo() -> ResearcherProfileRepository:
    return ResearcherProfileRepository()


def get_sponsor_profile_repo() -> SponsorProfileRepository:
    return SponsorProfileRepository()


def get_user_category_repo() -> UserCategoryRepository:
    return UserCategoryRepository()


def get_paper_repo() -> PaperRepository:
    return PaperRepository()


def get_product_repo() -> ProductRepository:
    return ProductRepository()


def get_comment_repo() -> CommentRepository:
    return CommentRepository()


def get_link_repo() -> ProductLinkRepository:
    return ProductLinkRepository()


def get_media_repo() -> ProductMediaRepository:
    return ProductMediaRepository()


def get_team_repo() -> ProductTeamRepository:
    return ProductTeamRepository()


def get_backer_repo() -> ProductBackerRepository:
    return ProductBackerRepository()


def get_voice_repo() -> ProductVoiceRepository:
    return ProductVoiceRepository()


def get_bounty_repo() -> BountyRepository:
    return BountyRepository()


# -------------------------
# Services
# -------------------------
def get_user_service(
    repo: UserRepository = Depends(get_user_repo),
    email_service: EmailService = Depends(get_email_service),
    investor_profile_repo: InvestorProfileRepository = Depends(get_investor_profile_repo),
    researcher_profile_repo: ResearcherProfileRepository = Depends(get_researcher_profile_repo),
    sponsor_profile_repo: SponsorProfileRepository = Depends(get_sponsor_profile_repo),
    user_category_repo: UserCategoryRepository = Depends(get_user_category_repo),
    category_repo: CategoryRepository = Depends(get_category_repo),
) -> UserService:
    return UserService(
        repo=repo,
        email_service=email_service,
        investor_profile_repo=investor_profile_repo,
        researcher_profile_repo=researcher_profile_repo,
        sponsor_profile_repo=sponsor_profile_repo,
        user_category_repo=user_category_repo,
        category_repo=category_repo,
    )


def get_university_service(
    repo: UniversityRepository = Depends(get_university_repo),
) -> UniversityService:
    return UniversityService(repo=repo)


def get_category_service(
    repo: CategoryRepository = Depends(get_category_repo),
) -> CategoryService:
    return CategoryService(repo=repo)


def get_lab_service(
    repo: LabRepository = Depends(get_lab_repo),
    university_repo: UniversityRepository = Depends(get_university_repo),
    category_repo: CategoryRepository = Depends(get_category_repo),
) -> LabService:
    return LabService(repo=repo, university_repo=university_repo, category_repo=category_repo)


def get_paper_service(
    repo: PaperRepository = Depends(get_paper_repo),
    category_repo: CategoryRepository = Depends(get_category_repo),
) -> PaperService:
    return PaperService(repo=repo, category_repo=category_repo)


def get_product_service(
    repo: ProductRepository = Depends(get_product_repo),
    category_repo: CategoryRepository = Depends(get_category_repo),
    comment_repo: CommentRepository = Depends(get_comment_repo),
    link_repo: ProductLinkRepository = Depends(get_link_repo),
    media_repo: ProductMediaRepository = Depends(get_media_repo),
    team_repo: ProductTeamRepository = Depends(get_team_repo),
    backer_repo: ProductBackerRepository = Depends(get_backer_repo),
    voice_repo: ProductVoiceRepository = Depends(get_voice_repo),
    bounty_repo: BountyRepository = Depends(get_bounty_repo),
) -> ProductService:
    return ProductService(
        repo=repo,
        category_repo=category_repo,
        comment_repo=comment_repo,
        link_repo=link_repo,
        media_repo=media_repo,
        team_repo=team_repo,
        backer_repo=backer_repo,
        voice_repo=voice_repo,
        bounty_repo=bounty_repo,
    )
