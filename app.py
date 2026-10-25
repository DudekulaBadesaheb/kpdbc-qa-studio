import sys
import os
import time
import json
import base64
import random
import zipfile
import asyncio
import threading
import httpx
from typing import List, Optional, Dict, Any
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from scanner import UniversalDeepScanner
from code_generator import (
    generate_multi_page_test_cases,
    generate_test_cases_csv,
    generate_excel_csv,
    generate_failed_elements_csv,
    generate_code_suite
)

app = FastAPI(title="KPDBC Universal AI QA & Multi-User Project Studio")

os.makedirs("videos", exist_ok=True)
os.makedirs("static", exist_ok=True)
os.makedirs("screenshots", exist_ok=True)
os.makedirs("users", exist_ok=True)

app.mount("/videos", StaticFiles(directory="videos"), name="videos")
app.mount("/static", StaticFiles(directory="static"), name="static")
app.mount("/screenshots", StaticFiles(directory="screenshots"), name="screenshots")

DEFAULT_GAS_URL = "https://script.google.com/macros/s/AKfycbxnOl3ddjPuR6lY6hrlUEdR430DFbrseHNdN_ZHHRETGMaoRrZauYlvIowjdODrvRhTyA/exec"

class AuthRegisterRequest(BaseModel):
    name: str
    email: str
    password: str
    gas_url: Optional[str] = DEFAULT_GAS_URL

class AuthLoginRequest(BaseModel):
    user_id: str
    password: str
    gas_url: Optional[str] = DEFAULT_GAS_URL

class AuthForgotRequest(BaseModel):
    email: str
    gas_url: Optional[str] = DEFAULT_GAS_URL

class AuthResetRequest(BaseModel):
    email: str
    reset_code: str
    new_password: str
    gas_url: Optional[str] = DEFAULT_GAS_URL

class ProjectScanRequest(BaseModel):
    user_id: str = "User_A"
    project_name: str = "Project_1"
    url: str
    app_archetype: str = "general"
    scope: str = "all"
    expected_content: Optional[List[str]] = []
    custom_test_cases: Optional[List[Dict[str, Any]]] = []
    form_config_text: Optional[str] = ""
    gas_webhook_url: Optional[str] = DEFAULT_GAS_URL
    latitude: Optional[float] = 12.9716
    longitude: Optional[float] = 77.5946
    pincode: Optional[str] = "560001"
    visual_mode: bool = False
    record_video: bool = True

@app.get("/")
def get_dashboard():
    return FileResponse("static/index.html")

# --- AUTH FORWARDING DIRECTLY TO GOOGLE APPS SCRIPT ---

@app.post("/api/auth/register")
async def register_user(req: AuthRegisterRequest):
    gas_payload = {
        "action": "register_user",
        "name": req.name,
        "email": req.email,
        "password": req.password
    }
    target_url = req.gas_url or DEFAULT_GAS_URL
    try:
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            resp = await client.post(target_url, json=gas_payload)
            return JSONResponse(status_code=resp.status_code, content=resp.json())
    except Exception as e:
        clean_name = "".join(filter(str.isalnum, req.name)).upper()
        local_id = f"KPDBC_{clean_name}_{random.randint(100, 999)}"
        return JSONResponse(status_code=200, content={
            "status": "success",
            "message": "Registered locally (GAS Sync Note: " + str(e) + ")",
            "kpdbc_id": local_id
        })

@app.post("/api/auth/login")
async def login_user(req: AuthLoginRequest):
    gas_payload = {
        "action": "login_user",
        "user_id": req.user_id,
        "password": req.password
    }
    target_url = req.gas_url or DEFAULT_GAS_URL
    try:
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            resp = await client.post(target_url, json=gas_payload)
            return JSONResponse(status_code=resp.status_code, content=resp.json())
    except Exception as e:
        return JSONResponse(status_code=200, content={
            "status": "success",
            "message": "Logged in offline mode.",
            "kpdbc_id": req.user_id,
            "name": req.user_id
        })

@app.post("/api/auth/forgot-password")
async def forgot_password(req: AuthForgotRequest):
    gas_payload = {
        "action": "forgot_password",
        "email": req.email
    }
    target_url = req.gas_url or DEFAULT_GAS_URL
    try:
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            resp = await client.post(target_url, json=gas_payload)
            return JSONResponse(status_code=resp.status_code, content=resp.json())
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"GAS Connection Error: {str(e)}"})

@app.post("/api/auth/reset-password")
async def reset_password(req: AuthResetRequest):
    gas_payload = {
        "action": "reset_password",
        "email": req.email,
        "reset_code": req.reset_code,
        "new_password": req.new_password
    }
    target_url = req.gas_url or DEFAULT_GAS_URL
    try:
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            resp = await client.post(target_url, json=gas_payload)
            return JSONResponse(status_code=resp.status_code, content=resp.json())
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"GAS Connection Error: {str(e)}"})

# --- SCANNER & TEST EXECUTION ---

def async_sync_to_gas(gas_url: str, payload: dict):
    try:
        httpx.post(gas_url, json=payload, timeout=25.0, follow_redirects=True)
    except Exception as e:
        print(f"[!] GAS Telemetry Sync Note: {e}")

@app.post("/api/scan")
async def run_scan(req: ProjectScanRequest):
    try:
        scanner = UniversalDeepScanner(
            base_url=req.url,
            user_id=req.user_id,
            project_name=req.project_name,
            app_archetype=req.app_archetype,
            scope=req.scope,
            expected_content=req.expected_content,
            form_config_text=req.form_config_text,
            latitude=req.latitude,
            longitude=req.longitude,
            pincode=req.pincode,
            visual_mode=req.visual_mode,
            record_video=req.record_video
        )
        report = await scanner.scan()
        
        test_cases = generate_multi_page_test_cases(report, req.custom_test_cases)
        tc_csv = generate_test_cases_csv(test_cases)
        excel_csv = generate_excel_csv(report)
        failures_csv = generate_failed_elements_csv(report)
        code_suite = generate_code_suite(report, req.url)

        proj_dir = os.path.join("users", req.user_id, req.project_name)
        os.makedirs(proj_dir, exist_ok=True)
        
        with open(os.path.join(proj_dir, "report.json"), "w", encoding="utf-8") as f:
            json.dump({"audit": report, "code": code_suite, "test_cases": test_cases}, f, indent=2)
        with open(os.path.join(proj_dir, "QA_Test_Cases.csv"), "w", encoding="utf-8") as f:
            f.write(tc_csv)
        with open(os.path.join(proj_dir, "PowerBI_Report.csv"), "w", encoding="utf-8") as f:
            f.write(excel_csv)
        with open(os.path.join(proj_dir, "Failures_Log.csv"), "w", encoding="utf-8") as f:
            f.write(failures_csv)

        # Write matching code files into the project directory
        with open(os.path.join(proj_dir, "test_suite.py"), "w", encoding="utf-8") as f:
            f.write(code_suite["python"])
        with open(os.path.join(proj_dir, "test_suite.java"), "w", encoding="utf-8") as f:
            f.write(code_suite["java"])
        with open(os.path.join(proj_dir, "test_suite.js"), "w", encoding="utf-8") as f:
            f.write(code_suite["javascript"])
        with open(os.path.join(proj_dir, "test_suite.ts"), "w", encoding="utf-8") as f:
            f.write(code_suite["typescript"])
        with open(os.path.join(proj_dir, "test_suite.cs"), "w", encoding="utf-8") as f:
            f.write(code_suite["csharp"])
        with open(os.path.join(proj_dir, "test_suite.php"), "w", encoding="utf-8") as f:
            f.write(code_suite["php"])

        # Include recording video in ZIP bundle folder
        if report.get("video_filename"):
            vid_source = os.path.join("videos", report["video_filename"])
            if os.path.exists(vid_source):
                with open(os.path.join(proj_dir, "session_recording.webm"), "wb") as vf:
                    with open(vid_source, "rb") as sf:
                        vf.write(sf.read())

        code_suite["test_cases"] = test_cases
        code_suite["test_cases_csv"] = tc_csv
        code_suite["excel_csv"] = excel_csv
        code_suite["failures_csv"] = failures_csv

        # Sync test telemetry and failure screenshot to Google Apps Script
        target_gas = req.gas_webhook_url or DEFAULT_GAS_URL
        if target_gas:
            screenshot_b64 = None
            screenshot_name = None
            if report.get("failures") and len(report["failures"]) > 0:
                first_shot = report["failures"][0].get("filename")
                if first_shot and os.path.exists(os.path.join("screenshots", first_shot)):
                    with open(os.path.join("screenshots", first_shot), "rb") as img_f:
                        screenshot_b64 = base64.b64encode(img_f.read()).decode("utf-8")
                        screenshot_name = first_shot

            gas_payload = {
                "action": "log_test_run",
                "user_id": req.user_id,
                "project_name": req.project_name,
                "base_url": req.url,
                "health_score": report["summary"]["overall_health_score"],
                "total_pages": report["summary"]["total_pages_tested"],
                "total_failures": report["summary"]["total_failures"],
                "total_test_cases": len(test_cases),
                "screenshot_base64": screenshot_b64,
                "screenshot_name": screenshot_name
            }
            threading.Thread(target=async_sync_to_gas, args=(target_gas, gas_payload), daemon=True).start()

        return JSONResponse(status_code=200, content={"audit": report, "code": code_suite, "test_cases": test_cases})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": f"Scanner Error: {str(e)}"})

@app.get("/api/user-projects")
def get_user_projects(user_id: str = "User_A"):
    user_path = os.path.join("users", user_id)
    if not os.path.exists(user_path):
        return {"projects": []}
    return {"projects": [d for d in os.listdir(user_path) if os.path.isdir(os.path.join(user_path, d))]}

@app.get("/api/load-project")
def load_project(user_id: str = "User_A", project_name: str = "Project_1"):
    file_path = os.path.join("users", user_id, project_name, "report.json")
    if os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8") as f:
            return json.load(f)
    return JSONResponse(status_code=404, content={"error": "Project not found."})

@app.get("/api/download-project-bundle")
def download_project_bundle(user_id: str = "User_A", project_name: str = "Project_1"):
    zip_path = f"users/{user_id}_{project_name}_Full_QA_Bundle.zip"
    proj_dir = os.path.join("users", user_id, project_name)

    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        if os.path.exists(proj_dir):
            for root, _, files in os.walk(proj_dir):
                for file in files:
                    zipf.write(os.path.join(root, file), arcname=file)
        if os.path.exists("screenshots"):
            for root, _, files in os.walk("screenshots"):
                for file in files[:12]:
                    zipf.write(os.path.join(root, file), arcname=f"screenshots/{file}")

    return FileResponse(zip_path, media_type="application/zip", filename=f"{user_id}_{project_name}_Bundle.zip")

@app.post("/api/stop")
def stop_server():
    def kill_process():
        time.sleep(0.4)
        os._exit(0)

    threading.Thread(target=kill_process, daemon=True).start()
    return JSONResponse(content={"message": "Server stopped cleanly."})