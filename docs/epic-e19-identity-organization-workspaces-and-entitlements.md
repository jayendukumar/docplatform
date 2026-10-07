# E19 — Identity, organization workspaces and entitlement-aware template access (proposed scope addition)

This epic extends the original 15-epic backlog. `docs/epics.md` remains generated from the supplied DOCX and is not rewritten. It complements E3 template management, E7 API authentication, E11 identity/security and E15 hosted organization management.

## Goal

Make the homepage a safe starting point for a signed-in user: their own templates appear first, followed by templates in workspaces they are entitled to access, while the large starter gallery remains an explicitly browsable catalog. Organization and sub-organization workspaces are isolated by API authorization, with a flexible entitlement model ready for SSO/SCIM and future paid capabilities.

## Proposed stories

| ID | Persona / outcome | Acceptance direction |
| --- | --- | --- |
| E19-01 | Owner: see My Templates first | The homepage orders My Templates before organization templates and the starter gallery; My Templates is limited to the signed-in user's owned templates. |
| E19-02 | Owner: browse large collections safely | Organization templates are paged/limited with an explicit load-more action; the starter gallery is category-based and does not infinite-scroll the entire catalog. |
| E19-03 | Admin: provision an organization workspace | Onboarding creates an organization and dedicated default workspace; sub-organizations can receive separate workspaces and are not visible outside authorized memberships. |
| E19-04 | Admin: manage workspace entitlements | Users may have access to one or more organizations/workspaces; admin and super-admin roles can see all workspaces in their organization. Entitlements are represented as versioned, extensible data rather than hard-coded plan checks. |
| E19-05 | Owner: use local login, guest access and sign-up | The default auth surface offers username/password, SSO placeholder and guest entry. Sign-up accepts an email and creates a restricted pending/guest account until a configured verification or invitation flow exists. |
| E19-06 | Admin: prepare for enterprise identity | SSO discovery/start/callback contracts are present but no provider or network egress is enabled by default; authorization claims map to organizations/workspaces through an explicit adapter boundary. |
| E19-07 | Ops: remove exact template duplicates | A one-time, deterministic cleanup identifies templates with identical canonical definitions, retains the oldest stable record, and records aliases/counts without deleting distinct versions or near-duplicates. |

## Initial sequencing

1. Introduce organization, workspace, membership, ownership and entitlement persistence with a migration and backfill.
2. Add API-side workspace authorization and paged template listing.
3. Add deterministic exact-duplicate audit/cleanup tooling and run it only against verified duplicate groups.
4. Reorder the homepage and add login/guest/sign-up/SSO-placeholder states.

## Non-goals for this slice

Real SAML/OIDC provider integration, email delivery/verification, SCIM provisioning, billing enforcement, cross-tenant hosting isolation certification, and a complete admin management console remain follow-up work. SSO placeholders must not imply that an external identity provider is configured.
