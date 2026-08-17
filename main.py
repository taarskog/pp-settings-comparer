#!/usr/bin/env python3
"""Build a settings/features matrix across every Power Platform environment in a tenant.

Usage:
  python main.py                    # collect live data, write out/report.html
  python main.py --sample           # render bundled sample data (no network)
  python main.py --max-envs 3 --open
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import webbrowser
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

from collect import collect  # noqa: E402
from ppapi import ApiError, TokenProvider  # noqa: E402
from report import render_html  # noqa: E402


def read_config(env_file: Path) -> dict[str, str]:
    """Reads KEY=value pairs; real environment variables win.

    Values are never exported to os.environ, so the secret is not inherited by the browser
    process that --open spawns.
    """
    values: dict[str, str] = {}
    if env_file.exists():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            values[key.strip()] = _unquote(value.strip())
    for key in ("PP_TENANT_ID", "PP_CLIENT_ID", "PP_CLIENT_SECRET"):
        if os.environ.get(key):
            values[key] = os.environ[key]
    return values


def _unquote(value: str) -> str:
    if len(value) > 1 and value[0] == value[-1] and value[0] in "\"'":
        return value[1:-1]
    return value


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", default=str(ROOT / "out" / "report.html"), help="HTML report path")
    parser.add_argument("--json", dest="json_out", help="also dump the collected data as JSON")
    parser.add_argument("--sample", action="store_true", help="render bundled sample data instead of calling Azure")
    parser.add_argument("--env-file", default=str(ROOT / ".env"), help="file holding PP_TENANT_ID/CLIENT_ID/SECRET")
    parser.add_argument("--env-filter", help="only environments whose display name contains this text")
    parser.add_argument("--max-envs", type=int, help="stop after the first N environments")
    parser.add_argument("--skip-dataverse", action="store_true", help="skip all per-environment Dataverse calls")
    parser.add_argument("--skip-ppapi", action="store_true", help="skip the Power Platform API settings call")
    parser.add_argument("--workers", type=int, default=6, help="environments collected in parallel (default 6)")
    parser.add_argument("--open", dest="open_browser", action="store_true", help="open the report when done")
    args = parser.parse_args()

    if args.max_envs is not None and args.max_envs < 1:
        parser.error("--max-envs must be 1 or greater")

    if args.sample:
        from sample_data import SAMPLE

        data = SAMPLE
    else:
        config = read_config(Path(args.env_file))
        tenant = config.get("PP_TENANT_ID")
        client_id = config.get("PP_CLIENT_ID")
        secret = config.get("PP_CLIENT_SECRET")
        if not (tenant and client_id and secret):
            print(
                "Missing PP_TENANT_ID / PP_CLIENT_ID / PP_CLIENT_SECRET.\n"
                "Run: pwsh -File deploy/Deploy-AppRegistration.ps1",
                file=sys.stderr,
            )
            return 2
        try:
            data = collect(
                TokenProvider(tenant, client_id, secret),
                tenant,
                env_filter=args.env_filter,
                max_envs=args.max_envs,
                skip_dataverse=args.skip_dataverse,
                skip_ppapi=args.skip_ppapi,
                workers=args.workers,
            )
        except ApiError as e:
            print(f"\nFailed: {e}", file=sys.stderr)
            if e.status in (401, 403):
                print(
                    "The service principal is not registered as a Power Platform management app.\n"
                    "Run deploy/Deploy-AppRegistration.ps1 as a tenant admin.",
                    file=sys.stderr,
                )
            return 1

    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(render_html(data), encoding="utf-8")

    if args.json_out:
        json_path = Path(args.json_out)
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
        print(f"Data:   {json_path}")

    print(f"\n{len(data['settings'])} settings x {len(data['environments'])} environments")
    print(f"Report: {out_path}")
    if args.open_browser:
        webbrowser.open(out_path.as_uri())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
