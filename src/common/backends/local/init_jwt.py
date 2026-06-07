"""Auto-generate a JWT secret on first run in local mode.

Run by the admin container's startup hook before uvicorn binds. If
JWT_SECRET_KEY is already set in the environment, this is a no-op.
Otherwise we read/write ``LOCAL_DATA_DIR/jwt.key`` so the same secret
is used across restarts and across the admin/mcp/worker processes.
"""

from __future__ import annotations

import os
import secrets
from pathlib import Path

from src.common.config import get_config


def ensure_jwt_secret() -> str:
    """Return the JWT secret, creating one in LOCAL_DATA_DIR if missing."""
    if os.environ.get("JWT_SECRET_KEY"):
        return os.environ["JWT_SECRET_KEY"]
    cfg = get_config()
    if cfg.backend != "local":
        # In AWS mode we require an explicit secret (per existing auth.py)
        return ""
    base = Path(cfg.local_data_dir).expanduser().resolve()
    base.mkdir(parents=True, exist_ok=True)
    key_path = base / "jwt.key"
    if key_path.exists():
        secret = key_path.read_text().strip()
    else:
        secret = secrets.token_urlsafe(64)
        key_path.write_text(secret)
        try:
            os.chmod(key_path, 0o600)
        except Exception:
            pass
    os.environ["JWT_SECRET_KEY"] = secret
    # Settings is frozen; the live config object already has empty secret.
    # Clear the cache so the next get_config() picks up the new env.
    from src.common.config import get_config as _g
    _g.cache_clear()
    import src.common.config as _cfg_mod
    _cfg_mod.settings = _g()
    return secret
