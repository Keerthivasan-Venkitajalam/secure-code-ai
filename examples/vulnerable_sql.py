"""Example: Vulnerable SQL Injection Code"""

import sqlite3
from typing import Optional, Tuple


def login_user(username: str, password: str) -> bool:
    """
    Authenticate user with database.
    VULNERABILITY: SQL injection via string concatenation.
    """
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # VULNERABLE: No input sanitization
    query = f"SELECT * FROM users WHERE username='{username}' AND password='{password}'"
    cursor.execute(query)
    
    result = cursor.fetchone()
    conn.close()
    
    return result is not None


def get_user_data(user_id: str) -> Optional[Tuple]:
    """
    Fetch user data by ID.
    VULNERABILITY: Type coercion SQL injection.
    """
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # VULNERABLE: user_id should be parameterized
    query = f"SELECT username, email FROM users WHERE id = {user_id}"
    cursor.execute(query)
    
    result = cursor.fetchone()
    conn.close()
    
    return result


def search_users(search_term: str) -> list:
    """
    Search users by name.
    VULNERABILITY: LIKE injection.
    """
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # VULNERABLE: LIKE wildcards not escaped
    query = f"SELECT * FROM users WHERE username LIKE '%{search_term}%'"
    cursor.execute(query)
    
    results = cursor.fetchall()
    conn.close()
    
    return results


# Example exploit payloads:
# login_user("admin' OR '1'='1", "anything")  # Bypasses authentication
# get_user_data("1 OR 1=1")  # Returns all users
# search_users("%' OR '1'='1' --")  # Returns all users
