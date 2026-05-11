import os
import datetime

def debug_log(tool_or_func_name: str, **kwargs) -> None:
    """
    Log debug information with a timestamp if the DEBUG environment variable is set to true.
    """
    if os.getenv("DEBUG", "false").lower() == "true":
        timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        print(f"[{timestamp}] [DEBUG] Executing: {tool_or_func_name}")
        if kwargs:
            for k, v in kwargs.items():
                print(f"    -> {k}: {v}")
