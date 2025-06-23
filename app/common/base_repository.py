from datetime import datetime
from typing import Optional, Type, Generic, TypeVar, Dict, Union, Any
from bson import ObjectId
from beanie import PydanticObjectId, Document
from pydantic import BaseModel

from app.exceptions import NotFoundError, DatabaseError
from app.domain.user.schema import UserOut
from app.domain.user.model import User


T = TypeVar('T', bound=Document)
C = TypeVar('C', bound=BaseModel)
S = TypeVar('S', bound=BaseModel)


class BaseRepository(Generic[T, S, C]):
    """
    Base repository class for MongoDB collections.

    This class provides common CRUD operations and can be extended by specific repository classes.
    """

    def __init__(
        self,
        collection: Type[T],
        default_schema: Type[S],
        create_schema: Type[C]
    ):
        """
        Initializes the BaseRepository with the collection and default schema.

        Args:
            collection (Type[T]): The MongoDB collection class.
            default_schema (Type[S]): The default Pydantic schema class.
        """
        self.collection = collection
        self.default_schema = default_schema
        self.create_schema = create_schema

    def _serialize(self, entity: Dict[str, Any]) -> Dict[str, Any]:
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

    async def get_by_id(self, _id: str) -> Optional[S]:
        """
        Retrieve an entity by its ID.

        Args:
            _id (str): The ID of the entity to retrieve.

        Returns:
            Optional[S]: The entity model if found, otherwise None.

        Raises:
            NotFoundError: If the entity with the specified ID is not found.
            DatabaseError: If there is an issue with the database operation.
        """
        try:
            entity = await self.collection.get(PydanticObjectId(_id))
            if not entity:
                raise NotFoundError(f"Entity with ID {_id} not found")

            entity_dict = self._serialize(entity.model_dump())
            return self.default_schema(**entity_dict)
        except NotFoundError as exc:
            raise exc
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve entity: {str(e)}") from e

    async def get_all(self, schema: Optional[Type[S]] = None) -> list[S]:
        """
        Retrieve all entities from the collection.

        Args:
            schema (Type[S]): The schema to use for serialization. If None, uses the default schema.

        Returns:
            list[S]: A list of entity models.

        Raises:
            DatabaseError: If there is an issue with the database operation.
        """
        try:
            entities = await self.collection.find().to_list()
            
            return [(schema or self.default_schema)(**self._serialize(entity.model_dump())) for entity in entities]
        except Exception as e:
            raise DatabaseError(f"Failed to retrieve all entities: {str(e)}") from e

    async def create(
        self,
        entity: C,
        schema: Optional[Type[S]] = None,
        current_user: Optional[User] = None
    ) -> S:
        """
        Create a new entity in the collection.

        Args:
            entity (T): The entity data to create.

        Returns:
            S: The created entity model.

        Raises:
            DatabaseError: If there is an issue with the database operation.
        """
        try:
            if isinstance(entity, BaseModel):
                entity = self.collection(**entity.model_dump())
                if current_user:
                    if hasattr(entity, 'created_by'):
                        entity.created_by = current_user
                    if hasattr(entity, 'updated_by'):
                        entity.updated_by = current_user

            created_entity = await self.collection.create(entity)
            created_entity_dict = self._serialize(created_entity.model_dump())

            return (schema or self.default_schema)(**created_entity_dict)
        except Exception as e:
            raise DatabaseError(f"Failed to create entity: {str(e)}") from e

    async def update(
        self,
        _id: str,
        update_data: Union[Dict[str, Any], BaseModel],
        schema: Optional[Type[S]] = None,
        current_user: Optional[User] = None
    ) -> S:
        """
        Update an entity in the collection.

        Args:
            _id (str): The ID of the entity to update.
            update_data (Union[Dict[str, Any], BaseModel]): The data to update. Can be a dictionary or a Pydantic schema.
            schema (Optional[Type[S]]): The schema to use for serialization. If None, uses the default schema.
            current_user (Optional[User]): The current user performing the update.

        Returns:
            S: The updated entity model.

        Raises:
            NotFoundError: If the entity with the specified ID is not found.
            DatabaseError: If there is an issue with the database operation.
        """
        try:
            if isinstance(update_data, BaseModel):
                update_data = update_data.model_dump(
                    exclude_unset=True,
                    exclude={'created_at', 'id'}
                )

            entity = await self.collection.get(PydanticObjectId(_id))
            if not entity:
                raise NotFoundError(f"Entity with ID {_id} not found")

            for key, value in update_data.items():
                if key not in {'created_at', 'id'}:
                    setattr(entity, key, value)

            if hasattr(entity, 'updated_at'):
                entity.updated_at = datetime.now()

            if current_user and hasattr(entity, 'updated_by'):
                entity.updated_by = current_user

            await entity.save()

            updated_entity_dict = self._serialize(entity.model_dump())
            return (schema or self.default_schema)(**updated_entity_dict)
        except NotFoundError as e:
            raise e
        except Exception as e:
            raise DatabaseError(f"Failed to update entity: {str(e)}") from e

    async def delete_by_id(self, _id: str) -> None:
        """
        Delete an entity by its ID.

        Args:
            _id (str): The ID of the entity to delete.

        Raises:
            NotFoundError: If the entity with the specified ID is not found.
            DatabaseError: If there is an issue with the database operation.
        """
        try:
            entity = await self.collection.get(PydanticObjectId(_id))
            if not entity:
                raise NotFoundError(f"Entity with ID {_id} not found")
            await entity.delete()
        except NotFoundError as e:
            raise e
        except Exception as e:
            raise DatabaseError(f"Failed to delete entity: {str(e)}") from e