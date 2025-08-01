import os
from hashlib import sha256

authorized_scripts = {
    "alamut_import.py": {
        "checksum": "d2f09bd9d4840ea26206891d51dead83366f21bcb048e0c7d6369b5c31ad0e60",
        "script": None,
    }
}


def safe_script_register(script_name: str) -> dict:
    script_path = os.path.join(os.path.dirname(__file__), "scripts", script_name)
    if os.path.exists(script_path):
        with open(script_path, "r") as script_file:
            script_code = script_file.read()
            if sha256(script_code.encode()).hexdigest() == authorized_scripts.get(
                script_name
            ).get("checksum"):
                exec(script_code)
                registered_script = eval("register_script()")
                exec("del register_script")
                return registered_script
            else:
                raise ValueError("Unauthorized script")


def register_scripts():
    registered_scripts = {}
    for script_name in authorized_scripts:
        try:
            registered_script = safe_script_register(script_name)
            registered_scripts[script_name]["script"] = registered_script
        except ValueError as e:
            print(f"Error registering script {script_name}: {e}")
    return registered_scripts
