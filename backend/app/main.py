"""
FastAPI Server Entry Point
--------------------------
Provides REST API endpoints for uploading contracts and analyzing compliance.
"""

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.engine import analyze_contract_compliance
from app.schemas import ContractAnalysisResponse

app = FastAPI(
    title="Legal Document Assistant",
    version="1.0.0"
)

class AnalysisRequest(BaseModel):
    contract_text: str
    playbook_rule: str

@app.get("/")
def health_check():
    return {"status": "healthy", "service": "Legal Document Assistant API"}

@app.post("/analyze", response_model=ContractAnalysisResponse)
def analyze(request: AnalysisRequest):
    try:
        response = analyze_contract_compliance(
            full_contract_text=request.contract_text,
            playbook_rule=request.playbook_rule
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))