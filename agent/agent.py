import os
import time
import json
import psycopg2
import logging
from logging.handlers import RotatingFileHandler
from metrics import Data

class TelemetryAgent:
    def __init__(self, db_config, interval=5):
        self.db_config = db_config
        self.interval = interval
        self.buffer_dir = "buffer"
        self.log_dir = "logs"
        self.log_file = os.path.join(self.log_dir, "agent.log")
        for d in [self.buffer_dir, self.log_dir]:
            if not os.path.exists(d): os.makedirs(d)
        self.logger = self._setup_logging()
        self.collector = Data(server_ip=db_config['host'])

    def _setup_logging(self):
        formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        handler = RotatingFileHandler(self.log_file, maxBytes=5*1024*1024, backupCount=5)
        handler.setFormatter(formatter)
        logger = logging.getLogger("Agent")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        return logger
    
    def check_journal_for_errors(self):
        if not os.path.exists(self.log_file):
            return False
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                for line in reversed(lines):
                    if "Database is available" in line:
                        return False
                    if "Database is not available" in line:
                        return True
        except Exception:
            return True  
        return False          
    
    def sync_buffer(self, conn):
        files = sorted([f for f in os.listdir(self.buffer_dir) if f.endswith('.json')])
        if not files:
            return
        self.logger.info(f"Detected {len(files)} missed sessions in journal. Starting synchronization...")
        for file_name in files:
            path = os.path.join(self.buffer_dir, file_name)
            try:
                with conn.cursor() as cur:
                    with open(path, 'r', encoding='utf-8') as f:
                        payload = json.load(f)
                    cur.execute("CALL parse_agent_data(%s)", [json.dumps(payload)])
                    conn.commit()
                    os.remove(path)
                    self.logger.info(f"The file {file_name} has been successfully sent (synchronization)")
            except Exception as e:
                conn.rollback()
                self.logger.error(f"Synchronization error: {e}")
                break

    def run(self):
        self.logger.info("Agent is run")
        while True:
            self.collector.update_data()
            payload = self.collector.get_payload()
            conn = None
            try:
                conn = psycopg2.connect(
                    dbname=self.db_config['dbname'], user=self.db_config['user'],
                    password=self.db_config['password'], host=self.db_config['host'],
                    port=self.db_config['port'], connect_timeout=3
                )
                if self.check_journal_for_errors():
                    self.sync_buffer(conn)
                self.logger.info("Database is available")
                with conn.cursor() as cur:
                    cur.execute("CALL parse_agent_data(%s)", [json.dumps(payload)])
                conn.commit()
                self.logger.info(f"The metrics file has been sent")
            except (psycopg2.OperationalError, psycopg2.InterfaceError):
                if not self.check_journal_for_errors():
                    self.logger.warning("Database is not available")
                timestamp = int(time.time())
                with open(f"{self.buffer_dir}/metrics_{timestamp}.json", 'w', encoding='utf-8') as f:
                    json.dump(payload, f, ensure_ascii=False)
            except Exception as e:
                self.logger.error(f"System error: {e}")     
            finally:
                if conn: conn.close()
            time.sleep(self.interval)

if __name__ == "__main__":
    params = {
        'dbname': os.getenv('DB_NAME', 'telemetry_db'),
        'user': os.getenv('DB_USER', 'admin'),
        'password': os.getenv('DB_PASSWORD', 'password'),
        'host': os.getenv('DB_HOST', '127.0.0.1'),
        'port': os.getenv('DB_PORT', '6432')
    }   
    poll_interval = int(os.getenv('COLLECT_INTERVAL', 5))
    agent = TelemetryAgent(db_config=params, interval=poll_interval)
    agent.run() 
