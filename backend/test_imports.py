#!/usr/bin/env python
"""Test which router imports hang."""
import sys
import time

routers = [
    ("auth", "from app.api.auth import router as auth_router"),
    ("analytics", "from app.api.analytics import router as analytics_router"),
    ("autonomous_agent", "from app.api.autonomous_agent import router as autonomous_agent_router"),
    ("donors", "from app.api.donors import router as donors_router"),
    ("embryos", "from app.api.embryos import router as embryos_router"),
    ("import_data", "from app.api.import_data import router as import_router"),
    ("grading", "from app.api.grading import router as grading_router"),
    ("health", "from app.api.health import router as health_router"),
    ("predictions", "from app.api.predictions import router as predictions_router"),
    ("protocols", "from app.api.protocols import router as protocols_router"),
    ("qc", "from app.api.qc import router as qc_router"),
    ("recipients", "from app.api.recipients import router as recipients_router"),
    ("sires", "from app.api.sires import router as sires_router"),
    ("technicians", "from app.api.technicians import router as technicians_router"),
    ("transfers", "from app.api.transfers import router as transfers_router"),
]

for name, import_stmt in routers:
    print(f"Testing {name}...", flush=True)
    try:
        exec(import_stmt)
        print(f"  ✓ {name} OK", flush=True)
    except Exception as e:
        print(f"  ✗ {name} failed: {e}", flush=True)
        break
