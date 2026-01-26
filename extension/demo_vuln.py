import sqlite3
def get_user_by_name(username):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    # Vulnerable: Direct string concatenation allows SQL Injection
    query = f"SELECT * FROM users WHERE name = '{username}'"
    
    cursor.execute(query)
    return cursor.fetchall()