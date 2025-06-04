from typing import Any
from bson import ObjectId


def serialize(entity: dict[str, Any]) -> dict[str, Any]:
    """
    Serialize the entity by converting ObjectId fields to strings.

    Args:
        entity (Dict[str, Any]): The entity to serialize.

    Returns:
        Dict[str, Any]: The serialized entity.
    """
    serialized_entity = {}
    for key, value in entity.items():
        if isinstance(value, ObjectId):
            serialized_entity[key] = str(value)
        else:
            serialized_entity[key] = value
    return serialized_entity
