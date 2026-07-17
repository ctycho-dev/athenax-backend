from fastapi import Depends
from app.api.dependencies.integrations import get_redis_client
from app.infrastructure.redis.client import RedisClient
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
    ProductBackerRepository, ProductGrantRepository, ProductVoiceRepository, BountyRepository,
)
from app.domain.product.service import ProductService
from app.infrastructure.logodev.service import LogoDevService
from app.domain.article.repository import ArticleRepository
from app.domain.article.service import ArticleService
from app.domain.broadcast.repository import BroadcastRepository
from app.domain.broadcast.service import BroadcastService
from app.domain.tag.repository import TagRepository
from app.domain.subscriber.repository import SubscriberRepository
from app.domain.subscriber.service import SubscriberService
from app.common.storage import R2StorageService


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


def get_grant_repo() -> ProductGrantRepository:
    return ProductGrantRepository()


def get_voice_repo() -> ProductVoiceRepository:
    return ProductVoiceRepository()


def get_bounty_repo() -> BountyRepository:
    return BountyRepository()


def get_article_repo() -> ArticleRepository:
    return ArticleRepository()


def get_broadcast_repo() -> BroadcastRepository:
    return BroadcastRepository()


def get_tag_repo() -> TagRepository:
    return TagRepository()


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
    redis: RedisClient = Depends(get_redis_client),
) -> CategoryService:
    return CategoryService(repo=repo, redis=redis)


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


def get_storage_service() -> R2StorageService:
    return R2StorageService()


def get_logo_dev_service() -> LogoDevService:
    return LogoDevService()


def get_article_service(
    repo: ArticleRepository = Depends(get_article_repo),
    tag_repo: TagRepository = Depends(get_tag_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    broadcast_repo: BroadcastRepository = Depends(get_broadcast_repo),
    redis: RedisClient = Depends(get_redis_client),
) -> ArticleService:
    return ArticleService(repo=repo, tag_repo=tag_repo, user_repo=user_repo, broadcast_repo=broadcast_repo, redis=redis)


def get_broadcast_service(
    repo: BroadcastRepository = Depends(get_broadcast_repo),
    tag_repo: TagRepository = Depends(get_tag_repo),
    user_repo: UserRepository = Depends(get_user_repo),
    article_repo: ArticleRepository = Depends(get_article_repo),
    redis: RedisClient = Depends(get_redis_client),
) -> BroadcastService:
    return BroadcastService(repo=repo, tag_repo=tag_repo, user_repo=user_repo, article_repo=article_repo, redis=redis)


def get_subscriber_repo() -> SubscriberRepository:
    return SubscriberRepository()


def get_subscriber_service(
    repo: SubscriberRepository = Depends(get_subscriber_repo),
    email_service: EmailService = Depends(get_email_service),
) -> SubscriberService:
    return SubscriberService(repo=repo, email_service=email_service)


def get_product_service(
    repo: ProductRepository = Depends(get_product_repo),
    category_repo: CategoryRepository = Depends(get_category_repo),
    comment_repo: CommentRepository = Depends(get_comment_repo),
    link_repo: ProductLinkRepository = Depends(get_link_repo),
    media_repo: ProductMediaRepository = Depends(get_media_repo),
    team_repo: ProductTeamRepository = Depends(get_team_repo),
    backer_repo: ProductBackerRepository = Depends(get_backer_repo),
    grant_repo: ProductGrantRepository = Depends(get_grant_repo),
    voice_repo: ProductVoiceRepository = Depends(get_voice_repo),
    bounty_repo: BountyRepository = Depends(get_bounty_repo),
    email_service: EmailService = Depends(get_email_service),
    logo_dev_service: LogoDevService = Depends(get_logo_dev_service),
    redis: RedisClient = Depends(get_redis_client),
) -> ProductService:
    return ProductService(
        repo=repo,
        category_repo=category_repo,
        comment_repo=comment_repo,
        link_repo=link_repo,
        media_repo=media_repo,
        team_repo=team_repo,
        backer_repo=backer_repo,
        grant_repo=grant_repo,
        voice_repo=voice_repo,
        bounty_repo=bounty_repo,
        email_service=email_service,
        logo_dev_service=logo_dev_service,
        redis=redis,
    )
