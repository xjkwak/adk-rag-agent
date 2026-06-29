"""Tenant profiles: instruction, corpus, and bundled assets."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .aegis_instruction import AEGIS_INSTRUCTION
from .amtech_instruction import AMTECH_INSTRUCTION
from .peakrock_instruction import PEAKROCK_INSTRUCTION

_REPO_ROOT = Path(__file__).resolve().parent.parent

DEFAULT_TENANT_ID = "peakrock"


@dataclass(frozen=True)
class TenantProfile:
    id: str
    label: str
    description: str
    default_corpus: str
    assets_dir: Path
    instruction: str

    def asset_files(self) -> list[str]:
        if not self.assets_dir.is_dir():
            return []
        return sorted(
            p.name
            for p in self.assets_dir.iterdir()
            if p.is_file() and not p.name.startswith(".")
        )

    def to_summary_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "label": self.label,
            "description": self.description,
            "default_corpus": self.default_corpus,
            "assets_path": str(self.assets_dir.relative_to(_REPO_ROOT)),
            "asset_files": self.asset_files(),
        }

    def to_profile_dict(self) -> dict[str, Any]:
        data = self.to_summary_dict()
        data["instruction"] = self.instruction.strip()
        return data


TENANTS: dict[str, TenantProfile] = {
    "peakrock": TenantProfile(
        id="peakrock",
        label="Peak Rock Capital",
        description=(
            "Engineering Intelligence Oracle — technical due diligence "
            "over governance SOPs and production C#/SQL."
        ),
        default_corpus="peakrock-demo",
        assets_dir=_REPO_ROOT / "assets" / "PeakRock",
        instruction=PEAKROCK_INSTRUCTION,
    ),
    "amtech": TenantProfile(
        id="amtech",
        label="Amtech / CoderoadERP",
        description=(
            "CoderoadERP AI Support Copilot — operational support, "
            "KB self-service, and Jira intake."
        ),
        default_corpus="amtech-demo",
        assets_dir=_REPO_ROOT / "assets" / "Amtech",
        instruction=AMTECH_INSTRUCTION,
    ),
    "aegis": TenantProfile(
        id="aegis",
        label="Aegis Manufacturing",
        description=(
            "Aegis Manufacturing Oracle — MES compliance, IPC standards, "
            "and production code gap analysis."
        ),
        default_corpus="aegis-demo",
        assets_dir=_REPO_ROOT / "assets" / "aegis",
        instruction=AEGIS_INSTRUCTION,
    ),
}


def list_tenant_summaries() -> list[dict[str, Any]]:
    return [t.to_summary_dict() for t in TENANTS.values()]


def get_tenant(tenant_id: str) -> TenantProfile:
    key = tenant_id.strip().lower()
    if key not in TENANTS:
        raise ValueError(f"Unknown tenant: {tenant_id!r}")
    return TENANTS[key]


def resolve_tenant_id(tenant_id: str | None) -> str:
    if not tenant_id:
        return DEFAULT_TENANT_ID
    key = tenant_id.strip().lower()
    if key not in TENANTS:
        return DEFAULT_TENANT_ID
    return key


def tenant_default_instruction(tenant_id: str) -> str:
    return get_tenant(tenant_id).instruction.strip()


def seed_tenant_corpus(
    tenant_id: str,
    *,
    incremental: bool = False,
) -> dict[str, Any]:
    """Create or refresh the tenant corpus from bundled assets."""
    profile = get_tenant(tenant_id)
    asset_names = profile.asset_files()
    if not asset_names:
        return {
            "status": "error",
            "message": (
                f"No files found in {profile.assets_dir.relative_to(_REPO_ROOT)}"
            ),
        }

    from .config import USE_LOCAL_RAG

    if not USE_LOCAL_RAG:
        return {
            "status": "error",
            "message": "Tenant seeding requires USE_LOCAL_RAG=1 in knowledge_hub/.env",
        }

    from .local_rag import store as local_store

    class _ToolContext:
        def __init__(self) -> None:
            self.state: dict[str, Any] = {}

    ctx = _ToolContext()
    paths = [str(profile.assets_dir / name) for name in asset_names]
    registry = local_store._load_registry()
    entry = local_store._find_corpus_entry(
        registry,
        display_name=profile.default_corpus,
    )

    if entry and not incremental:
        deleted = local_store.delete_corpus_dict(entry["resource_name"], ctx)
        if deleted.get("status") != "success":
            return {
                "status": "error",
                "message": deleted.get("message", "Failed to refresh corpus"),
            }
        entry = None

    if not entry:
        created = local_store.create_corpus_dict(profile.default_corpus, ctx)
        if created.get("status") not in ("success", "info"):
            return {
                "status": "error",
                "message": created.get("message", "Failed to create corpus"),
            }
        resource_name = created["corpus_name"]
    else:
        resource_name = entry["resource_name"]

    result = local_store.import_paths_dict(
        resource_name,
        paths,
        ctx,
        skip_existing=incremental,
    )
    corpus_id = local_store._corpus_id_from_resource(resource_name)
    collection = local_store._get_collection(corpus_id)
    chunk_count = collection.count()

    return {
        "status": result.get("status", "error"),
        "message": result.get("message", ""),
        "tenant": profile.id,
        "corpus_name": profile.default_corpus,
        "files_added": int(result.get("files_added", 0)),
        "files_skipped": int(result.get("files_skipped", 0)),
        "chunk_count": chunk_count,
        "asset_files": asset_names,
    }
