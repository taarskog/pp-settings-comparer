"""Realistic sample data for the environment settings report.

Mirrors the contract produced by :func:`collect.collect` and consumed by
:func:`report.render_html` - same categories, same key prefixes, same
ordering. Every name, GUID and URL is fictional.
"""

from __future__ import annotations

import json

from collect import (
    CAT_ENV,
    CAT_FCS,
    CAT_FEATURES,
    CAT_MANAGED,
    CAT_ORG,
    CAT_ORGDB,
    CAT_PPAPI,
    CATEGORY_ORDER,
)

GENERATED_UTC = "2026-08-17T10:00:00Z"
TENANT_ID = "0a1b2c3d-4e5f-4a6b-8c7d-9e0f1a2b3c4d"

ENVIRONMENTS = [
    {
        "id": "Default-8a1f2c31-4d0e-4f6b-9c7a-11b2c3d4e5f6",
        "name": "Contoso (default)",
        "type": "Default",
        "region": "europe",
        "url": "https://contoso.crm4.dynamics.com/",
        "state": "Ready",
        "status": "ok",
        "statusMessage": None,
    },
    {
        "id": "2b7e9a44-5c31-4a82-8f10-6d9e0a1b2c3d",
        "name": "Contoso Production",
        "type": "Production",
        "region": "europe",
        "url": "https://contoso-prod.crm4.dynamics.com/",
        "state": "Ready",
        "status": "ok",
        "statusMessage": None,
    },
    {
        "id": "3c8f0b55-6d42-4b93-9021-7e0f1b2c3d4e",
        "name": "Contoso UAT",
        "type": "Sandbox",
        "region": "europe",
        "url": "https://contoso-uat.crm4.dynamics.com/",
        "state": "Ready",
        "status": "ok",
        "statusMessage": None,
    },
    {
        "id": "4d901c66-7e53-4ca4-a132-8f102c3d4e5f",
        "name": "Contoso Test",
        "type": "Sandbox",
        "region": "europe",
        "url": "https://contoso-test.crm4.dynamics.com/",
        "state": "Ready",
        "status": "partial",
        "statusMessage": "Dataverse: 429 Too Many Requests (throttled after 3 retries).",
    },
    {
        "id": "5ea12d77-8f64-4db5-b243-90213d4e5f60",
        "name": "Contoso Dev",
        "type": "Sandbox",
        "region": "europe",
        "url": "https://contoso-dev.crm4.dynamics.com/",
        "state": "AdminMode",
        "status": "ok",
        "statusMessage": None,
    },
    {
        "id": "6fb23e88-9075-4ec6-c354-a1324e5f6071",
        "name": "Fabrikam Sales (US)",
        "type": "Production",
        "region": "unitedstates",
        "url": "https://fabrikam-sales.crm.dynamics.com/",
        "state": "Ready",
        "status": "ok",
        "statusMessage": None,
    },
    {
        "id": "70c34f99-a186-4fd7-d465-b2435f607182",
        "name": "Adventure Works Trial",
        "type": "Trial",
        "region": "unitedstates",
        "url": "https://adventureworks-trial.crm.dynamics.com/",
        "state": "Disabled",
        "status": "ok",
        "statusMessage": None,
    },
    {
        "id": "81d450aa-b297-40e8-e576-c354607182a3",
        "name": "Northwind Regulated",
        "type": "Production",
        "region": "germany",
        "url": "https://northwind-reg.crm.microsoftdynamics.de/",
        "state": "Ready",
        "status": "error",
        "statusMessage": "Access denied: caller is not a System Administrator in this environment.",
    },
]

ENV_IDS = [e["id"] for e in ENVIRONMENTS]


def _val(raw, source):
    """Same rendering rule as :func:`collect._display`."""
    if isinstance(raw, bool):
        display = "Yes" if raw else "No"
    elif isinstance(raw, (dict, list)):
        display = json.dumps(raw, sort_keys=True, separators=(",", ":"))
    else:
        display = str(raw)
    return {"display": display, "raw": raw, "source": source}


def _setting(key, category, name, description, per_env, source="value"):
    """Build a setting row.

    ``per_env`` holds one raw value per entry of :data:`ENVIRONMENTS`. ``None``
    means the collector produced no row for that environment - either the source
    was unreadable or the value was empty, which :func:`collect._row` drops.
    """
    values = {}
    for env_id, raw in zip(ENV_IDS, per_env):
        if raw is None or raw == "":
            continue
        values[env_id] = _val(raw, source)
    return {
        "key": key,
        "category": category,
        "name": name,
        "description": description,
        "values": values,
    }


ONBOARDING_MARKDOWN = (
    "## Welcome to the Contoso Power Platform\n\n"
    "Before you build here, please read the [maker handbook]"
    "(https://intranet.contoso.com/power-platform/handbook). A few ground rules:\n\n"
    "1. **Name your solutions** `con_<team>_<workload>` so the CoE can attribute them.\n"
    "2. **Never store customer data in a personal environment** - request a project "
    "environment through the Power Platform request form instead.\n"
    "3. **Connectors outside the approved list are blocked by DLP.** If you need one, "
    "raise a request and include the business justification plus the data classes involved.\n"
    "4. **Solution checker runs on every import.** Anything with a High finding is "
    "rejected automatically; fix the finding rather than requesting an exception.\n"
    "5. Apps with no run in 90 days are archived, and the owner is notified two weeks "
    "in advance. Contact the CoE team at powerplatform@contoso.com with any questions."
)

_ROWS = [
    # --------------------------------------------------------------- env: (BAP)
    _setting(
        "env:Azure region",
        CAT_ENV,
        "Azure region",
        None,
        ["westeurope", "westeurope", "westeurope", "westeurope", "westeurope", "westus", "westus", None],
    ),
    _setting(
        "env:Database type",
        CAT_ENV,
        "Database type",
        None,
        [
            "CommonDataService", "CommonDataService", "CommonDataService", "CommonDataService",
            "CommonDataService", "CommonDataService", "CommonDataService", None,
        ],
    ),
    _setting(
        "env:Dataverse URL",
        CAT_ENV,
        "Dataverse URL",
        None,
        [
            "https://contoso.crm4.dynamics.com/",
            "https://contoso-prod.crm4.dynamics.com/",
            "https://contoso-uat.crm4.dynamics.com/",
            "https://contoso-test.crm4.dynamics.com/",
            "https://contoso-dev.crm4.dynamics.com/",
            "https://fabrikam-sales.crm.dynamics.com/",
            "https://adventureworks-trial.crm.dynamics.com/",
            None,
        ],
    ),
    _setting(
        "env:Dataverse state",
        CAT_ENV,
        "Dataverse state",
        None,
        ["Ready", "Ready", "Ready", "Ready", "AdminMode", "Ready", "Disabled", None],
    ),
    _setting(
        "env:Dataverse version",
        CAT_ENV,
        "Dataverse version",
        None,
        [
            "9.2.25081.00214", "9.2.25081.00214", "9.2.25082.00107", "9.2.25082.00107",
            "9.2.25082.00107", "9.2.25081.00214", "9.2.25082.00107", None,
        ],
    ),
    _setting(
        "env:Domain name",
        CAT_ENV,
        "Domain name",
        None,
        [
            "contoso", "contoso-prod", "contoso-uat", "contoso-test",
            "contoso-dev", "fabrikam-sales", "adventureworks-trial", None,
        ],
    ),
    _setting(
        "env:Environment group id",
        CAT_ENV,
        "Environment group id",
        None,
        [
            None, "9f3d5b71-6c28-4e14-a0d9-2f7b8c1e4a55", None, None,
            None, "9f3d5b71-6c28-4e14-a0d9-2f7b8c1e4a55", None, None,
        ],
    ),
    _setting(
        "env:Environment type (SKU)",
        CAT_ENV,
        "Environment type (SKU)",
        None,
        ["Default", "Production", "Sandbox", "Sandbox", "Sandbox", "Production", "Trial", None],
    ),
    _setting(
        "env:Is default environment",
        CAT_ENV,
        "Is default environment",
        None,
        [True, False, False, False, False, False, False, None],
    ),
    _setting(
        "env:Location",
        CAT_ENV,
        "Location",
        None,
        ["europe", "europe", "europe", "europe", "europe", "unitedstates", "unitedstates", None],
    ),
    _setting(
        "env:Management state",
        CAT_ENV,
        "Management state",
        None,
        ["Ready", "Ready", "Ready", "Ready", "Ready", "Ready", "Ready", None],
    ),
    _setting(
        "env:Provisioning state",
        CAT_ENV,
        "Provisioning state",
        None,
        ["Succeeded", "Succeeded", "Succeeded", "Succeeded", "Succeeded", "Succeeded", "Succeeded", None],
    ),
    _setting(
        "env:Retention period",
        CAT_ENV,
        "Retention period",
        None,
        ["P7D", "P30D", "P7D", "P7D", "P7D", "P30D", "P7D", None],
    ),
    _setting(
        "env:Runtime state",
        CAT_ENV,
        "Runtime state",
        None,
        ["Enabled", "Enabled", "Enabled", "Enabled", "AdminMode", "Enabled", "Disabled", None],
    ),
    _setting(
        "env:Schema type",
        CAT_ENV,
        "Schema type",
        None,
        ["Standard", "Standard", "Standard", "Standard", "Standard", "Standard", "Standard", None],
    ),
    _setting(
        "env:Security group id",
        CAT_ENV,
        "Security group id",
        None,
        [
            None, "3b6c1d92-8a45-4f37-b1c0-7d5e2a9f4b68", None, None,
            None, "c47a0e13-2f96-4d58-9b71-0a3e6c8d5f24", None, None,
        ],
    ),
    # ------------------------------------------------- mgmt: (Managed Environment)
    _setting(
        "mgmt:protectionLevel",
        CAT_MANAGED,
        "protectionLevel",
        None,
        ["Standard", "Standard", "Standard", "Basic", "Basic", "Standard", "Basic", None],
    ),
    _setting(
        "mgmt:settings.extendedSettings.disableAiGeneratedDescriptions",
        CAT_MANAGED,
        "settings.extendedSettings.disableAiGeneratedDescriptions",
        None,
        ["false", "false", "false", None, None, "true", None, None],
    ),
    _setting(
        "mgmt:settings.extendedSettings.disableAiGenerativeFeatures",
        CAT_MANAGED,
        "settings.extendedSettings.disableAiGenerativeFeatures",
        None,
        ["false", "false", "false", None, None, "true", None, None],
    ),
    _setting(
        "mgmt:settings.extendedSettings.excludeEnvironmentFromAnalysis",
        CAT_MANAGED,
        "settings.extendedSettings.excludeEnvironmentFromAnalysis",
        None,
        ["false", "false", "true", None, None, "false", None, None],
    ),
    _setting(
        "mgmt:settings.extendedSettings.includeInsightsSummaryEmail",
        CAT_MANAGED,
        "settings.extendedSettings.includeInsightsSummaryEmail",
        None,
        ["true", "true", "false", None, None, "true", None, None],
    ),
    _setting(
        "mgmt:settings.extendedSettings.includeOnHomeNavigation",
        CAT_MANAGED,
        "settings.extendedSettings.includeOnHomeNavigation",
        None,
        ["true", "true", "false", None, None, "true", None, None],
    ),
    _setting(
        "mgmt:settings.extendedSettings.limitSharingMode",
        CAT_MANAGED,
        "settings.extendedSettings.limitSharingMode",
        None,
        [
            "excludeSharingToSecurityGroups", "excludeSharingToSecurityGroups", "noLimit", None,
            None, "excludeSharingToSecurityGroups", None, None,
        ],
    ),
    _setting(
        "mgmt:settings.extendedSettings.makerOnboardingMarkdown",
        CAT_MANAGED,
        "settings.extendedSettings.makerOnboardingMarkdown",
        None,
        [
            ONBOARDING_MARKDOWN,
            ONBOARDING_MARKDOWN,
            None,
            None,
            None,
            ONBOARDING_MARKDOWN.replace("Contoso", "Fabrikam").replace("contoso", "fabrikam").replace("con_", "fab_"),
            None,
            None,
        ],
    ),
    _setting(
        "mgmt:settings.extendedSettings.makerOnboardingTimestamp",
        CAT_MANAGED,
        "settings.extendedSettings.makerOnboardingTimestamp",
        None,
        [
            "2026-02-11T09:14:22Z", "2026-02-11T09:14:22Z", None, None,
            None, "2026-05-04T16:02:47Z", None, None,
        ],
    ),
    _setting(
        "mgmt:settings.extendedSettings.makerOnboardingUrl",
        CAT_MANAGED,
        "settings.extendedSettings.makerOnboardingUrl",
        None,
        [
            "https://intranet.contoso.com/power-platform/getting-started",
            "https://intranet.contoso.com/power-platform/getting-started",
            None,
            None,
            None,
            "https://intranet.fabrikam.com/coe/onboarding",
            None,
            None,
        ],
    ),
    _setting(
        "mgmt:settings.extendedSettings.maxLimitUserSharing",
        CAT_MANAGED,
        "settings.extendedSettings.maxLimitUserSharing",
        None,
        ["20", "5", "-1", None, None, "20", None, None],
    ),
    _setting(
        "mgmt:settings.extendedSettings.solutionCheckerMode",
        CAT_MANAGED,
        "settings.extendedSettings.solutionCheckerMode",
        None,
        ["warn", "block", "none", None, None, "warn", None, None],
    ),
    _setting(
        "mgmt:settings.extendedSettings.suppressValidationEmails",
        CAT_MANAGED,
        "settings.extendedSettings.suppressValidationEmails",
        None,
        ["false", "true", "true", None, None, "false", None, None],
    ),
    # ------------------------------------ ppapi: (environment management settings)
    _setting(
        "ppapi:copilotStudio_ConnectedAgents",
        CAT_PPAPI,
        "Copilot Studio / Connected Agents",
        None,
        ["Enabled", "Enabled", "Enabled", "Disabled", "Enabled", "Disabled", "Enabled", None],
    ),
    _setting(
        "ppapi:intelligence_DisableCopilot",
        CAT_PPAPI,
        "Intelligence / Disable Copilot",
        None,
        [False, False, False, False, False, True, False, None],
    ),
    _setting(
        "ppapi:powerApps_AllowCodeApps",
        CAT_PPAPI,
        "Power Apps / Allow Code Apps",
        None,
        [True, False, True, True, True, False, True, None],
    ),
    _setting(
        "ppapi:powerApps_DisableConnectionSharingWithEveryone",
        CAT_PPAPI,
        "Power Apps / Disable Connection Sharing With Everyone",
        None,
        [True, True, True, False, False, True, False, None],
    ),
    _setting(
        "ppapi:powerApps_DisableShareWithEveryone",
        CAT_PPAPI,
        "Power Apps / Disable Share With Everyone",
        None,
        [True, True, True, True, False, True, False, None],
    ),
    _setting(
        "ppapi:powerApps_EnableCanvasAppInsights",
        CAT_PPAPI,
        "Power Apps / Enable Canvas App Insights",
        None,
        [True, True, False, False, False, True, False, None],
    ),
    _setting(
        "ppapi:powerAutomate_DisableCopilot",
        CAT_PPAPI,
        "Power Automate / Disable Copilot",
        None,
        [False, False, False, False, False, True, False, None],
    ),
    _setting(
        "ppapi:powerPlatform_DisableAdminDigest",
        CAT_PPAPI,
        "Power Platform / Disable Admin Digest",
        None,
        [False, False, False, False, True, False, True, None],
    ),
    _setting(
        "ppapi:search_DisableDocsSearch",
        CAT_PPAPI,
        "Search / Disable Docs Search",
        None,
        [False, False, False, False, False, False, False, None],
    ),
    _setting(
        "ppapi:teamsIntegration_ShareWithColleaguesUserLimit",
        CAT_PPAPI,
        "Teams Integration / Share With Colleagues User Limit",
        None,
        [10000, 10000, 10000, 10000, 10000, 5000, 10000, None],
    ),
    # ------------------------------ setting: (settingdefinition + organizationsetting)
    # Contoso Test could not read the settings framework at all - absent everywhere below.
    _setting(
        "setting:enablecopilotmodeldrivenapps",
        CAT_FEATURES,
        "Copilot in model-driven apps",
        "Shows the Copilot side pane in model-driven apps for users with the "
        "required security role.",
        ["true", "false", "true", None, "true", "false", "true", None],
        source="override",
    ),
    _setting(
        "setting:enablelegacyauditlogging",
        CAT_FEATURES,
        "Enable legacy audit logging",
        None,
        ["false", "false", "false", None, "false", "false", "false", None],
        source="default",
    ),
    _setting(
        "setting:enableprimarynamesearch",
        CAT_FEATURES,
        "Enable primary name search",
        "Allows Dataverse search to match on the primary name column without an "
        "explicit search index.",
        ["true", "true", "true", None, "true", "true", "true", None],
        source="default",
    ),
    _setting(
        "setting:enablesolutioncheckerenforcement",
        CAT_FEATURES,
        "Solution checker enforcement",
        "Blocks import of managed solutions that fail solution checker rules of "
        "severity High or above.",
        ["warn", "block", "warn", None, "none", "warn", "none", None],
        source="override",
    ),
    _setting(
        "setting:pfi_allowedipranges",
        CAT_FEATURES,
        "Allowed IP ranges",
        "CIDR ranges permitted by the IP firewall.",
        [None, "10.20.0.0/16, 172.16.44.0/24, 203.0.113.0/24", None, None, None, None, None, None],
        source="override",
    ),
    _setting(
        "setting:pfi_customerlockboxenabled",
        CAT_FEATURES,
        "Customer Lockbox enabled",
        "Requires explicit customer approval before Microsoft engineers can "
        "access environment data during a support request.",
        ["false", "true", "false", None, "false", "false", "false", None],
        source="override",
    ),
    _setting(
        "setting:pfi_disablecrossgeodataflow",
        CAT_FEATURES,
        "Disable cross-geo data flow",
        "Blocks features that would move customer data outside the environment "
        "geography, including some AI Builder and Copilot capabilities.",
        ["false", "false", "false", None, "false", "true", "false", None],
        source="override",
    ),
    _setting(
        "setting:pfi_enablecustomermanagedkey",
        CAT_FEATURES,
        "Customer-managed encryption key",
        "Encrypts environment data with a key held in the customer's Azure Key "
        "Vault instead of the Microsoft-managed key.",
        ["false", "true", "false", None, "false", "false", "false", None],
        source="override",
    ),
    _setting(
        "setting:pfi_enableipbasedcookiebinding",
        CAT_FEATURES,
        "Enable IP based cookie binding",
        "Binds the Dataverse session cookie to the originating IP address. "
        "Mitigates session hijacking but breaks clients behind rotating NAT "
        "gateways or split-tunnel VPNs.",
        ["false", "true", "true", None, "false", "false", "false", None],
        source="override",
    ),
    _setting(
        "setting:pfi_enableipbasedfirewallrule",
        CAT_FEATURES,
        "Enable IP firewall",
        "Restricts Dataverse access to the configured IP address ranges.",
        ["false", "true", "false", None, "false", "false", "false", None],
        source="override",
    ),
    _setting(
        "setting:pfi_enableipbasedfirewallruleinauditmode",
        CAT_FEATURES,
        "IP firewall in audit-only mode",
        "Logs requests that would be blocked by the IP firewall without actually "
        "blocking them. Intended for rollout validation.",
        [None, "true", None, None, None, None, None, None],
        source="override",
    ),
    _setting(
        "setting:pfi_enabletelemetryexport",
        CAT_FEATURES,
        "Export telemetry to Application Insights",
        None,
        ["true", "true", "false", None, "false", "true", "false", None],
        source="override",
    ),
    _setting(
        "setting:pluginexecutiontimeout",
        CAT_FEATURES,
        "Plug-in execution timeout (seconds)",
        "Sandbox execution limit before a plug-in is aborted with a timeout fault.",
        ["120", "120", "120", None, "300", "120", "120", None],
        source="override",
    ),
    _setting(
        "setting:plugintracelogsetting",
        CAT_FEATURES,
        "Plug-in trace log level",
        None,
        ["Exception", "Off", "All", None, "All", "Exception", "All", None],
        source="override",
    ),
    _setting(
        "setting:powerapps_asyncsave",
        CAT_FEATURES,
        "Async save",
        None,
        ["true", "true", "true", None, "true", "true", "true", None],
        source="default",
    ),
    # ---------------------------------------------------- org: (organization table)
    # Contoso Test lost its whole Dataverse block, so it is absent from org:/orgdb:/setting:.
    _setting(
        "org:allowautoresponsecreation",
        CAT_ORG,
        "Allow Auto Response Creation",
        None,
        [False, False, False, None, False, True, False, None],
    ),
    _setting(
        "org:allowlegacyclientexperience",
        CAT_ORG,
        "Allow Legacy Client Experience",
        None,
        [False, False, False, None, True, False, True, None],
    ),
    _setting(
        "org:allowunresolvedpartiesonemailsend",
        CAT_ORG,
        "Allow Unresolved Parties On Email Send",
        "Permits sending email to addresses that do not resolve to a Dataverse record.",
        [True, False, True, None, True, True, True, None],
    ),
    _setting(
        "org:auditretentionperiodv2",
        CAT_ORG,
        "Audit Retention Period",
        "Number of days audit records are retained before automatic deletion. "
        "-1 means records are kept forever.",
        [90, 365, 90, None, 30, 365, 30, None],
    ),
    _setting(
        "org:blockedattachments",
        CAT_ORG,
        "Blocked Attachments",
        "Semicolon-separated list of file extensions that may not be uploaded as "
        "notes or file column content. The default platform list is applied in "
        "addition to any custom entries configured here.",
        [
            "ade;adp;app;asa;ashx;asmx;asp;bas;bat;cdx;cer;chm;class;cmd;com;config;cpl;crt;csh;dll;exe;fxp;hlp;hta;htr;htw;ida;idc;idq;inf;ins;isp;its;jse;ksh;lnk;mad;maf;mag;mam;maq;mar;mas;mat;mau;mav;maw;mda;mdb;mde;mdt;mdw;mdz;msc;msh;msi;msp;mst;ops;pcd;pif;prf;prg;printer;pst;reg;rem;scf;scr;sct;shb;shs;shtm;shtml;soap;stm;url;vb;vbe;vbs;vsmacros;vss;vst;vsw;ws;wsc;wsf;wsh",
            "ade;adp;app;asa;ashx;asmx;asp;bas;bat;cdx;cer;chm;class;cmd;com;config;cpl;crt;csh;dll;exe;fxp;hlp;hta;htr;htw;ida;idc;idq;inf;ins;isp;its;jse;ksh;lnk;mad;maf;mag;mam;maq;mar;mas;mat;mau;mav;maw;mda;mdb;mde;mdt;mdw;mdz;msc;msh;msi;msp;mst;ops;pcd;pif;prf;prg;printer;pst;reg;rem;scf;scr;sct;shb;shs;shtm;shtml;soap;stm;url;vb;vbe;vbs;vsmacros;vss;vst;vsw;ws;wsc;wsf;wsh;zip;7z",
            "ade;adp;app;asa;ashx;asmx;asp;bas;bat;cdx;cer;chm;class;cmd;com;config;cpl;crt;csh;dll;exe",
            None,
            "ade;adp;app;asa;ashx;asmx;asp;bas;bat;cdx;cer;chm;class;cmd;com;config;cpl;crt;csh;dll;exe",
            "ade;adp;app;asa;ashx;asmx;asp;bas;bat;cdx;cer;chm;class;cmd;com;config;cpl;crt;csh;dll;exe",
            "ade;adp;app;asa;ashx;asmx;asp;bas;bat;cdx;cer;chm;class;cmd;com;config;cpl;crt;csh;dll;exe",
            None,
        ],
    ),
    _setting(
        "org:currencydisplayoption",
        CAT_ORG,
        "Currency Display Option",
        "Choice column: 0 shows the currency symbol, 1 shows the ISO currency code. "
        "The collector reports the stored value, not the option label.",
        [0, 0, 0, None, 0, 0, 1, None],
    ),
    _setting(
        "org:enablebingmapsintegration",
        CAT_ORG,
        "Enable Bing Maps Integration",
        None,
        [True, True, True, None, True, True, True, None],
    ),
    _setting(
        "org:enableimmersiveskypeintegration",
        CAT_ORG,
        "Enable Immersive Skype Integration",
        None,
        [True, True, True, None, True, False, True, None],
    ),
    _setting(
        "org:fiscalyearformat",
        CAT_ORG,
        "Fiscal Year Format",
        None,
        ["FY {YYYY}", "FY {YYYY}", "FY {YYYY}", None, "FY {YYYY}", "{YYYY}", "FY {YYYY}", None],
    ),
    _setting(
        "org:isauditenabled",
        CAT_ORG,
        "Is Auditing Enabled",
        "Master switch for Dataverse auditing. When off, no entity or attribute "
        "level auditing is recorded regardless of table configuration.",
        [True, True, True, None, False, True, False, None],
    ),
    _setting(
        "org:isdisabled",
        CAT_ORG,
        "Is Disabled",
        None,
        [False, False, False, None, False, False, False, None],
    ),
    _setting(
        "org:isfolderbasedtrackingenabled",
        CAT_ORG,
        "Is Folder Based Tracking Enabled",
        "Allows users to track Exchange items by moving them into a tracked folder.",
        [False, True, False, None, False, False, False, None],
    ),
    _setting(
        "org:isreadauditenabled",
        CAT_ORG,
        "Is Read Auditing Enabled",
        "Records read operations. Significantly increases audit log volume and "
        "is normally only enabled for regulated workloads.",
        [False, False, False, None, False, False, False, None],
    ),
    _setting(
        "org:isuseraccessauditenabled",
        CAT_ORG,
        "Is User Access Auditing Enabled",
        "Records each time a user accesses the environment.",
        [True, True, False, None, False, True, False, None],
    ),
    _setting(
        "org:localeid",
        CAT_ORG,
        "Base Language Code",
        "Base language of the organization. Cannot be changed after provisioning.",
        [1033, 1033, 1033, None, 1033, 1033, 1033, None],
    ),
    _setting(
        "org:maxrecordsforexporttoexcel",
        CAT_ORG,
        "Max Records For Export To Excel",
        None,
        [100000, 100000, 100000, None, 100000, 50000, 100000, None],
    ),
    _setting(
        "org:maxrecordsforlookupfilters",
        CAT_ORG,
        "Max Records For Lookup Filters",
        None,
        [100, 100, 100, None, 100, 100, 100, None],
    ),
    _setting(
        "org:maxuploadfilesize",
        CAT_ORG,
        "Max Upload File Size",
        "Upper bound in bytes for attachments and file columns. The platform "
        "maximum is 131072000 bytes (125 MB).",
        [5242880, 33554432, 33554432, None, 131072000, 10485760, 5242880, None],
    ),
    _setting(
        "org:privacystatementurl",
        CAT_ORG,
        "Privacy Statement URL",
        "Custom privacy statement shown to users in the application footer.",
        [
            "https://www.contoso.com/legal/privacy",
            "https://www.contoso.com/legal/privacy",
            "https://www.contoso.com/legal/privacy",
            None,
            None,
            "https://www.fabrikam.com/privacy-policy",
            None,
            None,
        ],
    ),
    _setting(
        "org:quickfindrecordlimitenabled",
        CAT_ORG,
        "Quick Find Record Limit Enabled",
        "Aborts quick-find searches that would scan an excessive number of records.",
        [True, True, True, None, True, True, True, None],
    ),
    _setting(
        "org:sessiontimeoutenabled",
        CAT_ORG,
        "Session Timeout Enabled",
        "Forces re-authentication after the configured period of inactivity.",
        [True, True, True, None, False, True, False, None],
    ),
    _setting(
        "org:sessiontimeoutinmins",
        CAT_ORG,
        "Session Timeout In Mins",
        None,
        [1440, 480, 1440, None, None, 720, None, None],
    ),
    _setting(
        "org:useraccessauditinginterval",
        CAT_ORG,
        "User Access Auditing Interval",
        None,
        [4, 4, 4, None, 4, 4, 4, None],
    ),
    _setting(
        "org:usereadform",
        CAT_ORG,
        "Use Read Form",
        None,
        [True, True, True, None, True, True, True, None],
    ),
    # ------------------------------------------------ orgdb: (OrgDBOrgSettings XML)
    _setting(
        "orgdb:DisableImplicitSharingOfCommunicationActivity",
        CAT_ORGDB,
        "DisableImplicitSharingOfCommunicationActivity",
        None,
        ["0", "0", "0", None, "0", "1", "0", None],
    ),
    _setting(
        "orgdb:DisableInactiveRecordFilterForLookup",
        CAT_ORGDB,
        "DisableInactiveRecordFilterForLookup",
        None,
        ["0", "0", "1", None, "1", "0", "0", None],
    ),
    _setting(
        "orgdb:DisableSmartMatching",
        CAT_ORGDB,
        "DisableSmartMatching",
        None,
        ["1", "1", "1", None, "1", "0", "1", None],
    ),
    _setting(
        "orgdb:EnableRetrieveMultipleOptimization",
        CAT_ORGDB,
        "EnableRetrieveMultipleOptimization",
        None,
        ["1", "1", "1", None, "1", "1", "1", None],
    ),
    _setting(
        "orgdb:GrantFullAccessForMergeToMasterOwner",
        CAT_ORGDB,
        "GrantFullAccessForMergeToMasterOwner",
        None,
        ["0", "1", "0", None, "0", "0", "0", None],
    ),
    _setting(
        "orgdb:MaxSecurityPrincipalsToShareWith",
        CAT_ORGDB,
        "MaxSecurityPrincipalsToShareWith",
        None,
        ["1000", "250", "1000", None, "1000", "1000", "1000", None],
    ),
    _setting(
        "orgdb:RecordCountLimitToSwitchToBruteForceSearch",
        CAT_ORGDB,
        "RecordCountLimitToSwitchToBruteForceSearch",
        None,
        ["5000", "5000", "5000", None, "5000", "5000", "5000", None],
    ),
    _setting(
        "orgdb:ShareToPreviousOwnerOnAssign",
        CAT_ORGDB,
        "ShareToPreviousOwnerOnAssign",
        None,
        ["1", "0", "1", None, "1", "1", "1", None],
    ),
    _setting(
        "orgdb:SyncBulkOperationBatchSize",
        CAT_ORGDB,
        "SyncBulkOperationBatchSize",
        None,
        ["20", "50", "20", None, "20", "20", "20", None],
    ),
    _setting(
        "orgdb:TotalRecordCountLimit",
        CAT_ORGDB,
        "TotalRecordCountLimit",
        None,
        ["50000", "50000", "50000", None, "50000", "100000", "50000", None],
    ),
    # featurecontrolsetting rows - content arrives base64-encoded and is decoded to JSON.
    _setting(
        "fcs:FCB.AllowSavedQueryVisualizationInRibbon",
        CAT_FCS,
        "Allow saved query visualization in ribbon",
        None,
        [
            {"enabled": True},
            {"enabled": True},
            {"enabled": True},
            None,
            {"enabled": True},
            {"enabled": False},
            {"enabled": True},
            None,
        ],
    ),
    _setting(
        "fcs:FCB.AsyncGridDataLoad",
        CAT_FCS,
        "Async grid data load",
        None,
        [
            {"enabled": True, "rolloutStage": "ga"},
            {"enabled": True, "rolloutStage": "ga"},
            {"enabled": True, "rolloutStage": "preview"},
            None,
            {"enabled": True, "rolloutStage": "preview"},
            {"enabled": True, "rolloutStage": "ga"},
            {"enabled": True, "rolloutStage": "ga"},
            None,
        ],
    ),
    _setting(
        "fcs:FCB.EnableEditableGridOnPhone",
        CAT_FCS,
        "Enable editable grid on phone",
        None,
        [
            {"enabled": False},
            {"enabled": False},
            {"enabled": True},
            None,
            {"enabled": True},
            {"enabled": False},
            {"enabled": False},
            None,
        ],
    ),
    _setting(
        "fcs:FCB.MaintenanceNotice",
        CAT_FCS,
        "Maintenance notice",
        None,
        [
            "Scheduled maintenance window: Sundays 02:00-04:00 UTC\nContact: platform-ops@contoso.com",
            "Scheduled maintenance window: Sundays 02:00-04:00 UTC\nContact: platform-ops@contoso.com",
            None,
            None,
            None,
            "Scheduled maintenance window: Saturdays 22:00-02:00 UTC\nContact: ops@fabrikam.com",
            None,
            None,
        ],
    ),
    _setting(
        "fcs:FCB.OfflineProfileSync",
        CAT_FCS,
        "Offline profile sync",
        None,
        [
            {"enabled": True, "maxRecords": 5000},
            {"enabled": True, "maxRecords": 5000},
            {"enabled": True, "maxRecords": 1000},
            None,
            {"enabled": True, "maxRecords": 1000},
            {"enabled": True, "maxRecords": 5000},
            {"enabled": True, "maxRecords": 5000},
            None,
        ],
    ),
]

# Same ordering rule as collect.collect(): category order first, then name.
SETTINGS = sorted(_ROWS, key=lambda r: (CATEGORY_ORDER.index(r["category"]), r["name"].lower()))

SAMPLE = {
    "generatedUtc": GENERATED_UTC,
    "tenantId": TENANT_ID,
    "environments": ENVIRONMENTS,
    "settings": SETTINGS,
}
