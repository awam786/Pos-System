from __future__ import annotations

from app.models import Role, User
from app.permissions import Permission, role_has_permission


def has_permission(
    user: User,
    permission: Permission | str,
) -> bool:
    if user.is_super_admin:
        return True

    if user.role == Role.OWNER:
        return True

    return role_has_permission(
        user.role,
        permission,
    )


def require_permission(
    user: User,
    permission: Permission | str,
) -> None:
    if not has_permission(user, permission):
        permission_name = (
            permission.value
            if isinstance(permission, Permission)
            else str(permission)
        )

        from fastapi import HTTPException, status

        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=f"Permission required: {permission_name}",
        )
