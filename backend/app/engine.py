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

def analyze_contract_compliance(filename: str, full_contract_text: str, playbook_rule: str, model_name: str = "gemini-3.6-flash", mode: str = "compliance") -> ContractAnalysisResponse:
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

    if mode == "abstraction":
            prompt = f"""
            You are an expert corporate lawyer. Perform a "blind" abstraction on the following contract.
            Extract the most critical terms: Core Obligations, Rights, Financials, and Termination Conditions.
            
            Set 'is_compliant' to true.
            For the 'summary', provide a 2-3 sentence high-level overview of what this agreement actually is.
            
            For 'flagged_clauses', create one entry for each critical term you find:
            - clause_title: The category (e.g., "Termination Rights", "Payment Terms", "Intellectual Property")
            - risk_level: MUST be "INFO"
            - reason: A plain-English explanation of what this specific term means for the parties.
            - proposed_redline: "N/A"
            - original_text: The exact verbatim substring from the contract that proves this.
            
            Contract Name: 
            {filename}
    
            Contract Text:
            {full_contract_text}
            """
    else:
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
    
    
            prompt = f"""
            You are a Senior Legal Compliance Officer.
            Evaluate the provided contract excerpts strictly against the Legal Playbook Rule.
                    
            LEGAL PLAYBOOK RULE:
            {playbook_rule}
                    
            CONTRACT EXCERPTS:
            {context_text}
                    
            INSTRUCTIONS:
            - Identify any clauses that violate or deviate from the rule.
            - When extracting 'original_text', copy the EXACT substring from the excerpts so it can be matched via substring search.
            - Propose actionable, safer redline revisions.
            """

    # Setup Gemini with Structured Output
    llm = ChatGoogleGenerativeAI(
        model=model_name,
        temperature=0,
        google_api_key=os.getenv("GOOGLE_API_KEY")
    )
    structured_llm = llm.with_structured_output(ContractAnalysisResponse)
    
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

from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
import pypdf

def process_and_vectorize_file(file_path: str, filename: str) -> str:
    """Extracts text from a file, chunks it, and saves it to Qdrant."""

    try:
        delete_custom_document(filename)
    except Exception:
        pass # If it fails (e.g., file doesn't exist yet), just move on
    
    # Extract Text based on file type
    text = ""
    if filename.lower().endswith(".pdf"):
        reader = pypdf.PdfReader(file_path)
        for page in reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted + "\n"
    else:
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            text = f.read()
            
    if not text.strip():
        raise ValueError("Could not extract text. The PDF might be an image/scan.")

    # Split into semantic chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", ".", " ", ""]
    )
    chunks = text_splitter.split_text(text)
    
    # Attach metadata (so Qdrant knows which file this chunk belongs to)
    docs = [Document(page_content=chunk, metadata={"source": filename}) for chunk in chunks]
    
    # Connect to Qdrant and upload
    QdrantVectorStore.from_documents(
        docs,
        embeddings,
        url=QDRANT_URL,
        collection_name=COLLECTION_NAME
    )
    
    return text # Return the raw text so the Streamlit viewer can display it

def delete_custom_document(filename: str):
    """Deletes all vectorized chunks of a specific document from Qdrant."""
    client = QdrantClient(url=QDRANT_URL) 
    
    # Execute a delete-by-filter operation
    client.delete(
        collection_name=COLLECTION_NAME,
        points_selector=models.FilterSelector(
            filter=models.Filter(
                must=[
                    models.FieldCondition(
                        key="metadata.source",
                        match=models.MatchValue(value=filename)
                    )
                ]
            )
        )
    )
    print(f"SUCCESS: Wiped all vectors for {filename} from Qdrant.")


def chat_with_document(filename: str, query: str, model_name: str):
    """Retrieves context from Qdrant and answers a user's question about the contract."""
    
    # Connect to Qdrant Vector Store
    client = QdrantClient(url=QDRANT_URL)
    qdrant = QdrantVectorStore(client=client, collection_name=COLLECTION_NAME, embedding=embeddings)
    
    # Perform the Vector Search restricted to this specific file
    search_results = qdrant.similarity_search(
        query=query,
        k=4, # Grab the 4 most relevant chunks
        filter=models.Filter(
            must=[models.FieldCondition(key="metadata.source", match=models.MatchValue(value=filename))]
        )
    )
    
    # Combine the retrieved chunks into a single context string
    context_text = "\n\n".join([doc.page_content for doc in search_results])
    
    # Build a strict Q&A prompt to prevent hallucinations
    prompt = f"""
    You are a highly precise legal AI assistant. 
    Answer the user's question using ONLY the following excerpts from their uploaded contract.
    If the answer is not contained in the excerpts, simply say, "I cannot find the answer to this in the document."
    Do not make up outside legal information or assume standard contract terms.
    
    Contract Excerpts:
    {context_text}
    
    User Question: {query}
    """
    
    # Call Gemini (Standard text generation, no Pydantic schema needed)
    llm = ChatGoogleGenerativeAI(model=model_name, temperature=0.2)
    response = llm.invoke(prompt)
    
    answer = response.content

    # If Gemini returns a list of blocks, extract the text from the first block
    if isinstance(answer, list) and len(answer) > 0:
        answer = answer[0].get("text", str(answer))
        
    return answer