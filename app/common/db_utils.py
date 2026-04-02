from sqlalchemy import Table, delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession


async def sync_categories(
    session: AsyncSession,
    category_repo,
    table: Table,
    owner_col: str,
    owner_id: int,
    category_ids: list[int],
) -> None:
    """Validate that all category IDs exist, then sync the association table."""
    if category_ids:
        await category_repo.assert_exist(session, category_ids)
    await sync_association(session, table, owner_col, owner_id, "category_id", set(category_ids))


async def sync_association(
    session: AsyncSession,
    table: Table,
    owner_col: str,
    owner_id: int,
    target_col: str,
    new_ids: set[int],
) -> None:
    """Sync a many-to-many association table by only inserting/deleting what changed.

    Example: product has categories [1, 2, 3], user sends [2, 3, 4]
      - inserts 4  (new)
      - deletes 1  (removed)
      - leaves 2, 3 untouched (preserves their timestamps, avoids unnecessary writes)
    """
    result = await session.execute(
        select(table.c[target_col]).where(table.c[owner_col] == owner_id)
    )
    existing_ids = {row[0] for row in result.all()}

    to_add = new_ids - existing_ids
    to_remove = existing_ids - new_ids

    if to_remove:
        await session.execute(
            delete(table).where(
                table.c[owner_col] == owner_id,
                table.c[target_col].in_(to_remove),
            )
        )
    if to_add:
        await session.execute(
            insert(table),
            [{owner_col: owner_id, target_col: cid} for cid in to_add],
        )
