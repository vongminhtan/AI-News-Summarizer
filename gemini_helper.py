import subprocess
import json
import os

def call_gemini_cli(prompt, model="gemini-2.5-pro"):
    """
    Calls the local 'gemini' CLI tool and returns the response text.
    Assumes the output is in JSON format.
    """
    try:
        # Sử dụng subprocess để gọi lệnh CLI
        # heredoc syntax trong Python là đưa string vào stdin
        process = subprocess.Popen(
            ["gemini", "--model", model, "--output-format", "json"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8"
        )
        
        stdout, stderr = process.communicate(input=prompt)
        
        if process.returncode != 0:
            print(f"❌ CLI Error: {stderr}")
            return None
        
        # Parse JSON từ output của CLI
        # CLI của bạn in ra text dư thừa như "Loaded cached credentials." ở dòng đầu
        # Nên ta cần tìm phần JSON thực sự (bắt đầu bằng {)
        json_start = stdout.find('{')
        if json_start == -1:
            print(f"❌ Không tìm thấy JSON trong output: {stdout}")
            return None
            
        json_str = stdout[json_start:]
        response_data = json.loads(json_str)
        
        return response_data.get("response", "")

    except Exception as e:
        print(f"❌ Lỗi khi thực thi CLI: {e}")
        return None
