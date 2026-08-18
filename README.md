# Power Platform environment settings matrix (PoC)

Compares configuration across every Power Platform environment in a tenant. Authenticates
as a service principal (OAuth2 client credentials, no interactive sign-in), collects each
environment's settings and features, and renders a single self-contained HTML matrix:
**settings as rows, environments as columns**.

Useful for answering "why does this behave differently in UAT than in production?" without
clicking through the admin centre 30 times.

## Try it without a tenant

```powershell
python main.py --sample --open
```

Renders bundled demo data — no Azure, no credentials, no network. This is the fastest way
to see whether the tool is worth setting up.

The report supports: show/hide environments, filter by name/key/category/description, an
**only differences** toggle, a category filter, hover a setting for its description, a
light/system/dark theme switch, and highlighting of cells that deviate from the row's most
common value. Environments in a non-running state (`Disabled`, `AdminMode`, `Suspended`,
`Deleting`, `Deleted`, `Failed`, `NotSpecified`) are hidden on load; the environment
popover has an **Active** button next to All/None to restore that default.

## Prerequisites

| Tool | Needed for | Install |
| --- | --- | --- |
| Python 3.9+ | everything (stdlib only, no packages) | [python.org](https://www.python.org/downloads/) |
| PowerShell 7+ | the deploy scripts | `winget install Microsoft.PowerShell` |
| Azure CLI | creating the app registration | `winget install Microsoft.AzureCLI` |
| `Microsoft.PowerApps.Administration.PowerShell` | registering the management app | `Install-Module Microsoft.PowerApps.Administration.PowerShell -Scope CurrentUser` |
| Power Platform CLI (`pac`) | adding Dataverse application users | `dotnet tool install --global Microsoft.PowerApps.CLI.Tool` |

Roles you (the operator) need — the service principal cannot grant these to itself:

- **Power Platform Administrator** or **Global Administrator**, interactively, to register
  the app as a Power Platform management application.
- **Privileged Role Administrator** or **Global Administrator** to grant admin consent
  (the script falls back to printing a consent URL if you lack this).
- Admin rights on each environment where you add an application user.

## Setup

```powershell
az login --allow-no-subscriptions
pwsh -File deploy/Deploy-AppRegistration.ps1        # writes .env (gitignored)
```

This creates the app registration and secret and registers it as a **Power Platform
management application**, which is what grants the tenant-wide admin APIs. It does *not*
grant Dataverse data access.

For the Dataverse rows, add the app as an application user in each environment:

```powershell
python main.py --skip-dataverse --json out/data.json
pwsh -File deploy/Add-EnvironmentAppUsers.ps1 -FromReportJson out/data.json -DryRun
```

Drop `-DryRun` to apply. Environments without an application user are skipped gracefully
and flagged in their report column header.

Teardown: `pwsh -File deploy/Deploy-AppRegistration.ps1 -Teardown`

## Run

```powershell
python main.py --open
python main.py --max-envs 5 --skip-dataverse       # fast pass
python main.py --env-filter prod --json out/data.json
```

Writes `out/report.html` (override with `--out`) and prints `<n> settings x <m> environments`.

| Flag | Effect |
| --- | --- |
| `--out PATH` | report location (default `out/report.html`) |
| `--json PATH` | also dump the collected data as JSON |
| `--sample` | render bundled demo data, no network |
| `--env-file PATH` | credentials file (default `.env`) |
| `--env-filter TEXT` | only environments whose display name contains `TEXT` |
| `--max-envs N` | stop after the first N environments |
| `--skip-dataverse` / `--skip-ppapi` | skip a data source |
| `--workers N` | environments collected in parallel (default 6) |
| `--open` | open the report when done |

> **The generated report and JSON contain tenant configuration data** — tenant id, every
> environment name and Dataverse URL, security group ids, and the full settings posture.
> Treat them as internal. `out/`, `report.html` and `data.json` are gitignored; keep it
> that way.

## What gets collected

| Category | Source | Access needed |
| --- | --- | --- |
| Environment | BAP admin API `scopes/admin/environments` | management app registration |
| Managed Environment | `properties.governanceConfiguration` from the same call | same |
| Environment management settings | `api.powerplatform.com/environmentmanagement/.../settings` | management app or Power Platform RBAC role |
| Settings & features (Dataverse) | `settingdefinitions` + `organizationsettings` | application user |
| Feature control settings (Dataverse) | `featurecontrolsettings` — the `content` column is base64, decoded to JSON | application user |
| Organization table (Dataverse) | `organizations` (labels/descriptions from `EntityDefinitions`) | application user |
| OrgDBOrgSettings (Dataverse) | the `orgdborgsettings` XML column, parsed per key | application user |

Every source is best-effort: a failure degrades that environment to `partial`/`error` with
the reason shown on hover in its column header, rather than failing the run.

## Troubleshooting

| Symptom | Cause | Fix |
| --- | --- | --- |
| `HTTP 401/403` listing environments | the service principal is not a Power Platform management application | rerun `deploy/Deploy-AppRegistration.ps1` as a tenant admin |
| Column note *"no application user in this environment"* | no Dataverse application user | `deploy/Add-EnvironmentAppUsers.ps1` for that environment |
| Column note *"application user lacks a security role"* | app user exists without a role | assign a role with `-Role` |
| Column note *"no Dataverse database"* | Teams/database-less environment | expected — only the BAP and Power Platform API rows exist |
| Environment management settings return 403 | no Power Platform RBAC role assignment | assign *Power Platform reader* at tenant scope, or run with `--skip-ppapi` |

## Layout

| Path | Purpose |
| --- | --- |
| `main.py` | CLI entry point |
| `src/ppapi.py` | Token cache + HTTP with 429/Retry-After handling |
| `src/collect.py` | Environment + settings collection |
| `src/report.py` | HTML renderer (stdlib only, no external assets) |
| `src/sample_data.py` | Demo data for `--sample` |
| `deploy/Deploy-AppRegistration.ps1` | Creates/tears down the Entra app registration |
| `deploy/Add-EnvironmentAppUsers.ps1` | Adds the app as a Dataverse application user per environment |
| `tests/smoke_test.py` | Offline test of the collector — `python tests/smoke_test.py`, no Azure needed |

## PoC limitations

- Read-only. Nothing writes back to any environment.
- The Dataverse settings-framework tables are not documented on Microsoft Learn, so they
  are queried without `$select` and the columns are probed at runtime.
- `System Administrator` is the default role in `Add-EnvironmentAppUsers.ps1`; use a
  read-only custom role for anything beyond a PoC.
- Teardown removes the app registration (soft-deleted, recoverable for 30 days) but not the
  per-environment application users.

## Disclaimer

Proof of concept, provided as-is with no warranty or support. Not a Microsoft product and
not affiliated with or endorsed by Microsoft. Review it before running it against a
production tenant.

## License

[MIT](LICENSE)

