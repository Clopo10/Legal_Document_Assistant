"""
FastAPI Server Entry Point
--------------------------
Provides REST API endpoints for uploading contracts and analyzing compliance.
"""

import traceback
from fastapi.responses import JSONResponse

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from app.engine import analyze_contract_compliance, process_and_vectorize_file, delete_custom_document
from app.database import save_analysis, get_all_history, delete_history_record
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
    mode: str = "compliance"  # or "abstraction"

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
            model_name=request.model,
            mode=request.mode
        )

        save_analysis(
            filename=request.filename,
            playbook_rule=request.playbook_rule,
            result_dict=response,
            model_used=request.model
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

from fastapi import File, UploadFile
import tempfile
import os

@app.post("/upload")
async def upload_document(file: UploadFile = File(...)):
    try:
        # Save the uploaded file to a temporary location
        extension = os.path.splitext(file.filename)[1]
        with tempfile.NamedTemporaryFile(delete=False, suffix=extension) as temp:
            content = await file.read()
            temp.write(content)
            temp_path = temp.name

        # Extract text and vectorize into Qdrant
        raw_text = process_and_vectorize_file(temp_path, file.filename)
        
        # Clean up the temp file
        os.remove(temp_path)
        
        return {"filename": file.filename, "text": raw_text, "message": "Vectorization complete"}
        
    except Exception as e:
        error_msg = traceback.format_exc()
        print("\n=== UPLOAD CRASH ===")
        print(error_msg)
        return JSONResponse(status_code=500, content={"detail": str(e)})

class CleanupRequest(BaseModel):
    filename: str

@app.post("/cleanup")
def cleanup_document(request: CleanupRequest):
    try:
        delete_custom_document(request.filename)
        return {"message": f"Successfully deleted vectors for {request.filename}"}
    except Exception as e:
        error_msg = traceback.format_exc()
        print("\n=== CLEANUP CRASH ===")
        print(error_msg)
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.get("/history")
def fetch_history():
    try:
        data = get_all_history()
        return {"history": data}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})

@app.delete("/history/{record_id}")
def delete_history(record_id: int):
    try:
        delete_history_record(record_id)
        return {"message": "Record deleted successfully."}
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": str(e)})