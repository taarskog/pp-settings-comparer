"""Offline test for collect.py - patches the HTTP layer with fake API payloads.

Run with: python tests/smoke_test.py
"""

import sys
from pathlib import Path

import base64

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

import collect  # noqa: E402
from ppapi import ApiError  # noqa: E402

BAP_ENVS = [
    {
        "id": "/providers/Microsoft.BusinessAppPlatform/scopes/admin/environments/Default-aaa",
        "name": "Default-aaa",
        "location": "europe",
        "properties": {
            "displayName": "Contoso (default)",
            "environmentSku": "Default",
            "azureRegion": "westeurope",
            "databaseType": "CommonDataService",
            "isDefault": True,
            "provisioningState": "Succeeded",
            "states": {"management": {"id": "Ready"}, "runtime": {"id": "Enabled"}},
            "governanceConfiguration": {"protectionLevel": "Standard", "settings": {"extendedSettings": {"excludeEnvironmentFromAnalysis": "false"}}},
            "linkedEnvironmentMetadata": {
                "instanceUrl": "https://org1.crm4.dynamics.com/",
                "instanceApiUrl": "https://org1.api.crm4.dynamics.com",
                "instanceState": "Ready",
                "domainName": "org1",
                "version": "9.2.24.1",
            },
        },
    },
    {
        "name": "denied-bbb",
        "location": "unitedstates",
        "properties": {
            "displayName": "Fabrikam Dev",
            "environmentSku": "Sandbox",
            "azureRegion": "westus",
            "databaseType": "CommonDataService",
            "states": {"runtime": {"id": "Disabled"}},
            "provisioningState": "Succeeded",
            "governanceConfiguration": {"protectionLevel": "Basic"},
            "linkedEnvironmentMetadata": {
                "instanceUrl": "https://org2.crm.dynamics.com/",
                "instanceApiUrl": "https://org2.api.crm.dynamics.com",
            },
        },
    },
    {
        "name": "nodb-ccc",
        "location": "unitedstates",
        "properties": {"displayName": "Teams env", "environmentSku": "Teams", "databaseType": "None"},
    },
]

ORG = {
    "@odata.etag": 'W/"123"',
    "organizationid": "11111111-1111-1111-1111-111111111111",
    "isauditenabled": True,
    "maxuploadfilesize": 5242880,
    "_createdby_value": "x",
    "orgdborgsettings": "<OrgSettings><EnableRetrieveMultipleOptimization>1</EnableRetrieveMultipleOptimization><DisableImplicitSharingOfCommunicationActivity>0</DisableImplicitSharingOfCommunicationActivity></OrgSettings>",
}

ATTRS = [
    {"LogicalName": "isauditenabled", "DisplayName": {"UserLocalizedLabel": {"Label": "Is Auditing Enabled"}}, "Description": {"UserLocalizedLabel": {"Label": "Whether auditing is enabled."}}},
    {"LogicalName": "maxuploadfilesize", "DisplayName": {"LocalizedLabels": [{"Label": "Max Upload File Size"}]}, "Description": {"UserLocalizedLabel": {"Label": None}}},
]

DEFS = [
    {"settingdefinitionid": "DEF-1", "uniquename": "pfi_enableipbasedcookiebinding", "displayname": "Enable IP based cookie binding", "description": "Binds session cookies to the client IP.", "defaultvalue": "false"},
    {"settingdefinitionid": "def-2", "uniquename": "powerapps_asyncsave", "displayname": "Async save", "defaultvalue": "true"},
]
OVERRIDES = [{"_settingdefinitionid_value": "def-1", "value": "true"}]


def _b64(text):
    return base64.b64encode(text.encode("utf-8")).decode("ascii")


# One row per content shape the decoder has to survive.
FCS = [
    {"featurecontrolsettingid": "f1", "uniquename": "FCB.EnableFoo", "name": "Enable Foo",
     "content": _b64('{"enabled":true,"scope":"org"}')},
    {"featurecontrolsettingid": "f2", "uniquename": "FCB.MultiLine", "name": "Multi line",
     "content": _b64("line one\r\nline two")},
    {"featurecontrolsettingid": "f3", "uniquename": "FCB.NotBase64", "name": "Not base64",
     "content": "this is not base64!!"},
    {"featurecontrolsettingid": "f4", "uniquename": "FCB.Empty", "name": "Empty", "content": ""},
]

PPAPI_SETTINGS = {"objectResult": [{"id": "x", "tenantId": "t", "powerApps_AllowCodeApps": True, "copilotStudio_ConnectedAgents": "Disabled"}]}


def fake_get_json(url, token, timeout=60):
    if "environmentmanagement" in url:
        if "denied-bbb" in url:
            raise ApiError(403, "forbidden", url)
        return PPAPI_SETTINGS
    if "/organizations" in url:
        if "org2" in url:
            raise ApiError(401, '{"error":{"code":"0x80072560","message":"The user is not a member of the organization."}}', url)
        return {"value": [ORG]}
    raise AssertionError(f"unexpected GET {url}")


def fake_get_paged(url, token, value_key="value", next_key="@odata.nextLink"):
    if "scopes/admin/environments" in url:
        return BAP_ENVS
    if "EntityDefinitions" in url:
        return ATTRS
    if "settingdefinitions" in url:
        return DEFS
    if "organizationsettings" in url:
        return OVERRIDES
    if "featurecontrolsettings" in url:
        return FCS
    raise AssertionError(f"unexpected paged GET {url}")


class FakeTokens:
    def token(self, scope):
        return "fake"


def main():
    collect.get_json = fake_get_json
    collect.get_paged = fake_get_paged

    data = collect.collect(FakeTokens(), "tenant-guid", workers=3)

    envs = {e["id"]: e for e in data["environments"]}
    assert len(envs) == 3, envs
    assert envs["Default-aaa"]["status"] == "ok", envs["Default-aaa"]
    assert envs["Default-aaa"]["state"] == "Ready", envs["Default-aaa"]
    # Runtime state must win over provisioningState so the report can hide it by default.
    assert envs["denied-bbb"]["state"] == "Disabled", envs["denied-bbb"]
    assert "no application user" in (envs["denied-bbb"]["statusMessage"] or ""), envs["denied-bbb"]
    assert "no Dataverse database" in (envs["nodb-ccc"]["statusMessage"] or ""), envs["nodb-ccc"]
    # Status must reflect what failed, not how many rows came back.
    assert envs["denied-bbb"]["status"] == "error", envs["denied-bbb"]
    assert envs["nodb-ccc"]["status"] == "partial", envs["nodb-ccc"]

    rows = {r["key"]: r for r in data["settings"]}
    assert rows["env:Environment type (SKU)"]["values"]["Default-aaa"]["display"] == "Default"
    assert rows["mgmt:protectionLevel"]["values"]["denied-bbb"]["display"] == "Basic"
    assert rows["mgmt:settings.extendedSettings.excludeEnvironmentFromAnalysis"]["values"]["Default-aaa"]["display"] == "false"
    assert rows["ppapi:powerApps_AllowCodeApps"]["name"] == "Power Apps / Allow Code Apps"
    assert rows["ppapi:powerApps_AllowCodeApps"]["values"]["Default-aaa"]["display"] == "Yes"
    assert rows["org:isauditenabled"]["name"] == "Is Auditing Enabled"
    assert rows["org:isauditenabled"]["description"] == "Whether auditing is enabled."
    assert rows["org:maxuploadfilesize"]["name"] == "Max Upload File Size"
    assert "org:organizationid" not in rows and "org:_createdby_value" not in rows
    assert rows["orgdb:EnableRetrieveMultipleOptimization"]["values"]["Default-aaa"]["display"] == "1"
    assert rows["setting:pfi_enableipbasedcookiebinding"]["values"]["Default-aaa"] == {
        "display": "true", "raw": "true", "source": "override",
    }
    assert rows["setting:powerapps_asyncsave"]["values"]["Default-aaa"]["source"] == "default"
    assert rows["setting:pfi_enableipbasedcookiebinding"]["description"] == "Binds session cookies to the client IP."

    # featurecontrolsetting.content is base64; JSON, plain text and undecodable all have to survive.
    assert rows["fcs:FCB.EnableFoo"]["name"] == "Enable Foo"
    assert rows["fcs:FCB.EnableFoo"]["values"]["Default-aaa"]["raw"] == {"enabled": True, "scope": "org"}
    assert rows["fcs:FCB.EnableFoo"]["values"]["Default-aaa"]["display"] == '{"enabled":true,"scope":"org"}'
    assert rows["fcs:FCB.MultiLine"]["values"]["Default-aaa"]["raw"] == "line one\nline two"
    assert rows["fcs:FCB.NotBase64"]["values"]["Default-aaa"]["raw"] == "this is not base64!!"
    assert "fcs:FCB.Empty" not in rows, "empty content must not produce a row"
    # The environment we could not read must contribute no Dataverse values at all.
    assert "denied-bbb" not in rows["org:isauditenabled"]["values"], rows["org:isauditenabled"]

    categories = [c for c in collect.CATEGORY_ORDER if any(r["category"] == c for r in data["settings"])]
    assert categories == [c for c in collect.CATEGORY_ORDER if c in categories], "category ordering broken"

    from report import render_html

    html = render_html(data)
    assert "<table" in html and "Contoso (default)" in html
    out_dir = ROOT / "out"
    out_dir.mkdir(exist_ok=True)
    (out_dir / "smoke-report.html").write_text(html, encoding="utf-8")

    print(f"OK - {len(data['settings'])} settings x {len(data['environments'])} envs; categories: {categories}")


if __name__ == "__main__":
    main()
