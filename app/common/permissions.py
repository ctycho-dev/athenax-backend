from app.domain.user.schema import UserOutSchema
from app.enums.enums import UserRole
from app.exceptions.exceptions import ValidationError


def assert_can_modify(entity, current_user: UserOutSchema) -> None:
    """Check if the current user is allowed to modify this resource (product, paper, lab, etc).

    Allowed if:
      - user is an admin, OR
      - user is the owner — meaning entity.user_id (whoever created it) matches current_user.id

    Raises ValidationError if neither — nothing is modified.
    """
    if current_user.role == UserRole.ADMIN:
        return
    if entity.user_id is None or entity.user_id != current_user.id:
        raise ValidationError("You do not have permission to modify this resource")
