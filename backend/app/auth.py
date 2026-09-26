"""Token auth (M1): Single-User-Stufe, Rollen-Reserve fürs Portal.

* Ohne ``CHORMANAGER_API_TOKEN`` (Dev-Default): alles offen, Rolle
  ``chorleiter``.
* Mit Token: Reads bleiben offen, Writes brauchen
  ``Authorization: Bearer <token>`` (sonst 401).
* Gültiges Token ⇒ Rolle ``chorleiter``. Spätere Portal-Rollen
  (``vorstand``, ``saenger``, Analyse §3.4) hängen sich an
  :func:`current_role` / :func:`require_chorleiter` — die
  ``users``-Tabelle kommt mit dem Portal-Meilenstein, nicht hier.
"""
import os
from typing import Optional

from fastapi import Depends, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

ROLE_CHORLEITER = "chorleiter"
ROLE_ANONYMOUS = "anonymous"

_scheme = HTTPBearer(auto_error=False)


def configured_token() -> str:
    """Return the configured API token (empty = open dev mode)."""
    return os.environ.get("CHORMANAGER_API_TOKEN") or ""


def current_role(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(_scheme),
) -> str:
    """Resolve the caller role from the bearer token."""
    token = configured_token()
    if not token:
        return ROLE_CHORLEITER
    if (
        credentials is None
        or credentials.scheme.lower() != "bearer"
        or credentials.credentials != token
    ):
        raise HTTPException(
            status_code=401,
            detail="Unauthorized",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return ROLE_CHORLEITER


def require_chorleiter(
    role: str = Depends(current_role),
) -> str:
    """Dependency for write endpoints (403 for lesser roles)."""
    if role != ROLE_CHORLEITER:
        raise HTTPException(status_code=403, detail="Forbidden")
    return role
