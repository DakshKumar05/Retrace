"""End-to-end check of every major endpoint. Run with: python smoke_test.py"""
from __future__ import annotations

import io
import secrets
import sys

from fastapi.testclient import TestClient

from app.config import settings
from app.main import app

FAILURES: list[str] = []


def check(name: str, condition: bool, extra: str = "") -> None:
    status = "PASS" if condition else "FAIL"
    print(f"[{status}] {name}{(' — ' + extra) if extra else ''}")
    if not condition:
        FAILURES.append(name)


def main() -> int:
    with TestClient(app) as client:
        health = client.get("/api/health").json()
        check("health", health["status"] == "ok", health["refund_mode"])

        login = client.post(
            "/api/auth/login",
            json={"email": settings.demo_email, "password": settings.demo_password},
        )
        check("login", login.status_code == 200, str(login.status_code))
        token = login.json()["access_token"]
        auth = {"Authorization": f"Bearer {token}"}

        check("login rejects bad password", client.post(
            "/api/auth/login", json={"email": settings.demo_email, "password": "wrong-password"}
        ).status_code == 401)
        check("protected route needs a token", client.get("/api/dashboard").status_code == 401)

        me = client.get("/api/auth/me", headers=auth).json()
        check("me", me["email"] == settings.demo_email, me["full_name"])

        dash = client.get("/api/dashboard", headers=auth).json()
        check("dashboard", "recent_transactions" in dash,
              f"{len(dash['recent_transactions'])} recent, alerts {dash['risk_alerts']}")

        txs = client.get("/api/transactions", headers=auth).json()
        check("transactions", len(txs) > 5, f"{len(txs)} rows")
        high = client.get("/api/transactions?filter=high_risk", headers=auth).json()
        check("transaction filter", len(high) >= 1, f"{len(high)} high risk")

        critical = high[0]
        detail = client.get(f"/api/transactions/{critical['reference']}", headers=auth).json()
        check("transaction detail", detail["reference"] == critical["reference"],
              f"{len(detail['events'])} behaviour events")

        analysis = client.post(
            "/api/risk/analyze-refund",
            headers=auth,
            json={
                "transaction_id": critical["reference"],
                "refund_amount": 8000,
                "original_sender": critical["sender_handle"],
                "refund_destination": "xyz987@upi",
                "time_since_payment": 180,
                "message": "Please send it back urgently to my wife's UPI, my account isn't working.",
            },
        ).json()
        check("refund safety score", analysis["risk_level"] == "CRITICAL",
              f"risk {analysis['risk_score']}, safety {analysis['safety_score']}, "
              f"{len(analysis['signals'])} signals")
        check("recommendation", analysis["recommendation"] == "DO_NOT_REFUND")

        low = client.post(
            "/api/risk/analyze-refund",
            headers=auth,
            json={
                "transaction_id": "TX-NOT-REAL",
                "refund_amount": 400,
                "original_sender": "priya.sharma@okaxis",
                "refund_destination": "priya.sharma@okaxis",
                "time_since_payment": 90000,
                "persist": False,
            },
        ).json()
        check("safe refund scores low", low["risk_score"] < 40,
              f"risk {low['risk_score']} ({low['risk_level']})")

        message = client.post(
            "/api/risk/analyze-message",
            headers=auth,
            json={"message": "Hi bro, I accidentally sent 8000 to you. Please send it to my wife's "
                             "UPI urgently. My account isn't working."},
        ).json()
        check("message analyzer", message["message_risk_score"] >= 61
              and message["recommendation"] == "DO_NOT_TRANSFER_MANUALLY",
              f"{message['message_risk_score']} {message['risk_level']}")

        benign = client.post(
            "/api/risk/analyze-message", headers=auth,
            json={"message": "Hey, sending the rent for this month as discussed. Thanks!"},
        ).json()
        check("benign message scores low", benign["message_risk_score"] <= 30,
              str(benign["message_risk_score"]))

        refunds = client.get("/api/refunds", headers=auth).json()
        pending = [r for r in refunds if r["status"] in {"PENDING", "BLOCKED"}]
        check("refund list", len(pending) >= 1, f"{len(refunds)} total")

        safe = client.post(
            "/api/refunds/safe", headers=auth, json={"refund_request_id": pending[0]["id"]}
        ).json()
        check("safe refund", safe["status"] == "PROCESSING", f"{safe['refund_id']} ({safe['mode']})")

        sim = client.post("/api/simulation/scam", headers=auth, json={"unsafe": True}).json()
        check("scam simulation", sim["incident"] is not None,
              f"case {sim['incident']['case_id']}, risk {sim['analysis']['risk_score']}")
        check("safe mode auto-on", sim["safe_mode_enabled"] is True)
        check("simulation steps", len(sim["steps"]) >= 6, f"{len(sim['steps'])} steps")

        incident_id = sim["incident"]["id"]
        incident = client.get(f"/api/incidents/{incident_id}", headers=auth).json()
        check("incident detail", incident["case_id"] == sim["incident"]["case_id"],
              f"{len(incident['events'])} timeline events, "
              f"{incident['completeness']['percent']}% complete")

        upload = client.post(
            "/api/evidence/upload",
            headers=auth,
            files={"file": ("complaint-ack.txt", io.BytesIO(b"Bank complaint acknowledgement 8891"), "text/plain")},
            data={"evidence_type": "complaint_acknowledgement", "incident_id": str(incident_id)},
        )
        check("evidence upload", upload.status_code == 201, str(upload.status_code))
        item = upload.json()
        check("sha-256 recorded", len(item["sha256"] or "") == 64, (item["sha256"] or "")[:12] + "…")

        verify = client.get(f"/api/evidence/{item['id']}/verify", headers=auth).json()
        check("hash verifies", verify["unchanged"] is True)

        rejected = client.post(
            "/api/evidence/upload",
            headers=auth,
            files={"file": ("payload.exe", io.BytesIO(b"MZ"), "application/octet-stream")},
            data={"evidence_type": "supporting_document"},
        )
        check("rejects disallowed file type", rejected.status_code == 415, str(rejected.status_code))

        completeness = client.get(
            f"/api/evidence/completeness?incident_id={incident_id}", headers=auth
        ).json()
        check("completeness", completeness["percent"] == 100,
              f"{completeness['percent']}%, missing {completeness['missing']}")

        report = client.post(
            "/api/reports/generate", headers=auth,
            json={"incident_id": incident_id, "include_package": True},
        )
        check("report generated", report.status_code == 201, str(report.status_code))
        rep = report.json()
        pdf = client.get(f"/api/reports/{rep['id']}/pdf", headers=auth)
        check("pdf download", pdf.status_code == 200 and pdf.content[:4] == b"%PDF",
              f"{len(pdf.content) // 1024} KB")
        pkg = client.get(f"/api/reports/{rep['id']}/package", headers=auth)
        check("evidence package", pkg.status_code == 200 and pkg.content[:2] == b"PK",
              f"{len(pkg.content) // 1024} KB")

        patched = client.patch(
            f"/api/incidents/{incident_id}", headers=auth,
            json={"status": "SUBMITTED", "bank_complaint_ref": "SBI/CMP/88213"},
        ).json()
        check("incident status change", patched["status"] == "SUBMITTED")

        client.post("/api/protection/release", headers=auth)
        protection = client.post(
            "/api/protection/activate", headers=auth, json={"amount": 42000}
        ).json()
        check("emergency protection", protection["protection_active"] is True)
        after = client.get("/api/auth/me", headers=auth).json()
        check("protected balance moved", after["protected_balance"] == 42000.0,
              f"Rs {after['protected_balance']:,.0f}")

        stats = client.get("/api/admin/statistics", headers=auth).json()
        check("admin statistics", stats["total_transactions"] > 100_000,
              f"{stats['total_transactions']:,} transactions, "
              f"{len(stats['transactions_over_time'])} day series")

        feed = client.get("/api/admin/risk-feed", headers=auth).json()
        check("risk feed", len(feed) > 0, f"{len(feed)} items")

        network = client.get("/api/admin/fraud-network", headers=auth).json()
        clusters = network["clusters"]
        check("fraud network", len(clusters) >= 1,
              f"{len(clusters)} clusters, largest has {clusters[0]['victim_count']} victims "
              f"and {clusters[0]['destination_count']} destinations"
              if clusters else "none")
        if clusters:
            graph = clusters[0]["graph"]
            check("graph laid out", all("x" in n for n in graph["nodes"]),
                  f"{len(graph['nodes'])} nodes / {len(graph['edges'])} edges")

        model = client.get("/api/risk/model-info", headers=auth).json()
        check("ml model", "accuracy" in model,
              f"accuracy {model.get('accuracy')}, auc {model.get('roc_auc')}")

        reg = client.post(
            "/api/auth/register",
            json={
                "email": f"new.user+{secrets.token_hex(4)}@example.com",
                "full_name": "New User",
                "password": "Passw0rd!23",
            },
        )
        check("register", reg.status_code == 201, str(reg.status_code))
        new_auth = {"Authorization": f"Bearer {reg.json()['access_token']}"}
        check("rbac blocks non-admin", client.get("/api/admin/statistics", headers=new_auth).status_code == 403)
        empty = client.get("/api/transactions", headers=new_auth).json()
        check("new account starts empty", empty == [], f"{len(empty)} rows")

        reset = client.post("/api/simulation/reset", headers=auth)
        check("demo reset", reset.status_code == 200)

    print()
    if FAILURES:
        print(f"{len(FAILURES)} check(s) failed: {', '.join(FAILURES)}")
        return 1
    print("All checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
