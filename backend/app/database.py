import sqlite3
import json
from datetime import datetime
import os

# Define where the database file will live
DB_PATH = "history.db"

def init_db():
    """Creates the SQLite database and the history table if they don't exist."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS analysis_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            filename TEXT,
            playbook_rule TEXT,
            is_compliant BOOLEAN,
            summary TEXT,
            flagged_clauses TEXT, -- Stored as a JSON string
            model_used TEXT,
            estimated_cost_usd REAL
        )
    ''')
    conn.commit()
    conn.close()

def save_analysis(filename, playbook_rule, result_dict, model_used):
    """Saves a completed analysis to the database."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    is_compliant = result_dict.get("is_compliant", False)
    summary = result_dict.get("summary", "")
    
    # Convert the list of flagged clauses into a JSON string for storage
    flagged_clauses_json = json.dumps(result_dict.get("flagged_clauses", []))
    cost = result_dict.get("estimated_cost_usd", 0.0)

    cursor.execute('''
        INSERT INTO analysis_history 
        (timestamp, filename, playbook_rule, is_compliant, summary, flagged_clauses, model_used, estimated_cost_usd)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (timestamp, filename, playbook_rule, is_compliant, summary, flagged_clauses_json, model_used, cost))
    
    conn.commit()
    conn.close()

def get_all_history():
    """Retrieves all past analyses, sorted by newest first."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row # Returns dict-like objects instead of plain tuples
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM analysis_history ORDER BY id DESC')
    rows = cursor.fetchall()
    conn.close()
    
    # Convert rows to a list of standard dictionaries
    history_list = []
    for row in rows:
        item = dict(row)
        # Parse the JSON string back into a Python list
        item["flagged_clauses"] = json.loads(item["flagged_clauses"])
        history_list.append(item)
        
    return history_list

def delete_history_record(record_id: int):
    """Deletes a specific record by ID."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute('DELETE FROM analysis_history WHERE id = ?', (record_id,))
    conn.commit()
    conn.close()

# Automatically initialize the DB when this file is imported
init_db()