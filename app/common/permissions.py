from app.domain.user.schema import UserOutSchema
from app.enums.enums import UserRole
from app.exceptions.exceptions import ValidationError



def is_admin(current_user: UserOutSchema) -> bool:
    return current_user.role == UserRole.ADMIN


def is_owner(entity, current_user: UserOutSchema) -> bool:
    return entity.created_by_id is not None and entity.created_by_id == current_user.id


def assert_can_modify(entity, current_user: UserOutSchema) -> None:
    """Check if the current user is allowed to modify this resource (product, paper, lab, etc).

    Allowed if:
      - user is an admin, OR
      - user is the owner — meaning entity.created_by_id (whoever created it) matches current_user.id

    Raises ValidationError if neither — nothing is modified.
    """
    if is_admin(current_user):
        return
    if not is_owner(entity, current_user):
        raise ValidationError("You do not have permission to modify this resource")
