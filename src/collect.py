"""Collects Power Platform environments plus their settings/features into the report data contract."""

from __future__ import annotations

import json
import threading
import urllib.parse
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

from ppapi import BAP_SCOPE, PPAPI_SCOPE, ApiError, TokenProvider, explain, get_json, get_paged

BAP_ENVIRONMENTS = (
    "https://api.bap.microsoft.com/providers/Microsoft.BusinessAppPlatform"
    "/scopes/admin/environments?api-version=2020-10-01&$expand=properties.capacity,properties.addons"
)
PPAPI_SETTINGS = "https://api.powerplatform.com/environmentmanagement/environments/{env}/settings?api-version=2024-10-01"
DV = "/api/data/v9.2"

CAT_ENV = "Environment"
CAT_MANAGED = "Managed Environment"
CAT_PPAPI = "Environment management settings"
CAT_FEATURES = "Settings & features (Dataverse)"
CAT_ORG = "Organization table (Dataverse)"
CAT_ORGDB = "OrgDBOrgSettings (Dataverse)"
CATEGORY_ORDER = [CAT_ENV, CAT_MANAGED, CAT_PPAPI, CAT_FEATURES, CAT_ORG, CAT_ORGDB]

# Identifiers and churn columns - never interesting in a settings comparison.
ORG_SKIP = {
    "organizationid", "versionnumber", "createdon", "modifiedon", "orgdborgsettings",
    "name", "uniquename", "sqlaccessgroupid", "privilegeusergroupid", "privilegereportinggroupid",
    "reportinggroupid", "sqldatabasename", "sqlaccessgroupname", "privilegeusergroupname",
    "privilegereportinggroupname", "reportinggroupname", "highcontrastthemedata", "defaultthemedata",
    "slaid", "kmsettings", "userlastsyncdate", "expiredprocessruntimecombinedtimeout",
}


class MetaCache:
    """Organization column labels/descriptions - identical across environments, so fetch once."""

    def __init__(self):
        self._lock = threading.Lock()
        self._labels: dict[str, tuple[str, str | None]] | None = None

    def labels(self, base: str, token: str) -> dict[str, tuple[str, str | None]]:
        if self._labels is not None:
            return self._labels
        url = (
            f"{base}{DV}/EntityDefinitions(LogicalName='organization')/Attributes"
            "?$select=LogicalName,DisplayName,Description"
        )
        fetched: dict[str, tuple[str, str | None]] = {}
        try:
            # Fetched outside the lock: a duplicate fetch is cheaper than serializing every worker.
            for attr in get_paged(url, token):
                logical = attr.get("LogicalName")
                if logical:
                    fetched[logical] = (_label(attr.get("DisplayName")) or logical, _label(attr.get("Description")))
        except ApiError:
            return {}  # labels are a nice-to-have; never cache the failure, the next env may succeed
        with self._lock:
            if self._labels is None:
                self._labels = fetched
        return self._labels


def collect(
    tp: TokenProvider,
    tenant_id: str,
    *,
    env_filter: str | None = None,
    max_envs: int | None = None,
    skip_dataverse: bool = False,
    skip_ppapi: bool = False,
    workers: int = 6,
    log=print,
) -> dict:
    log("Listing environments...")
    raw_envs = get_paged(BAP_ENVIRONMENTS, tp.token(BAP_SCOPE))
    if env_filter:
        needle = env_filter.lower()
        raw_envs = [e for e in raw_envs if needle in _prop(e, "displayName", "").lower()]
    raw_envs.sort(key=lambda e: _prop(e, "displayName", "").lower())
    if max_envs:
        raw_envs = raw_envs[:max_envs]
    log(f"  {len(raw_envs)} environment(s)")

    meta = MetaCache()
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        results = list(
            pool.map(
                lambda e: _collect_one(tp, e, meta, skip_dataverse, skip_ppapi, log),
                raw_envs,
            )
        )

    table: dict[str, dict] = {}
    environments = []
    for env, rows in results:
        environments.append(env)
        for category, key, name, description, value in rows:
            row = table.setdefault(
                key, {"key": key, "category": category, "name": name, "description": description, "values": {}}
            )
            if row["description"] is None and description:
                row["description"] = description
            row["values"][env["id"]] = value

    settings = sorted(
        table.values(),
        key=lambda r: (CATEGORY_ORDER.index(r["category"]) if r["category"] in CATEGORY_ORDER else 99, r["name"].lower()),
    )
    return {
        "generatedUtc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "tenantId": tenant_id,
        "environments": environments,
        "settings": settings,
    }


def _collect_one(tp, raw, meta, skip_dataverse, skip_ppapi, log):
    try:
        env, rows = _collect_env(tp, raw, meta, skip_dataverse, skip_ppapi)
    except Exception as e:  # one misbehaving environment must never sink the whole run
        env, rows = _env_summary(raw, "error", f"collection failed: {e}"), []
    note = env["statusMessage"]
    log(f"  {env['name']}: {len(rows)} setting(s){' - ' + note if note else ''}")
    return env, rows


def _collect_env(tp, raw, meta, skip_dataverse, skip_ppapi):
    env_id = raw.get("name") or raw.get("id", "")
    linked = _prop(raw, "linkedEnvironmentMetadata", {}) or {}
    notes: list[str] = []
    attempted = 0
    failed = 0
    rows = list(_rows_bap(raw))

    if not skip_ppapi:
        attempted += 1
        try:
            rows += _rows_ppapi(tp, env_id)
        except ApiError as e:
            failed += 1
            notes.append(f"environment management settings: {explain(e)}")

    api_url = (linked.get("instanceApiUrl") or linked.get("instanceUrl") or "").rstrip("/")
    if not skip_dataverse:
        if not api_url:
            notes.append("no Dataverse database")  # informational, not a failure
        else:
            attempted += 1
            try:
                rows += _rows_dataverse(api_url, tp.token(f"{api_url}/.default"), meta, notes)
            except ApiError as e:
                failed += 1
                notes.append(f"Dataverse: {explain(e)}")

    status = "ok"
    if attempted and failed >= attempted:
        status = "error"
    elif notes:
        status = "partial"
    return _env_summary(raw, status, "; ".join(notes) or None), rows


def _env_summary(raw, status, message):
    linked = _prop(raw, "linkedEnvironmentMetadata", {}) or {}
    return {
        "id": raw.get("name") or raw.get("id", ""),
        "name": _prop(raw, "displayName") or raw.get("name", ""),
        "type": _prop(raw, "environmentSku", "Unknown"),
        "region": _prop(raw, "azureRegion") or raw.get("location") or "",
        "url": linked.get("instanceUrl") or "",
        "state": _env_state(raw, linked),
        "status": status,
        "statusMessage": message,
    }


def _rows_bap(raw):
    """Core environment facts plus the Managed Environment / governance block."""
    props = raw.get("properties") or {}
    linked = props.get("linkedEnvironmentMetadata") or {}
    states = props.get("states") or {}
    core = {
        "Environment type (SKU)": props.get("environmentSku"),
        "Is default environment": props.get("isDefault"),
        "Azure region": props.get("azureRegion"),
        "Location": raw.get("location"),
        "Database type": props.get("databaseType"),
        "Provisioning state": props.get("provisioningState"),
        "Runtime state": (states.get("runtime") or {}).get("id"),
        "Management state": (states.get("management") or {}).get("id"),
        "Dataverse URL": linked.get("instanceUrl"),
        "Dataverse version": linked.get("version"),
        "Dataverse state": linked.get("instanceState"),
        "Domain name": linked.get("domainName"),
        "Schema type": linked.get("schemaType"),
        "Security group id": props.get("securityGroupId") or linked.get("securityGroupId"),
        "Retention period": props.get("retentionPeriod"),
        "Environment group id": (props.get("parentEnvironmentGroup") or {}).get("id"),
    }
    for name, value in core.items():
        row = _row(CAT_ENV, f"env:{name}", name, value)
        if row:
            yield row

    for key, value in _flatten(props.get("governanceConfiguration") or {}).items():
        row = _row(CAT_MANAGED, f"mgmt:{key}", key, value)
        if row:
            yield row


def _rows_ppapi(tp, env_id):
    """Power Platform API environment management settings - works without a Dataverse app user."""
    data = get_json(PPAPI_SETTINGS.format(env=urllib.parse.quote(env_id)), tp.token(PPAPI_SCOPE))
    merged: dict = {}
    for item in data.get("objectResult") or []:
        merged.update(item or {})
    for key, value in _flatten(merged).items():
        if key in ("id", "tenantId"):
            continue
        row = _row(CAT_PPAPI, f"ppapi:{key}", _humanize(key), value)
        if row:
            yield row


def _rows_dataverse(base, token, meta, notes):
    """Organization columns, the OrgDBOrgSettings XML blob and the settings framework."""
    rows = []
    org = (get_json(f"{base}{DV}/organizations", token).get("value") or [{}])[0]
    labels = meta.labels(base, token)

    for key, value in org.items():
        if "@" in key or key.startswith("_") or key in ORG_SKIP or isinstance(value, (dict, list)):
            continue
        display, description = labels.get(key, (key, None))
        row = _row(CAT_ORG, f"org:{key}", display or key, value, description)
        if row:
            rows.append(row)

    rows += _rows_orgdb(org.get("orgdborgsettings"), notes)
    rows += _rows_settings_framework(base, token, notes)
    return rows


def _rows_orgdb(xml_text, notes):
    """orgdborgsettings is a single XML column holding many feature flags."""
    if not xml_text:
        return []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        notes.append("OrgDBOrgSettings: XML could not be parsed")
        return []
    out = []
    for node in root:
        row = _row(CAT_ORGDB, f"orgdb:{node.tag}", node.tag, (node.text or "").strip())
        if row:
            out.append(row)
    return out


def _rows_settings_framework(base, token, notes):
    """settingdefinition + organizationsetting back the PPAC settings/feature toggles.

    The schema is not documented on Learn, so query without $select and probe the columns.
    """
    try:
        definitions = get_paged(f"{base}{DV}/settingdefinitions", token)
    except ApiError as e:
        notes.append(f"setting definitions: {explain(e)}")
        return []
    try:
        overrides = get_paged(f"{base}{DV}/organizationsettings", token)
    except ApiError as e:
        notes.append(f"setting values: {explain(e)} (showing defaults)")
        overrides = []

    by_definition = {}
    for item in overrides:
        ref = _first(item, "_settingdefinitionid_value", "settingdefinitionid")
        if ref:
            by_definition[str(ref).lower()] = item

    out = []
    for d in definitions:
        unique = _first(d, "uniquename", "name")
        if not unique:
            continue
        override = by_definition.get(str(_first(d, "settingdefinitionid") or "").lower())
        value = _first(override or {}, "value", "settingvalue")
        source = "override"
        if value is None:
            value, source = _first(d, "defaultvalue"), "default"
        row = _row(
            CAT_FEATURES,
            f"setting:{unique}",
            _first(d, "displayname", "uniquename") or unique,
            value,
            _first(d, "description"),
            source,
        )
        if row:
            out.append(row)
    return out


def _row(category, key, name, value, description=None, source="value"):
    if value is None or value == "":
        return None
    return (category, key, name, description, {"display": _display(value), "raw": value, "source": source})


def _display(value):
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (dict, list)):
        return json.dumps(value, sort_keys=True, separators=(",", ":"))
    return str(value)


def _flatten(obj, prefix=""):
    if not isinstance(obj, dict):
        return {}
    out = {}
    for key, value in (obj or {}).items():
        if isinstance(value, dict):
            out.update(_flatten(value, f"{prefix}{key}."))
        else:
            out[f"{prefix}{key}"] = value
    return out


def _first(item, *names):
    for name in names:
        value = (item or {}).get(name)
        if value is not None and value != "":
            return value
    return None


def _label(node):
    node = node or {}
    localized = node.get("UserLocalizedLabel") or (node.get("LocalizedLabels") or [{}])[0]
    return (localized or {}).get("Label") or None


def _humanize(key):
    """powerApps_AllowCodeApps -> Power apps / Allow code apps."""
    parts = key.split("_", 1)
    words = [_spaced(p) for p in parts]
    return " / ".join(w for w in words if w)


def _spaced(text):
    out = ""
    for i, ch in enumerate(text):
        if ch.isupper() and i and not text[i - 1].isupper():
            out += " "
        out += ch
    return out[:1].upper() + out[1:]


def _prop(raw, key, default=None):
    return (raw.get("properties") or {}).get(key, default)


def _env_state(raw, linked):
    """Runtime state wins when it is not Enabled - Disabled/AdminMode is what makes an env unusable."""
    runtime = ((_prop(raw, "states") or {}).get("runtime") or {}).get("id")
    if runtime and runtime.lower() != "enabled":
        return runtime
    return linked.get("instanceState") or _prop(raw, "provisioningState") or runtime or ""
