# Local authentication contract

The foundation now provides a first-account setup endpoint, PBKDF2-SHA256 password storage, server-side sessions, HttpOnly SameSite cookies, CSRF tokens, login failure lockout, logout, and the current-user endpoint.

The automated authentication suite verifies the setup-only bootstrap, password/session boundary, CSRF rejection, API-key scope enforcement, revocation, secure-cookie deployment mode, and account lockout after five failed passwords. The local password implementation is PBKDF2-SHA256 with a per-password random salt and 310,000 iterations; no claim is made that this selects the only acceptable password KDF for every deployment.

`POST /api/auth/setup` is accepted only while no users exist. It creates the initial local administrator and then becomes unavailable. `POST /api/auth/login` returns a CSRF token and sets the `docplatform_session` cookie. Review corrections and review-state changes require both the session and `X-CSRF-Token`.

For compatibility with the unauthenticated local foundation, review mutations remain open only while the users table is empty. Once the initial account exists, API-side session enforcement is active. Set `secure_cookies=true` when the service is reached through an HTTPS reverse proxy; the local default remains false for the loopback HTTP Compose endpoint. Broader role/scoped API-key authorization, rate-limit infrastructure beyond account lockout, and a login/review UI remain incomplete.

After setup/login, administrators can create, list, and revoke API keys through `/api/auth/api-keys`. The plaintext key is returned only at creation. Keys carry `read`, `render`, or `admin` scopes and are stored as SHA-256 digests. A `read` key can list templates, upload and extract documents, and read results; it cannot create or run render jobs or generate from approved data. A `render` key can submit/run render jobs and generate from approved data. Revoked or insufficient-scope keys are rejected. Review mutations still require a browser session and CSRF token.
