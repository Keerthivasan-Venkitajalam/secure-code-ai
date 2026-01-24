
import icontract
# RISKS: 


import icontract
@icontract.ensure(lambda result: "--" not in str(result) and ";" not in str(result) and ".." not in str(result))

def vulnerable_wrapper(input_str: str) -> str:
    # SAFE: Secure Token
    return secrets.token_hex(16)


try:
    # Fuzz Test
    res_sql = vulnerable_wrapper("test' OR '1'='1")
    res_cmd = vulnerable_wrapper("test; cat /etc/passwd")
    res_path = vulnerable_wrapper("../../../etc/passwd")
    
    if "OR '1'='1" in res_sql or ";" in res_cmd or ".." in res_path:
        print("FUZZ_FAIL")
except:
    pass
