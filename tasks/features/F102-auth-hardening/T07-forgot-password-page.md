# T07 -- Admin Password Reset UI + API Endpoint

**Wave:** 2
**Depends on:** T02 (CLI reset-password), T04 (error codes)
**Estimated effort:** small

## User Story

As an admin, I want to reset a user's password from the admin panel in
the web UI so that I don't need CLI access to help a user who forgot
their password.

## What to Build

### 1. Backend: Admin reset-password endpoint

Add to `src/api/routers/admin.py`:

```python
@router.post("/users/{user_id}/reset-password", summary="Reset a user's password")
def admin_reset_password(
    user_id: int,
    user: User = Depends(require_admin),
    repo: Repository = Depends(get_db),
):
    """Generate a temporary password for the specified user.

    Sets password_expires_at to 24 hours from now, forcing the user
    to change their password on next login.
    """
    target = repo.get_user_by_id(user_id)
    if not target:
        raise api_error(404, ErrorCode.RESOURCE_NOT_FOUND, "User not found")

    import secrets
    from datetime import datetime, timedelta
    from src.auth.passwords import hash_password

    temp_password = secrets.token_urlsafe(9)
    pw_hash = hash_password(temp_password)
    expires_at = datetime.now() + timedelta(hours=24)

    repo.update_user(user_id, password_hash=pw_hash, password_expires_at=expires_at)

    return success_response(data={
        "user_id": user_id,
        "email": target.email,
        "temporary_password": temp_password,
        "expires_at": expires_at.isoformat(),
    })
```

### 2. Frontend: Admin reset password section

Add a "Reset Password" action to the admin user management page
(`frontend/src/pages/AdminPage.tsx` or wherever user management lives).

UI elements:
- A "Reset Password" button next to each user row in the admin user list.
- Clicking it shows a confirmation dialog: "Generate a temporary password
  for {email}? The user will be required to change it on next login."
- On confirm, call `POST /api/v1/admin/users/{id}/reset-password`.
- Display the temporary password in a copyable field with a "Copy"
  button. Show a warning: "Save this password -- it will not be shown
  again."
- Show the expiry time.

### 3. Pydantic schema

Add to `src/api/schemas/auth.py`:

```python
class ResetPasswordResponse(BaseModel):
    user_id: int
    email: str
    temporary_password: str
    expires_at: str
```

### 4. Frontend API function

Add to the appropriate API module:

```typescript
export async function adminResetPassword(userId: number): Promise<ApiResponse<{
  user_id: number;
  email: string;
  temporary_password: string;
  expires_at: string;
}>> {
  const resp = await fetch(`/api/v1/admin/users/${userId}/reset-password`, {
    method: "POST",
    headers: authHeaders(),
  });
  return resp.json();
}
```

## Dev Notes

- The admin endpoint reuses the same logic as the CLI command (T02) but
  exposed via HTTP. Consider extracting the shared logic into a service
  function if the CLI was implemented inline.
- Admin-only: protected by `require_admin` dependency.
- The temporary password is returned in the response body (not emailed).
  The admin must communicate it to the user out-of-band.
- This is intentionally NOT a self-service "forgot password" flow. There
  is no public-facing reset endpoint. Only admins can trigger resets.

## Testing

### Backend tests (`tests/api/test_admin_reset_password.py`)

1. Test admin can reset another user's password -- returns temp password.
2. Test non-admin gets 403.
3. Test resetting non-existent user returns 404 with `RESOURCE_NOT_FOUND`.
4. Test that the user's `password_expires_at` is set after reset.
5. Test that the temp password works for login but triggers
   `password_expired: true`.

### Frontend tests

6. Test "Reset Password" button renders for each user row.
7. Test confirmation dialog appears on click.
8. Test successful reset shows temp password + copy button.
9. Test error state displays error message.

Expected: ~8-10 tests total.
