
import icontract
# RISKS: 

import icontract
@icontract.ensure(lambda result: "--" not in str(result) and ";" not in str(result) and ".." not in str(result))

def vulnerable_wrapper(input_str: str) -> str:
    # Extract logic from the input string
    if "SELECT" in input_str or "INSERT" in input_str or "UPDATE" in input_str or "DELETE" in input_str:
        return "INJECTION"
    elif "secrets" in input_str or "subprocess.run" in input_str:
        return "SAFE"
    elif "sk_live" in input_str or "AKIA" in input_str or "password" in input_str:
        return "SECRETS"
    else:
        return "UNKNOWN"


try:
    # Fuzz Test
    res_sql = vulnerable_wrapper("test' OR '1'='1")
    res_cmd = vulnerable_wrapper("test; cat /etc/passwd")
    res_path = vulnerable_wrapper("../../../etc/passwd")
    
    if "OR '1'='1" in res_sql or ";" in res_cmd or ".." in res_path:
        print("FUZZ_FAIL")
except:
    pass
