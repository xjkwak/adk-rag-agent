# Support KB — Reporting System Unauthorized Error

## Symptom

Users see **"Unauthorized"** or **HTTP 401** when accessing the Reporting System.

## Common causes

1. **Expired session** — SSO session timed out after 8 hours of inactivity
2. **Missing role** — User lacks `REPORT_VIEWER` or `REPORT_ADMIN` role in Production
3. **Wrong environment** — User credentials valid in Staging but not provisioned in Production
4. **Recent password change** — Active sessions invalidated; user must log in again

## Resolution steps

### Step 1: Refresh session
1. Log out completely from the SSO portal
2. Close all browser tabs for reporting.example.com
3. Log in again via `https://reporting.example.com/login`

### Step 2: Verify role assignment
1. Open the Access Management portal
2. Search for the user's email
3. Confirm `REPORT_VIEWER` role is assigned for **Production** environment
4. If missing, submit an access request via the IT Service Desk

### Step 3: Clear cache
1. Clear browser cache and cookies for reporting.example.com
2. Retry in a private/incognito window

## When to escalate

Escalate to support if:
- User has correct roles but still receives 401 in Production
- Multiple users affected simultaneously (possible service outage)
- Error persists after session refresh and role verification

## Workaround

Use the Staging environment at `https://staging-reporting.example.com` for read-only reports while Production access is restored. Staging data may be up to 24 hours behind Production.
