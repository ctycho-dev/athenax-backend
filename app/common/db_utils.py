from sqlalchemy import Table, delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession


async def sync_association(
    session: AsyncSession,
    table: Table,
    owner_col: str,
    owner_id: int,
    target_col: str,
    new_ids: set[int],
) -> None:
    """Diff-based sync for a many-to-many association table.

    Fetches the current rows, then only inserts/deletes what changed.
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
