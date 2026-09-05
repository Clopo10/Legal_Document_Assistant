"""
FastAPI Server Entry Point
--------------------------
Provides REST API endpoints for uploading contracts and analyzing compliance.
"""

import traceback
from fastapi.responses import JSONResponse

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.engine import analyze_contract_compliance
from app.schemas import ContractAnalysisResponse

app = FastAPI(
    title="Legal Document Assistant",
    version="1.0.0"
)

class AnalysisRequest(BaseModel):
    filename: str
    contract_text: str
    playbook_rule: str
    model: str = "gemini-3.6-flash"

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "Legal Document Assistant API"}

@app.post("/analyze", response_model=ContractAnalysisResponse)
def analyze(request: AnalysisRequest):
    try:
        response = analyze_contract_compliance(
            filename=request.filename,
            full_contract_text=request.contract_text,
            playbook_rule=request.playbook_rule,
            model_name=request.model
        )
        return response
    except Exception as e:
        # Intercept the crash and force it to print to the terminal
        error_msg = traceback.format_exc()
        print("\n" + "="*60)
        print("FATAL BACKEND CRASH")
        print("="*60)
        print(error_msg)
        print("="*60 + "\n")
        
        # Return the error cleanly so it doesn't just hang
        return JSONResponse(status_code=500, content={"detail": str(e)})