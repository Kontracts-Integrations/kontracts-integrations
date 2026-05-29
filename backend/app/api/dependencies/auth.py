import logging
import time
from typing import Dict, Optional, Tuple

import httpx
from fastapi import HTTPException, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import settings

logger = logging.getLogger(__name__)

_bearer_scheme = HTTPBearer(auto_error=False)

# token -> (github_user_dict, expiry_monotonic)
_token_cache: Dict[str, Tuple[dict, float]] = {}
_CACHE_TTL = 300  # 5 minutes


def _get_cached(token: str) -> Optional[dict]:
    entry = _token_cache.get(token)
    if entry and entry[1] > time.monotonic():
        return entry[0]
    _token_cache.pop(token, None)
    return None


def _set_cached(token: str, user: dict) -> None:
    _token_cache[token] = (user, time.monotonic() + _CACHE_TTL)


async def verify_github_token(
    credentials: Optional[HTTPAuthorizationCredentials] = Security(_bearer_scheme),
) -> dict:
    """Validate a GitHub OAuth access token; return the GitHub user profile.

    In demo_mode the check is skipped entirely so local dev works without
    a real GitHub OAuth app.
    """
    if settings.demo_mode:
        return {"login": "demo", "id": 0}

    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = credentials.credentials

    cached = _get_cached(token)
    if cached:
        return cached

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2022-11-28",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get("https://api.github.com/user", headers=headers)

            if resp.status_code != 200:
                logger.warning("GitHub token validation failed (HTTP %s)", resp.status_code)
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid or expired GitHub token",
                    headers={"WWW-Authenticate": "Bearer"},
                )

            user: dict = resp.json()

            if settings.github_org:
                # Uses GET /orgs/{org}/members/{username} which returns 204 for public
                # members and 404 for non-members. Private org members who have chosen
                # to keep their membership private will also receive 404 and will be
                # incorrectly denied. Switching to /orgs/{org}/memberships/{username}
                # would fix this but requires an org admin token on the server side.
                membership = await client.get(
                    f"https://api.github.com/orgs/{settings.github_org}/members/{user['login']}",
                    headers=headers,
                )
                if membership.status_code != 204:
                    logger.warning(
                        "User %s is not a member of org %s", user.get("login"), settings.github_org
                    )
                    raise HTTPException(
                        status_code=status.HTTP_403_FORBIDDEN,
                        detail=f"Access restricted to members of the {settings.github_org} GitHub organisation",
                    )
    except httpx.HTTPError as exc:
        logger.error("GitHub API unreachable: %s", exc)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Unable to reach GitHub API for token validation",
        ) from exc

    _set_cached(token, user)
    logger.debug("Authenticated GitHub user: %s", user.get("login"))
    return user
