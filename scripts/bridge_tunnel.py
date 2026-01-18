from database_manager import get_db
import time
import sys

def maintain_tunnel():
    print("🌉 [BRIDGE] Đang thiết lập SSH Tunnel cho Next.js...")
    print("👉 Vui lòng GIỮ terminal này chạy để Next.js có thể truy cập Database qua cổng 5432.")
    
    try:
        # Sử dụng DatabaseManager để mở tunnel
        # get_db() trả về instance DatabaseManager
        db_manager = get_db()
        
        # Chúng ta dùng __enter__ thủ công để giữ tunnel không bị đóng
        with db_manager as conn:
            # Kiểm tra kết nối phát đầu tiên
            cur = conn.cursor()
            cur.execute("SELECT 1")
            cur.close()
            
            print("✅ Tunnel đã SẴN SÀNG tại localhost:5432")
            print("Press Ctrl+C to close.")
            
            # Vòng lặp vô tận để giữ tunnel
            while True:
                time.sleep(1)
                
    except KeyboardInterrupt:
        print("\n🔌 Đang đóng Tunnel...")
    except Exception as e:
        print(f"❌ Lỗi: {e}")
        sys.exit(1)

if __name__ == "__main__":
    maintain_tunnel()
