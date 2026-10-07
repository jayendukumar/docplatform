# Fictitious identity seed

The explicit seed creates ten fictitious organizations. Each organization receives one workspace and ten member accounts: one admin and nine members. It also creates ten individual accounts with no organization or workspace membership.

Run from the repository root with the database available:

```powershell
docker compose run --rm web python /app/scripts/seed_demo_identity.py --apply
```

The command is idempotent and does not overwrite existing passwords. It prints a redacted summary and writes the demo credential manifest only when `--credentials-report` is explicitly supplied. All addresses use `.test` domains and must not be used for real mail.

Default demo passwords:

- Organization admins: `OrgAdmin-2026!`
- Organization members and individual accounts: `DemoUser-2026!`

These credentials are for local demonstrations only. Replace or remove them before any shared deployment.
