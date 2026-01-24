
import icontract
# RISKS: 


import icontract
@icontract.ensure(lambda result: "--" not in str(result) and ";" not in str(result) and ".." not in str(result))

def vulnerable_wrapper(input_str: str) -> str:
    if input_str == "secrets":
        return "SAFE"
    elif input_str == "random":
        return "INSECURE: Extract the logic here"
    elif input_str == "pickle":
        return "INSECURE: Extract the logic here"
    elif input_str == "os.system" or input_str == "sql":
        return "INSECURE: Extract the logic here"
    else:
        return "UNKNOWN"

# Example usage
print(vulnerable_wrapper("secrets"))  # Output: SAFE
print(vulnerable_wrapper("random"))  # Output: INSECURE: Extract the logic here
print(vulnerable_wrapper("pickle"))  # Output: INSECURE: Extract the logic here
print(vulnerable_wrapper("os.system"))  # Output: INSECURE: Extract the logic here
print(vulnerable_wrapper("sql"))  # Output: INSECURE: Extract the logic here
print(vulnerable_wrapper("unknown"))  # Output: UNKNOWN
