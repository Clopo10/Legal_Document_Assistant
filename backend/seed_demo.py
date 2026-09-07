import os
from app.engine import process_and_vectorize_file

DEMO_FOLDER = "../data/sample_contracts"

def seed_database():
    print("Seeding demo contracts into Qdrant...")
    
    if not os.path.exists(DEMO_FOLDER):
        print(f"Error: Could not find folder {DEMO_FOLDER}")
        return

    # Loop through every file in the demo folder
    for filename in os.listdir(DEMO_FOLDER):
        if filename.endswith(".txt") or filename.endswith(".pdf"):
            file_path = os.path.join(DEMO_FOLDER, filename)
            print(f"Vectorizing {filename}...")
            
            try:
                # We use the exact same function we built for the custom uploads!
                process_and_vectorize_file(file_path, filename)
                print(f"{filename} added permanently.")
            except Exception as e:
                print(f"Failed to process {filename}: {e}")

    print("Demo database is fully seeded and ready!")

if __name__ == "__main__":
    seed_database()