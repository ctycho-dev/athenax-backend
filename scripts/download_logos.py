"""
Download all product logos from R2 into local per-project folders, named by slug.

Existing files are skipped by default (pass --overwrite to replace them).

Usage:
    PYTHONPATH=. python scripts/download_logos.py [--output-dir ./logos] [--overwrite] [--dry-run] [--concurrency N]
"""

import argparse
import asyncio
import logging
from pathlib import Path

import httpx
from sqlalchemy import select

from app.common.storage import R2StorageService
from app.database.connection import db_manager
from app.domain.product.model import Product
from app.domain.user.model import User  # noqa: F401 — registers 'users' table in metadata

logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.getLogger(__name__)

DEFAULT_CONCURRENCY = 5


async def _fetch_candidates(session) -> list[tuple[str, str]]:
    """(slug, logo_key) for non-deleted products that have a logo set."""
    result = await session.execute(
        select(Product.slug, Product.logo).where(
            Product.deleted_at.is_(None),
            Product.logo.is_not(None),
        )
    )
    return [(row.slug, row.logo) for row in result.all()]


async def _process_one(
    slug: str,
    logo_key: str,
    output_dir: Path,
    storage: R2StorageService,
    client: httpx.AsyncClient,
    overwrite: bool,
    dry_run: bool,
) -> str:
    """Returns one of: 'downloaded', 'skipped_existing', 'error'."""
    ext = Path(logo_key).suffix or ".webp"
    dest_dir = output_dir / slug
    dest_path = dest_dir / f"logo{ext}"

    if dest_path.exists() and not overwrite:
        log.info("  SKIP    %-30s already exists at %s", slug, dest_path)
        return "skipped_existing"

    if dry_run:
        log.info("  WOULD GET %-28s -> %s", slug, dest_path)
        return "downloaded"

    url = storage.build_url(logo_key)
    try:
        response = await client.get(url)
        response.raise_for_status()
    except httpx.HTTPError as exc:
        log.warning("  ERROR   %-30s %s: %s", slug, url, exc)
        return "error"

    dest_dir.mkdir(parents=True, exist_ok=True)
    dest_path.write_bytes(response.content)
    log.info("  SAVED   %-30s -> %s", slug, dest_path)
    return "downloaded"


async def download_logos(output_dir: Path, overwrite: bool, dry_run: bool, concurrency: int) -> None:
    db_manager.init_engine()
    storage = R2StorageService()

    async with db_manager.session_scope() as session:
        candidates = await _fetch_candidates(session)

    await db_manager.close()

    log.info("%d product(s) with a logo set\n", len(candidates))
    if not candidates:
        return

    semaphore = asyncio.Semaphore(concurrency)

    async with httpx.AsyncClient(timeout=30.0) as client:

        async def _bounded(slug: str, logo_key: str) -> str:
            async with semaphore:
                return await _process_one(slug, logo_key, output_dir, storage, client, overwrite, dry_run)

        results = await asyncio.gather(*(_bounded(slug, logo_key) for slug, logo_key in candidates))

    counts = {outcome: results.count(outcome) for outcome in set(results)}
    log.info(
        "\nDone — downloaded: %d  skipped_existing: %d  error: %d",
        counts.get("downloaded", 0),
        counts.get("skipped_existing", 0),
        counts.get("error", 0),
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Download all product logos into per-slug folders")
    parser.add_argument("--output-dir", type=Path, default=Path("./logos"), help="Root folder to save logos into")
    parser.add_argument("--overwrite", action="store_true", help="Replace files that already exist")
    parser.add_argument("--dry-run", action="store_true", help="Preview without downloading or writing files")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY, help="Max concurrent downloads")
    args = parser.parse_args()
    asyncio.run(
        download_logos(
            output_dir=args.output_dir,
            overwrite=args.overwrite,
            dry_run=args.dry_run,
            concurrency=args.concurrency,
        )
    )
