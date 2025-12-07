"""Example: Secure SQL Code (Fixed Version)"""

import sqlite3
from typing import Optional, Tuple
import re


def login_user(username: str, password: str) -> bool:
    """
    Authenticate user with database.
    SECURE: Uses parameterized queries.
    """
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # SECURE: Parameterized query prevents SQL injection
    query = "SELECT * FROM users WHERE username=? AND password=?"
    cursor.execute(query, (username, password))
    
    result = cursor.fetchone()
    conn.close()
    
    return result is not None


def get_user_data(user_id: str) -> Optional[Tuple]:
    """
    Fetch user data by ID.
    SECURE: Input validation + parameterized query.
    """
    # Validate user_id is numeric
    if not user_id.isdigit():
        raise ValueError("Invalid user ID")
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # SECURE: Parameterized query
    query = "SELECT username, email FROM users WHERE id = ?"
    cursor.execute(query, (int(user_id),))
    
    result = cursor.fetchone()
    conn.close()
    
    return result


def search_users(search_term: str) -> list:
    """
    Search users by name.
    SECURE: Input sanitization + parameterized query.
    """
    # Sanitize input: remove SQL wildcards and special chars
    sanitized_term = re.sub(r'[%_\\]', '', search_term)
    
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # SECURE: Parameterized query with sanitized input
    query = "SELECT * FROM users WHERE username LIKE ?"
    cursor.execute(query, (f"%{sanitized_term}%",))
    
    results = cursor.fetchall()
    conn.close()
    
    return results
