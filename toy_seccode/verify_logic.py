
def vulnerable_logic(username: str):
    '''
    This function mimics the logic inside your app.
    CrossHair will analyze this to find inputs that break the assert.
    '''
    # The original vulnerable line
    query = "SELECT * FROM users WHERE username = '" + username + "'"
    
    # The Security Contract (Invariant)
    # We assert that NO input should be able to inject a comment.
    assert "--" not in query
