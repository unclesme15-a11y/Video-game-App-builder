"""Publish Android builds to the Amazon Appstore via the App Submission API.

Amazon developer accounts are free and the submission API is fully
scriptable: create edit -> replace APK -> commit edit. The app listing must
be created once by hand in the developer console; updates are automated.

Setup (one time):
1. Free account at developer.amazon.com
2. Create the app listing, note its App ID (amzn1.devportal.mobileapp....)
3. Create an LWA Security Profile, attach it to the App Submission API,
   set AMAZON_CLIENT_ID / AMAZON_CLIENT_SECRET

Env-only config (no engine imports) so this runs on the Nitro too.
"""

from __future__ import annotations

import os
from pathlib import Path

import requests

TOKEN_URL = "https://api.amazon.com/auth/o2/token"
BASE = "https://developer.amazon.com/api/appstore/v1"

CLIENT_ID = os.getenv("AMAZON_CLIENT_ID", "")
CLIENT_SECRET = os.getenv("AMAZON_CLIENT_SECRET", "")


def _token() -> str:
    r = requests.post(
        TOKEN_URL,
        data={
            "grant_type": "client_credentials",
            "client_id": CLIENT_ID,
            "client_secret": CLIENT_SECRET,
            "scope": "appstore::apps:readwrite",
        },
        timeout=30,
    )
    r.raise_for_status()
    return r.json()["access_token"]


def publish(apk_path: str, app_id: str) -> str:
    """Upload a new APK for an existing Amazon Appstore listing and submit it."""
    if not (CLIENT_ID and CLIENT_SECRET):
        raise RuntimeError("set AMAZON_CLIENT_ID / AMAZON_CLIENT_SECRET")
    headers = {"Authorization": f"Bearer {_token()}"}

    # 1. open an edit (or reuse the open one)
    r = requests.get(f"{BASE}/applications/{app_id}/edits", headers=headers, timeout=30)
    r.raise_for_status()
    edit = r.json()
    if not edit:
        r = requests.post(f"{BASE}/applications/{app_id}/edits", headers=headers, timeout=30)
        r.raise_for_status()
        edit = r.json()
    edit_id = edit["id"]

    # 2. replace the first APK in the edit
    r = requests.get(f"{BASE}/applications/{app_id}/edits/{edit_id}/apks", headers=headers, timeout=30)
    r.raise_for_status()
    apks = r.json()
    apk_id, etag = apks[0]["id"], apks[0]["etag"] if apks else (None, None)
    with open(apk_path, "rb") as f:
        if apk_id:
            r = requests.put(
                f"{BASE}/applications/{app_id}/edits/{edit_id}/apks/{apk_id}/replace",
                headers=headers | {"Content-Type": "application/vnd.android.package-archive", "If-Match": etag},
                data=f, timeout=600,
            )
        else:
            r = requests.post(
                f"{BASE}/applications/{app_id}/edits/{edit_id}/apks/upload",
                headers=headers | {"Content-Type": "application/vnd.android.package-archive"},
                data=f, timeout=600,
            )
    r.raise_for_status()

    # 3. commit the edit (submits for Amazon review)
    r = requests.get(f"{BASE}/applications/{app_id}/edits/{edit_id}", headers=headers, timeout=30)
    r.raise_for_status()
    r = requests.post(
        f"{BASE}/applications/{app_id}/edits/{edit_id}/commit",
        headers=headers | {"If-Match": r.json()["etag"]},
        timeout=30,
    )
    r.raise_for_status()
    return f"submitted {Path(apk_path).name} to Amazon Appstore app {app_id}"
