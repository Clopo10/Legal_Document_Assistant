"""
Core Analysis Engine
--------------------
Coordonates Qdrant vector retrieval, Gemini structured reasoning,
and character index calculation for frontend highlighting.
"""

import os
import time
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from app.schemas import ContractAnalysisResponse
from qdrant_client.http import models

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
COLLECTION_NAME = "legal_contracts"

# Embedding model loaded in memory
embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")

def get_llm():
    return ChatGoogleGenerativeAI(
        model="gemini-3.6-flash",
        temperature=0,
        max_retries=3
    )

def analyze_contract_compliance(filename: str, full_contract_text: str, playbook_rule: str, model_name: str = "gemini-3.6-flash") -> ContractAnalysisResponse:
    start_time = time.time()
    
    # Connect to Qdrant
    client = QdrantClient(url=QDRANT_URL)
    qdrant = QdrantVectorStore(client=client, collection_name=COLLECTION_NAME, embedding=embeddings)

    # Account for how Windows vs Mac/Linux saves file paths in LangChain
    possible_sources = [
        filename,                                  # e.g., "contract_1.txt"
        f"data/sample_contracts/{filename}",       # Mac/Linux path
        f"data\\sample_contracts\\{filename}",     # Windows path
        f"../data/sample_contracts/{filename}"     # Relative path
    ]
    
    # Retrieve top chunks ONLY from the selected contract
    retriever = qdrant.as_retriever(
        search_type="similarity_score_threshold",
        search_kwargs={
            "score_threshold": 0.65,
            "k": 20,
            "filter": models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.source",
                        match=models.MatchAny(any=possible_sources) # Filters by the selected file
                    )
                ]
            )
        }
    )
    retrieved_docs = retriever.invoke(playbook_rule)
    print(f"DEBUG: Qdrant returned {len(retrieved_docs)} chunks passing the threshold.")
    context_text = "\n\n---\n\n".join([doc.page_content for doc in retrieved_docs])

    # Setup Gemini with Structured Output
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0,
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    structured_llm = llm.with_structured_output(ContractAnalysisResponse)

    prompt_template = PromptTemplate(
        input_variables=["rule", "context"],
        template="""
        You are a Senior Legal Compliance Officer.
        Evaluate the provided contract excerpts strictly against the Legal Playbook Rule.
        
        LEGAL PLAYBOOK RULE:
        {rule}
        
        CONTRACT EXCERPTS:
        {context}
        
        INSTRUCTIONS:
        - Identify any clauses that violate or deviate from the rule.
        - When extracting 'original_text', copy the EXACT substring from the excerpts so it can be matched via substring search.
        - Propose actionable, safer redline revisions.
        """
    )

    prompt = prompt_template.format(rule=playbook_rule, context=context_text)
    
    # Invoke the model (Gemini only handles the legal stuff)
    result_pydantic: ContractAnalysisResponse = structured_llm.invoke(prompt)
    
    # Convert the Pydantic object to a standard Python dictionary
    final_response = result_pydantic.model_dump()
    
    # Calculate Latency
    latency = round(time.time() - start_time, 3)
    final_response["latency_seconds"] = latency
    
    # Rough token estimation for logging (1 token ≈ 4 chars)
    est_input_tokens = len(prompt) // 4
    final_response["input_tokens"] = est_input_tokens
    
    # Dynamic Pricing Calculator
    if "3.8" in model_name.lower():
        price_per_million = 0.15  # 3.8 Flash pricing
    else:
        price_per_million = 0.075 # 3.6 Flash pricing
        
    final_response["estimated_cost_usd"] = round((est_input_tokens / 1_000_000) * price_per_million, 6)

    # Return the dictionary to FastAPI (FastAPI automatically converts dicts to JSON)
    return final_response