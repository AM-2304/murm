"""
Project management endpoints.
A project holds the seed material and produces one or more simulation runs.
"""

from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, HTTPException, Request, UploadFile
from pydantic import BaseModel

from murm.api.store import ProjectStore
from murm.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


class CreateProjectRequest(BaseModel):
    title: str
    seed_text: str = ""


@router.post("/")
async def create_project(body: CreateProjectRequest, request: Request) -> dict:
    store: ProjectStore = request.app.state.store
    project_id = await store.create_project(title=body.title)
    if body.seed_text:
        await store.update_project(project_id, seed_text=body.seed_text)
    return {"project_id": project_id, "title": body.title}


@router.get("/")
async def list_projects(request: Request) -> list[dict]:
    store: ProjectStore = request.app.state.store
    return await store.list_projects()


@router.get("/{project_id}")
async def get_project(project_id: str, request: Request) -> dict:
    store: ProjectStore = request.app.state.store
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail=f"Project {project_id} not found")
    return project


@router.post("/{project_id}/upload")
async def upload_seed_file(project_id: str, file: UploadFile, request: Request) -> dict:
    """
    Upload a seed document (PDF, DOCX, TXT) for a project.
    Stored to disk; text extraction happens during graph building.
    """
    store: ProjectStore = request.app.state.store
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    upload_dir = settings.data_dir / "projects" / project_id / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)

    dest = upload_dir / (file.filename or "upload.bin")
    content = await file.read()
    dest.write_bytes(content)

    current_files: list[str] = project.get("seed_files", [])
    current_files.append(str(dest.name))
    await store.update_project(project_id, seed_files=current_files)

    logger.info("Uploaded seed file %s to project %s", dest.name, project_id)
    return {"filename": dest.name, "size_bytes": len(content)}


@router.delete("/{project_id}")
async def delete_project(project_id: str, request: Request) -> dict:
    """
    Delete a project and all associated data from the database.
    Graph files and uploads on disk are removed separately via the data_dir.
    """
    store: ProjectStore = request.app.state.store
    project = await store.get_project(project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")

    import shutil
    project_dir = settings.data_dir / "projects" / project_id
    if project_dir.exists():
        shutil.rmtree(project_dir)

    from murm.graph.embedder import Embedder
    try:
        embedder = Embedder(settings.chroma_path, project_id)
        embedder.delete_collection()
    except Exception:
        pass

    await store.delete_project(project_id)
    logger.info("Deleted project %s and all associated runs", project_id)
    return {"deleted": project_id}
