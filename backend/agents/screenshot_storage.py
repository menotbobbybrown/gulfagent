"""
T23 — Store browser screenshots in Supabase Storage and link to task.

Bucket: gulfagent-screenshots (create in Supabase dashboard, public read)
Path:   {user_id}/{task_id}/step_{n:03d}.png
"""

from __future__ import annotations

import logging
import mimetypes
from pathlib import Path
from uuid import UUID

from supabase import Client, create_client

from config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

BUCKET = "gulfagent-screenshots"


def _get_client() -> Client:
    return create_client(settings.supabase_url_http, settings.supabase_service_key)


async def upload_screenshots(
    task_id: str,
    user_id: str,
    screenshot_paths: list[str],
) -> list[str]:
    """
    Upload a list of local screenshot paths to Supabase Storage.
    Returns list of public URLs (empty string for any that fail).
    """
    if not screenshot_paths:
        return []

    urls: list[str] = []

    try:
        client = _get_client()
        storage = client.storage.from_(BUCKET)
    except Exception as e:
        logger.error("Supabase storage init failed: %s", e)
        return [""] * len(screenshot_paths)

    for local_path in screenshot_paths:
        path_obj = Path(local_path)
        if not path_obj.exists():
            urls.append("")
            continue

        storage_key = f"{user_id}/{task_id}/{path_obj.name}"
        try:
            with open(path_obj, "rb") as f:
                data = f.read()

            storage.upload(
                path=storage_key,
                file=data,
                file_options={"content-type": "image/png", "upsert": "true"},
            )

            public_url_resp = storage.get_public_url(storage_key)
            # supabase-py returns str directly
            urls.append(str(public_url_resp))
            logger.debug("Uploaded screenshot: %s → %s", path_obj.name, public_url_resp)
        except Exception as e:
            logger.error("Failed to upload %s: %s", local_path, e)
            urls.append("")

    return urls


async def link_screenshots_to_task(
    session,  # AsyncSession
    task_id: str,
    user_id: str,
    screenshot_paths: list[str],
    steps_data: list[dict],
) -> list[str]:
    """
    Upload screenshots and patch the task's metadata.screenshots field.
    Returns list of public URLs.
    """
    from sqlalchemy import update
    from db.models import Task

    public_urls = await upload_screenshots(task_id, user_id, screenshot_paths)

    # Attach URLs back to steps_data
    for i, step in enumerate(steps_data):
        if i < len(public_urls):
            step["screenshot_url"] = public_urls[i]

    # Update task metadata
    await session.execute(
        update(Task)
        .where(Task.id == UUID(task_id))
        .values(metadata={"screenshots": public_urls, "steps": steps_data})
    )
    await session.commit()

    return public_urls
