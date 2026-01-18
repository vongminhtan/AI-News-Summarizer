from database_manager import get_db
import config

def test_new_manager():
    print(f"--- TESTING DATABASE MANAGER (USE_SSH_TUNNEL={config.USE_SSH_TUNNEL}) ---")
    
    try:
        with get_db() as conn:
            cur = conn.cursor()
            cur.execute("SELECT version();")
            version = cur.fetchone()
            print(f"🎉 Kết nối thành công!")
            print(f"🐘 Ver: {version[0]}")
            cur.close()
    except Exception as e:
        print(f"❌ Lỗi: {e}")

if __name__ == "__main__":
    test_new_manager()
