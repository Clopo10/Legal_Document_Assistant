"""
Data Schemas for Legal Document Assistant
-----------------------------------------
Defines strict Pydantic models for LLM structured output,
API requests, and API responses.
"""

from typing import List, Optional
from pydantic import BaseModel, Field

class FlaggedClause(BaseModel):
    clause_title: str = Field(
        description="The section name or clause number (e.g. 'Section 14: Construction')"
    )
    original_text: str = Field(
        description="The EXACT verbatim text from the contract that violates the rule."
    )
    risk_level: str = Field(
        description="Severity of the non-compliance: 'HIGH', 'MEDIUM', or 'LOW'."
    )
    reason: str = Field(
        description="Explanation of why this violates the legal playbook rule."
    )
    proposed_redline: str = Field(
        description="A safer, compliant revision of the clause."
    )

class ContractAnalysisResponse(BaseModel):
    is_compliant: bool = Field(
        description="True if all clauses comply with the playbook rule, False otherwise."
    )
    summary: str = Field(
        description="High-level summary of the compliance review."
    )
    flagged_clauses: List[FlaggedClause] = Field(
        default=[], 
        description="List of all non-compliant clauses found."
    )
    # Metadata for cost & latency tracking
    latency_seconds: Optional[float] = None
    input_tokens: Optional[int] = None
    output_tokens: Optional[int] = None
    estimated_cost_usd: Optional[float] = None