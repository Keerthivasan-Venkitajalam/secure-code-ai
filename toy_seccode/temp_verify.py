
import icontract

# The Contract: Checks the RETURN VALUE (result) for the forbidden string
@icontract.ensure(lambda result: "--" not in result)
def vulnerable_logic(username: str) -> str:
    # The Vulnerable Logic
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    return query
    