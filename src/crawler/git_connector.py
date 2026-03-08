"""Git repository connector — clones a repo and indexes docs from a folder.

Supports public repos (no auth) and private repos (via token in URL).
Processes markdown, HTML, text, and other doc files found in the target path.
"""

from __future__ import annotations

import hashlib
import logging
import os
import shutil
import tempfile
from pathlib import Path

from src.common.models import Document
from src.crawler.file_processor import process_file

logger = logging.getLogger(__name__)

# File extensions we index
_DOC_EXTENSIONS = {
    ".md", ".mdx", ".markdown",
    ".txt", ".text", ".rst",
    ".html", ".htm",
    ".pdf", ".docx", ".pptx",
}


def crawl_git_repo(
    repo_url: str,
    branch: str,
    docs_path: str,
    source_id: str,
    tenant_id: str,
    token: str = "",
) -> list[Document]:
    """Clone a git repo and extract documents from a folder.

    Args:
        repo_url: HTTPS URL of the repository
        branch: Branch to checkout (default: main)
        docs_path: Subfolder to index (e.g., "docs", "." for root)
        source_id: KnowledgeMCP source identifier
        tenant_id: Owning tenant
        token: Optional PAT for private repos (injected into clone URL)
    """
    import subprocess

    tmpdir = tempfile.mkdtemp(prefix="knowledgemcp_git_")

    try:
        # Inject token if provided (for private repos)
        clone_url = repo_url
        if token and "github.com" in repo_url:
            clone_url = repo_url.replace("https://", f"https://x-access-token:{token}@")
        elif token and "gitlab.com" in repo_url:
            clone_url = repo_url.replace("https://", f"https://oauth2:{token}@")

        # Shallow clone for speed
        cmd = [
            "git", "clone",
            "--depth", "1",
            "--branch", branch,
            "--single-branch",
            clone_url,
            tmpdir,
        ]
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
            env={**os.environ, "GIT_TERMINAL_PROMPT": "0"},
        )

        if result.returncode != 0:
            logger.error("Git clone failed: %s", result.stderr)
            return []

        # Walk the docs folder
        docs_root = Path(tmpdir) / docs_path
        if not docs_root.exists():
            logger.warning("Docs path %s not found in repo", docs_path)
            # Fall back to repo root
            docs_root = Path(tmpdir)

        documents: list[Document] = []

        for filepath in sorted(docs_root.rglob("*")):
            if not filepath.is_file():
                continue
            if filepath.suffix.lower() not in _DOC_EXTENSIONS:
                continue
            # Skip hidden files and common non-doc directories
            rel = filepath.relative_to(Path(tmpdir))
            if any(part.startswith(".") or part in ("node_modules", "__pycache__", "venv") for part in rel.parts):
                continue

            try:
                file_bytes = filepath.read_bytes()
                content, metadata = process_file(file_bytes, filepath.name)

                if not content.strip():
                    continue

                rel_path = str(filepath.relative_to(Path(tmpdir)))
                page_url = f"{repo_url}/blob/{branch}/{rel_path}"

                documents.append(
                    Document(
                        doc_id=hashlib.sha256(f"{tenant_id}:{source_id}:{rel_path}".encode()).hexdigest(),
                        source_id=source_id,
                        tenant_id=tenant_id,
                        url=page_url,
                        title=metadata.get("title", filepath.stem),
                        content_markdown=content,
                        content_hash=hashlib.sha256(content.encode("utf-8")).hexdigest(),
                        metadata={
                            **metadata,
                            "source_kind": "git_repo",
                            "repo_url": repo_url,
                            "branch": branch,
                            "file_path": rel_path,
                        },
                    )
                )
            except Exception:
                logger.exception("Failed to process %s", filepath)
                continue

        logger.info("Indexed %d files from git repo %s (%s/%s)", len(documents), repo_url, branch, docs_path)
        return documents

    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)
