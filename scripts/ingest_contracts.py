"""
Document Ingestion & Chunking Pipeline
--------------------------------------
Loads text contracts, chunks them safely using LangChain, 
embeds them using a local Hugging Face model, and stores 
them in local Qdrant Docker container.
"""

import os
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_qdrant import QdrantVectorStore
from qdrant_client import QdrantClient
from qdrant_client.http.models import Distance, VectorParams

#  Configuration variables
DATA_DIR = "data/sample_contracts"
QDRANT_URL = "http://localhost:6333"
COLLECTION_NAME = "legal_contracts"

def ingest_data():
    # Load the raw text files
    print("Loading text files from directory...")
    # DirectoryLoader grabs every .txt file in the target folder
    loader = DirectoryLoader(
        DATA_DIR, 
        glob="**/*.txt", 
        loader_cls=TextLoader,
        loader_kwargs={'autodetect_encoding': True} # Handles weird legal text encodings
    )
    documents = loader.load()
    print(f"Loaded {len(documents)} contracts.")

    # Chunk the documents
    print("Chunking documents...")
    # RecursiveCharacterTextSplitter safely splits text without breaking clauses
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,      
        chunk_overlap=200,  
        separators=["\n\n", "\n", ".", " ", ""] # Strict hierarchy: paragraphs -> sentences -> words
    )
    chunks = text_splitter.split_documents(documents)
    print(f"Created {len(chunks)} overlapping chunks.")

    # Initialize Local Embeddings
    print("Initializing local Hugging Face embedding model...")

    embeddings = HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2"
    )

    # Connect to Qdrant and Save the Vectors
    print("Connecting to local Qdrant database...")
    client = QdrantClient(url=QDRANT_URL)
    
    # Check if collection exists; if not, create it with the correct vector size (384 for MiniLM)
    if not client.collection_exists(collection_name=COLLECTION_NAME):
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE),
        )

    print("Embedding chunks and uploading to Qdrant...")
    # This automatically embeds the text and saves the vector + original text to Qdrant
    qdrant = QdrantVectorStore(
        client=client, 
        collection_name=COLLECTION_NAME, 
        embedding=embeddings
    )
    
    # Insert chunks in batches
    qdrant.add_documents(chunks)
    print("Ingestion complete! The contracts are now vectorized and searchable.")

if __name__ == "__main__":
    ingest_data()