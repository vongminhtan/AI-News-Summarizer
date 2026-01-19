import subprocess
import json
import os
import config

import threading

# Counter để xoay vòng Engine (Round-robin)
_engine_counter = 0
_counter_lock = threading.Lock()

def call_ai_cli(prompt, model=None, engine_override=None):
    """
    Hàm gọi AI tùy theo cấu hình (Gemini hoặc Codex).
    Hỗ trợ engine_override cho phép ép luồng dùng AI cụ thể.
    """
    global _engine_counter
    
    engine = engine_override or getattr(config, "AI_ENGINE", "gemini").lower()
    
    if engine == "hybrid":
        with _counter_lock:
            # Xoay vòng giữa gemini và codex
            current_choice = _engine_counter % 2
            _engine_counter += 1
        
        if current_choice == 0:
            res = call_gemini_cli(prompt, model or config.GEMINI_MODEL)
            # Nếu Gemini lỗi (nhiều khả năng là 429), thử fallback sang Codex ngay
            if res is None:
                print("🔄 Gemini failed/limit, falling back to Codex...")
                return call_codex_cli(prompt, config.CODEX_MODEL)
            return res
        else:
            return call_codex_cli(prompt, config.CODEX_MODEL)
            
    if engine == "codex":
        # Nếu dùng Codex nhưng model truyền vào là của Gemini, ép sang Codex model
        actual_model = model if model and not model.startswith("gemini") else config.CODEX_MODEL
        return call_codex_cli(prompt, actual_model)
    else:
        return call_gemini_cli(prompt, model or config.GEMINI_MODEL)

def call_gemini_cli(prompt, model="gemini-2.5-pro"):
    """
    Calls the local 'gemini' CLI tool.
    """
    try:
        # Đường dẫn tới gemini CLI từ config
        gemini_path = getattr(config, "GEMINI_CLI_PATH", "gemini")
        process = subprocess.Popen(
            [gemini_path, "--model", model, "--output-format", "json"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8"
        )
        
        stdout, stderr = process.communicate(input=prompt)
        
        if process.returncode != 0:
            print(f"❌ Gemini CLI Error: {stderr}")
            return None
        
        json_start = stdout.find('{')
        if json_start == -1:
            return None
            
        json_str = stdout[json_start:]
        response_data = json.loads(json_str)
        return response_data.get("response", "")

    except Exception as e:
        print(f"❌ Lỗi khi thực thi Gemini CLI: {e}")
        return None

def call_codex_cli(prompt, model="gpt-5.2"):
    """
    Calls the local 'codex' CLI tool.
    Example: codex exec --model gpt-5.2 --skip-git-repo-check - <<'PROMPT'
    """
    try:
        # Đường dẫn tới codex CLI từ config
        codex_path = getattr(config, "CODEX_CLI_PATH", "codex")
        process = subprocess.Popen(
            [codex_path, "exec", "--model", model, "--skip-git-repo-check", "-"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8"
        )
        
        stdout, stderr = process.communicate(input=prompt)
        
        if process.returncode != 0:
            print(f"❌ Codex CLI Error: {stderr}")
            return None
        
        # Codex output thường có header và footer
        # Ta lấy nội dung sau dấu gạch ngang cuối cùng hoặc sau chữ 'codex'
        lines = stdout.splitlines()
        content_lines = []
        is_content = False
        
        # Logic bóc tách: Lấy phần text thô ở cuối (trước phần token used)
        # Hoặc đơn giản là trả về toàn bộ stdout và để caller tự parse JSON nếu cần.
        # Codex thường trả về text trực tiếp.
        
        # Tìm dòng 'codex' và lấy phần sau đó cho đến khi thấy 'tokens used'
        for i, line in enumerate(lines):
            if line.strip() == "codex":
                is_content = True
                continue
            if line.strip() == "tokens used":
                break
            if is_content:
                content_lines.append(line)
        
        if not content_lines:
            # Nếu không tìm thấy format chuẩn, lấy 5 dòng cuối cùng bỏ đi 2 dòng cuối
            return stdout.strip()

        return "\n".join(content_lines).strip()

    except Exception as e:
        print(f"❌ Lỗi khi thực thi Codex CLI: {e}")
        return None
