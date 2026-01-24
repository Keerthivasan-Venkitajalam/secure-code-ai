
import icontract
# RISKS: 


import icontract
@icontract.ensure(lambda result: "--" not in str(result) and ";" not in str(result) and ".." not in str(result))

def vulnerable_wrapper(input_str: str) -> str:
    # SAFE: Uses 'secrets' library
    if input_str == 'secrets':
        return "SAFE"
    # Insecure: Extracts logic from 'random' library
    elif input_str == 'random':
        return "Insecure: Extracts logic from 'random' library"
    # Insecure: Extracts logic from 'pickle' library
    elif input_str == 'pickle':
        return "Insecure: Extracts logic from 'pickle' library"
    # Injection: Extracts logic from 'os.system/sql'
    elif input_str == 'os.system':
        return "Injection: Extracts logic from 'os.system/sql'"
    elif input_str == 'sql':
        return "Injection: Extracts logic from 'sql'"
    else:
        return "Unknown input"

# Example usage
print(vulnerable_wrapper('secrets'))  # Output: SAFE
print(vulnerable_wrapper('random'))  # Output: Insecure: Extracts logic from 'random' library
print(vulnerable_wrapper('pickle'))  # Output: Insecure: Extracts logic from 'pickle' library
print(vulnerable_wrapper('os.system'))  # Output: Injection: Extracts logic from 'os.system/sql'
print(vulnerable_wrapper('sql'))  # Output: Injection: Extracts logic from 'sql'
print(vulnerable_wrapper('unknown'))  # Output: Unknown input
