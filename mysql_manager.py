import pymysql
from pymysql.cursors import DictCursor

class MySQLManager:
    def __init__(self):
        self.config = {
            'host': 'localhost',
            'user': 'ResQueue',
            'password': '123456',
            'database': 'res_queue_db',
            'charset': 'utf8mb4',
            'cursorclass': DictCursor
        }

    def _get_connection(self):
        return pymysql.connect(**self.config)

    def query(self, sql, args=None):
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, args)
                return cursor.fetchall()

    def query_one(self, sql, args=None):
        with self._get_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(sql, args)
                return cursor.fetchone()

    def execute(self, sql, args=None):
        conn = self._get_connection()
        try:
            with conn.cursor() as cursor:
                affected_rows = cursor.execute(sql, args)
            conn.commit()
            return affected_rows
        except Exception as e:
            conn.rollback()
            raise e
        finally:
            conn.close()

db = MySQLManager()