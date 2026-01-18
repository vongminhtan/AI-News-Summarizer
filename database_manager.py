import os
import psycopg2
import paramiko
from sshtunnel import SSHTunnelForwarder
from dotenv import load_dotenv
import config

# Load environment variables
load_dotenv() # Load root .env if exists
load_dotenv("infrastructure/postgres/.env")
load_dotenv("infrastructure/ssh/.env")

class DatabaseManager:
    def __init__(self):
        self.tunnel = None
        self.conn = None
        
        # Database configs
        self.db_name = os.getenv("POSTGRES_DB")
        self.db_user = os.getenv("POSTGRES_USER")
        self.db_pass = os.getenv("POSTGRES_PASSWORD")
        self.db_host = os.getenv("DB_HOST", "localhost")
        self.db_port = int(os.getenv("DB_PORT", 5432))
        
        # SSH configs (only used if tunnel is enabled)
        self.ssh_host = os.getenv("SSH_HOST")
        self.ssh_user = os.getenv("SSH_USER")
        self.ssh_pass = os.getenv("SSH_PASSWORD")
        self.proxy_cmd = os.getenv("PROXY_COMMAND")

    def __enter__(self):
        # Quyết định kết nối trực tiếp hay qua Tunnel
        # Ở VPS, config.USE_SSH_TUNNEL phải là False
        if config.USE_SSH_TUNNEL:
            print(f"🌉 [LOCAL MODE] Đang mở SSH Tunnel tới {self.ssh_host}...")
            proxy = paramiko.ProxyCommand(self.proxy_cmd.replace('%h', self.ssh_host))
            
            self.tunnel = SSHTunnelForwarder(
                (self.ssh_host, 22),
                ssh_username=self.ssh_user,
                ssh_password=self.ssh_pass,
                ssh_proxy=proxy,
                remote_bind_address=('localhost', 5432),
                local_bind_address=('127.0.0.1', 6544) # Port local tạm thời
            )
            self.tunnel.start()
            
            connect_host = '127.0.0.1'
            connect_port = self.tunnel.local_bind_port
            print(f"✅ Tunnel opened at {connect_host}:{connect_port}")
        else:
            print(f"🚀 [SERVER MODE] Kết nối trực tiếp tới Database ({self.db_host}:{self.db_port})...")
            connect_host = self.db_host
            connect_port = self.db_port

        # Kết nối tới Postgres
        self.conn = psycopg2.connect(
            dbname=self.db_name,
            user=self.db_user,
            password=self.db_pass,
            host=connect_host,
            port=connect_port,
            connect_timeout=10
        )
        return self.conn

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.conn:
            self.conn.close()
        if self.tunnel:
            self.tunnel.stop()
            print("🔌 SSH Tunnel closed.")

def get_db():
    return DatabaseManager()
