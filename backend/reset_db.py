from qdrant_client import QdrantClient

QDRANT_URL = "http://localhost:6333" 
COLLECTION_NAME = "legal_contracts"

def wipe_database():
    client = QdrantClient(url=QDRANT_URL)
    
    # This completely deletes the collection and all vectors inside it
    client.delete_collection(collection_name=COLLECTION_NAME)
    print(f"SUCCESS: Collection '{COLLECTION_NAME}' has been completely wiped!")

if __name__ == "__main__":
    wipe_database()