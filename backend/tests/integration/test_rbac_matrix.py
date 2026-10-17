"""The four-role permission matrix, encoded row for row.

Each row is one function, a representative endpoint, and the roles that may use
it. For writes the probe sends an empty body to an id that does not exist:

  * an allowed role reaches the handler and fails validation or lookup (any
    status except 401/403);
  * a refused role is stopped by the permission check before anything is read (403).

For reads the allowed roles must get 200.
"""

from __future__ import annotations

import uuid

import pytest

from app.auth.security import hash_password
from app.models.user import User

PASSWORD = "Str0ng!Passw0rd"
ROLES = ["admin", "embryologist", "veterinarian", "researcher"]

# (function, method, path, allowed roles, kind)
MATRIX = [
    ("User management",            "GET",   "/admin/users",                                       {"admin"},                          "read"),
    ("Lab data entry",             "POST",  "/opu-sessions/",                                     {"admin", "embryologist"},          "write"),
    ("OPU / IVF",                  "POST",  "/ivf-batches/",                                      {"admin", "embryologist"},          "write"),
    ("Embryo grading",             "POST",  "/grade/embryo",                                      {"admin", "embryologist"},          "write"),
    ("Recipient / ET",             "POST",  "/recipients/",                                       {"admin", "veterinarian"},          "write"),
    ("Synchronization",            "POST",  "/vet/enrollments",                                   {"admin", "veterinarian"},          "write"),
    ("Pregnancy diagnosis",        "POST",  "/vet/transfers/999999/pregnancy-checks",             {"admin", "veterinarian"},          "write"),
    ("Run prediction",             "POST",  "/predict/pregnancy",                                 {"admin", "embryologist", "veterinarian"}, "write"),
    ("Record prediction outcome",  "PATCH", "/predict/999999/outcome",                            {"admin", "veterinarian"},          "write"),
    ("Analytics",                  "GET",   "/analytics/kpis",                                    {"admin", "researcher"},            "read"),
    ("Research / model performance", "GET", "/research/donor-sire",                              {"admin", "researcher"},            "read"),
    ("Research / model performance", "GET", "/predict/performance",                              {"admin", "researcher"},            "read"),
    ("Reports",                    "GET",   "/reports/datasets",                                  {"admin", "embryologist", "veterinarian", "researcher"}, "read"),
]


def _headers_for(client, db_session, role: str) -> dict:
    admin = db_session.query(User).filter(User.username == "admin").first()
    username = f"rbac_{role}_{uuid.uuid4().hex[:6]}"
    db_session.add(User(username=username, password_hash=hash_password(PASSWORD), role=role,
                        active=True, organization_id=admin.organization_id))
    db_session.commit()
    r = client.post("/auth/login", data={"username": username, "password": PASSWORD})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.fixture(scope="module")
def _unused():
    return None


@pytest.mark.integration
@pytest.mark.parametrize("function, method, path, allowed, kind", MATRIX,
                         ids=[f"{m[0]}::{m[2]}" for m in MATRIX])
@pytest.mark.parametrize("role", ROLES)
def test_matrix_row(client, db_session, admin_user, function, method, path, allowed, kind, role):
    headers = _headers_for(client, db_session, role)
    if method == "GET":
        r = client.get(path, headers=headers)
    else:
        r = client.request(method, path, headers=headers, json={})

    if role in allowed:
        if kind == "read":
            assert r.status_code == 200, f"{role} should read {function} ({path}): {r.status_code} {r.text[:160]}"
        else:
            assert r.status_code not in (401, 403), (
                f"{role} should be allowed {function} ({path}) but was refused: {r.status_code}")
    else:
        assert r.status_code == 403, (
            f"{role} should be refused {function} ({path}) but got {r.status_code}")
