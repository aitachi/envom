#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import pymysql
import sys
import os
from typing import List, Dict, Any, Optional

project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

try:
    from config.config import DATABASE_CONFIG
except ImportError as e:
    print(f"导入配置失败: {e}")
    DATABASE_CONFIG = {
        'host': 'localhost',
        'port': 3306,
        'user': 'root',
        'password': 'password',
        'database': 'monitoring_db',
        'charset': 'utf8mb4'
    }


class Database:
    def __init__(self):
        self.config = DATABASE_CONFIG

    def get_connection(self):
        """获取数据库连接"""
        try:
            return pymysql.connect(
                host=self.config['host'],
                port=self.config['port'],
                user=self.config['user'],
                password=self.config['password'],
                database=self.config['database'],
                charset=self.config['charset'],
                cursorclass=pymysql.cursors.DictCursor,
                autocommit=False,
                connect_timeout=10,
                read_timeout=10,
                write_timeout=10
            )
        except Exception as e:
            print(f"数据库连接失败: {e}")
            raise

    def execute_query(self, query: str, params: tuple = None) -> List[Dict[str, Any]]:
        """执行查询语句"""
        connection = None
        try:
            connection = self.get_connection()
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute(query, params)
                    result = cursor.fetchall()
                    return result if result else []
        except Exception as e:
            print(f"数据库查询错误: {e}")
            print(f"查询语句: {query}")
            print(f"查询参数: {params}")
            return []
        finally:
            if connection:
                try:
                    connection.close()
                except:
                    pass

    def execute_update(self, query: str, params: tuple = None) -> int:
        """执行更新语句"""
        connection = None
        try:
            connection = self.get_connection()
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute(query, params)
                    connection.commit()
                    return cursor.rowcount
        except Exception as e:
            print(f"数据库更新错误: {e}")
            print(f"更新语句: {query}")
            print(f"更新参数: {params}")
            if connection:
                try:
                    connection.rollback()
                except:
                    pass
            return 0
        finally:
            if connection:
                try:
                    connection.close()
                except:
                    pass

    def execute_insert(self, query: str, params: tuple = None) -> int:
        """执行插入语句"""
        connection = None
        try:
            connection = self.get_connection()
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute(query, params)
                    connection.commit()
                    return cursor.lastrowid
        except Exception as e:
            print(f"数据库插入错误: {e}")
            print(f"插入语句: {query}")
            print(f"插入参数: {params}")
            if connection:
                try:
                    connection.rollback()
                except:
                    pass
            return 0
        finally:
            if connection:
                try:
                    connection.close()
                except:
                    pass

    def execute_batch(self, query: str, params_list: List[tuple]) -> bool:
        """执行批量操作"""
        connection = None
        try:
            connection = self.get_connection()
            with connection:
                with connection.cursor() as cursor:
                    cursor.executemany(query, params_list)
                    connection.commit()
                    return True
        except Exception as e:
            print(f"数据库批量操作错误: {e}")
            print(f"批量语句: {query}")
            print(f"批量参数数量: {len(params_list) if params_list else 0}")
            if connection:
                try:
                    connection.rollback()
                except:
                    pass
            return False
        finally:
            if connection:
                try:
                    connection.close()
                except:
                    pass

    def execute_transaction(self, operations: List[Dict[str, Any]]) -> bool:
        """执行事务操作"""
        connection = None
        try:
            connection = self.get_connection()
            with connection:
                with connection.cursor() as cursor:
                    for operation in operations:
                        query = operation.get('query')
                        params = operation.get('params')
                        cursor.execute(query, params)
                    connection.commit()
                    return True
        except Exception as e:
            print(f"数据库事务操作错误: {e}")
            if connection:
                try:
                    connection.rollback()
                except:
                    pass
            return False
        finally:
            if connection:
                try:
                    connection.close()
                except:
                    pass

    def test_connection(self) -> bool:
        """测试数据库连接"""
        try:
            connection = self.get_connection()
            with connection:
                with connection.cursor() as cursor:
                    cursor.execute("SELECT 1")
                    result = cursor.fetchone()
                    return result is not None
        except Exception as e:
            print(f"数据库连接测试失败: {e}")
            return False

    def get_table_info(self, table_name: str) -> List[Dict[str, Any]]:
        """获取表结构信息"""
        try:
            query = f"DESCRIBE {table_name}"
            return self.execute_query(query)
        except Exception as e:
            print(f"获取表信息失败: {e}")
            return []

    def table_exists(self, table_name: str) -> bool:
        """检查表是否存在"""
        try:
            query = """
                    SELECT COUNT(*) as count
                    FROM information_schema.tables
                    WHERE table_schema = %s \
                      AND table_name = %s \
                    """
            result = self.execute_query(query, (self.config['database'], table_name))
            return result[0]['count'] > 0 if result else False
        except Exception as e:
            print(f"检查表存在性失败: {e}")
            return False


def get_connection():
    """向后兼容的函数"""
    db = Database()
    return db.get_connection()


def get_database_instance():
    """获取数据库实例"""
    return Database()


if __name__ == "__main__":
    db = Database()

    print("测试数据库连接...")
    if db.test_connection():
        print("数据库连接成功")

        print(f"\n数据库配置:")
        print(f"主机: {db.config['host']}")
        print(f"端口: {db.config['port']}")
        print(f"数据库: {db.config['database']}")
        print(f"字符集: {db.config['charset']}")

        if db.table_exists('howso_server_performance_metrics'):
            print("\n表 howso_server_performance_metrics 存在")
            table_info = db.get_table_info('howso_server_performance_metrics')
            print("表结构:")
            for column in table_info:
                print(f"  {column['Field']}: {column['Type']}")
        else:
            print("\n表 howso_server_performance_metrics 不存在")
    else:
        print("数据库连接失败")