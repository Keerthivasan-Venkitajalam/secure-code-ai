
import sqlite3

def get_user_data(username):
    conn = sqlite3.connect("users.db")
    cursor = conn.cursor()
    
    # VULNERABILITY: Direct string formatting allows SQL Injection
    # Example attack: username = "admin' --"
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    
    cursor.execute(query)
    return cursor.fetchall()
