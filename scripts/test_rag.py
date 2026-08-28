"""
RAG Test Pipeline
-----------------
Tests the core Agentic workflow:
1. Embeds a Playbook rule.
2. Retrieves relevant contract chunks from Qdrant.
3. Passes the chunks + rule to Gemini to check for compliance.
"""

import os
from dotenv import load_dotenv
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate

# Load the environment variables
load_dotenv()

# Configuration
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "legal_contracts"

def run_rag_test():
    # Define Legal Playbook Rule
    # In a full app, this would be a JSON file or a database table.
    playbook_rule = "The governing law of the contract must be the State of Delaware."
    print(f"Rule: {playbook_rule}\n")

    #  Connect to the Local Vector Database
    print("Connecting to Qdrant and searching for relevant clauses...")
    embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
    client = QdrantClient(url=QDRANT_URL)
    
    qdrant = QdrantVectorStore(
        client=client, 
        collection_name=COLLECTION_NAME, 
        embedding=embeddings
    )

    # Retrieve the Top 3 most relevant chunks from our database
    # We use the playbook rule as the search query
    retriever = qdrant.as_retriever(search_kwargs={"k": 3})
    retrieved_docs = retriever.invoke(playbook_rule)
    
    # Combine the retrieved text chunks into one big string
    context_text = "\n\n---\n\n".join([doc.page_content for doc in retrieved_docs])
    print(f"Found {len(retrieved_docs)} relevant contract chunks.\n")

    # Initialize Google Gemini (The Brain)
    print("Sending context to Google Gemini for analysis...")
    llm = ChatGoogleGenerativeAI(
        model="gemini-3.6-flash", 
        temperature=0, 
        max_retries=3
    )

    # Define the LangChain Prompt
    # This instructs the AI exactly how to behave and what to output
    prompt_template = PromptTemplate(
        input_variables=["rule", "context"],
        template="""
        You are an expert corporate lawyer analyzing a contract.
        
        LEGAL PLAYBOOK RULE:
        {rule}
        
        CONTRACT EXCERPTS:
        {context}
        
        INSTRUCTIONS:
        1. Read the contract excerpts.
        2. Determine if the contract complies with the legal playbook rule.
        3. If it does not comply, explain why and draft a safer redlined revision.
        4. Be concise and professional.
        
        ANALYSIS:
        """
    )

    # Execute the Chain
    # We pipe the prompt into the LLM
    chain = prompt_template | llm
    
    response = chain.invoke({
        "rule": playbook_rule,
        "context": context_text
    })

    print("========================================")
    print("AI LEGAL ANALYSIS:")
    print("========================================")
    print(response.content)

if __name__ == "__main__":
    run_rag_test()