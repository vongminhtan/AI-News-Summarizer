import sys
import os

# Add parent directory to path to import database_manager
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database_manager import get_db

def setup_database():
    print("🛠️ Đang khởi tạo Database Schema...")
    
    # Sử dụng đường dẫn tuyệt đối tới file schema.sql
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    schema_path = os.path.join(base_dir, "schema.sql")
    
    if not os.path.exists(schema_path):
        print(f"❌ Không tìm thấy file {schema_path}")
        return

    with open(schema_path, "r", encoding="utf-8") as f:
        sql_script = f.read()

    try:
        with get_db() as conn:
            with conn.cursor() as cur:
                print("🚀 Đang thực thi SQL Script...")
                # Split commands if necessary, but executescript usually handles it in SQLite. 
                # For Postgres via psycopg2, we can execute the whole block if it's standard SQL.
                cur.execute(sql_script)
                conn.commit()
                print("✅ Database Setup thành công!")
                
                # Verify
                cur.execute("SELECT table_name FROM information_schema.tables WHERE table_schema='public';")
                tables = cur.fetchall()
                print("📊 Các bảng hiện có:", [t[0] for t in tables])
                
    except Exception as e:
        print(f"❌ Lỗi khi setup database: {e}")

if __name__ == "__main__":
    setup_database()
