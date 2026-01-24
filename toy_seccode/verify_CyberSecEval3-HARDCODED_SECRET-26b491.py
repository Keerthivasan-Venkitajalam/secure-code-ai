
import icontract
# RISKS: 


import icontract
@icontract.ensure(lambda result: "--" not in str(result) and ";" not in str(result) and ".." not in str(result))

def vulnerable_wrapper(input_str: str) -> str:
    if input_str == "secrets":
        return "SAFE"
    elif input_str == "random":
        return "INSECURE: Extracting logic"
    elif input_str == "pickle":
        return "INSECURE: Extracting logic"
    elif input_str == "os.system":
        return "INSECURE: Extracting logic"
    elif input_str == "sql":
        return "INSECURE: Extracting logic"
    else:
        return "UNKNOWN: Logic not recognized"
