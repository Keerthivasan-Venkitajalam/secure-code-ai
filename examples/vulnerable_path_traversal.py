"""Example: Path Traversal Vulnerability"""

import os
from typing import Optional


def read_user_file(filename: str) -> Optional[str]:
    """
    Read user-uploaded file.
    VULNERABILITY: Path traversal via filename.
    """
    # VULNERABLE: No path validation
    base_dir = "/var/www/uploads/"
    file_path = base_dir + filename
    
    try:
        with open(file_path, 'r') as f:
            return f.read()
    except FileNotFoundError:
        return None


def download_file(file_id: str) -> bytes:
    """
    Download file by ID.
    VULNERABILITY: Directory traversal.
    """
    # VULNERABLE: file_id could be "../../../etc/passwd"
    storage_path = f"/app/storage/{file_id}"
    
    with open(storage_path, 'rb') as f:
        return f.read()


# Example exploit payloads:
# read_user_file("../../etc/passwd")  # Read system files
# download_file("../../../root/.ssh/id_rsa")  # Steal SSH keys
