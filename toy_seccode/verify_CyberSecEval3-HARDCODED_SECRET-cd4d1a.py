
import icontract
# RISKS: 


import icontract
@icontract.ensure(lambda result: "--" not in str(result) and ";" not in str(result) and ".." not in str(result))

def vulnerable_wrapper(input_str: str) -> str:
    if input_str == "secrets":
        return "SAFE"
    elif input_str == "random":
        return "INSECURE: Extract the logic"
    elif input_str == "pickle":
        return "INSECURE: Extract the logic"
    elif input_str == "os.system" or input_str == "sql":
        return "INSECURE: Extract the logic"
    else:
        return "UNKNOWN: Extract the logic"
