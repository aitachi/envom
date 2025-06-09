#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import json
import pymysql
import decimal
import sys
import os
from datetime import datetime, timedelta

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.logger import setup_logger
from utils.database import get_connection

logger = setup_logger(__name__)


class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, decimal.Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)


class SystemInspector:
    def __init__(self):
        self.connection = None
        current_dir = os.path.dirname(os.path.abspath(__file__))
        self.output_file = os.path.join(current_dir, 'data', 'system.json')

    def get_connection(self):
        try:
            if not self.connection:
                self.connection = get_connection()
            return self.connection
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return None

    def close_connection(self):
        if self.connection:
            self.connection.close()
            self.connection = None

    def query_abnormal_servers(self, memory_threshold=70, disk_threshold=80):
        try:
            conn = self.get_connection()
            if not conn:
                return None

            cursor = conn.cursor()

            # 查询内存异常，每个IP只取最新的一条记录，去掉时间限制
            memory_query = """
                           SELECT ip, memory_usage, memory_status, collect_time
                           FROM (
                               SELECT ip, memory_usage, memory_status, collect_time,
                                      ROW_NUMBER() OVER (PARTITION BY ip ORDER BY collect_time DESC) as rn
                               FROM howso_server_performance_metrics
                               WHERE memory_usage > %s
                           ) t
                           WHERE t.rn = 1
                           ORDER BY collect_time DESC 
                           """

            cursor.execute(memory_query, (memory_threshold,))
            memory_results = cursor.fetchall()

            abnormal_memory_ips = list(set([row['ip'] for row in memory_results]))

            memory_details = []
            for row in memory_results:
                memory_details.append({
                    'ip': row['ip'],
                    'memory_usage': float(row['memory_usage']) if isinstance(row['memory_usage'], decimal.Decimal) else
                    row['memory_usage'],
                    'memory_status': row['memory_status'],
                    'collect_time': row['collect_time'].strftime('%Y-%m-%d %H:%M:%S') if row['collect_time'] else None
                })

            # 硬盘结果写为正常
            disk_details = []

            cursor.close()
            return {
                'abnormal_memory_ips': abnormal_memory_ips,
                'abnormal_disk_ips': [],  # 硬盘异常IP列表为空
                'memory_details': memory_details,
                'disk_details': disk_details  # 硬盘详情为空列表
            }

        except Exception as e:
            logger.error(f"查询异常服务器失败: {e}")
            return None

    def query_environment_monitoring(self, hours=12):
        try:
            conn = self.get_connection()
            if not conn:
                return {}

            cursor = conn.cursor()
            time_threshold = datetime.now() - timedelta(hours=hours)

            env_query = """
                        SELECT battery_status, 
                               avg_temperature, 
                               avg_temperature_status,
                               avg_humidity, 
                               avg_humidity_status, 
                               inspection_time
                        FROM power_monitoring_avg_data
                        WHERE inspection_time >= %s
                        ORDER BY inspection_time DESC LIMIT 10 
                        """

            cursor.execute(env_query, (time_threshold,))
            env_results = cursor.fetchall()

            abnormal_environment_details = []
            if env_results:
                for row in env_results:
                    if (row['battery_status'] == '异常' or
                            row['avg_temperature_status'] == '异常' or
                            row['avg_humidity_status'] == '异常'):

                        temp_value = row['avg_temperature']
                        humidity_value = row['avg_humidity']

                        if isinstance(temp_value, decimal.Decimal):
                            temp_value = float(temp_value)
                        if isinstance(humidity_value, decimal.Decimal):
                            humidity_value = float(humidity_value)

                        abnormal_environment_details.append({
                            'type': '温度' if row['avg_temperature_status'] == '异常' else
                            '湿度' if row['avg_humidity_status'] == '异常' else '电池',
                            'value': temp_value if row['avg_temperature_status'] == '异常' else
                            humidity_value if row['avg_humidity_status'] == '异常' else
                            row['battery_status'],
                            'status': row['avg_temperature_status'] if row['avg_temperature_status'] == '异常' else
                            row['avg_humidity_status'] if row['avg_humidity_status'] == '异常' else
                            row['battery_status'],
                            'inspection_time': row['inspection_time'].strftime('%Y-%m-%d %H:%M:%S')
                        })

            cursor.close()
            return {'abnormal_environment_details': abnormal_environment_details}

        except Exception as e:
            logger.error(f"查询环境监控失败: {e}")
            return {}

    def save_to_file(self, data):
        try:
            os.makedirs(os.path.dirname(self.output_file), exist_ok=True)
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2, cls=DecimalEncoder)
            logger.info(f"系统巡检结果已保存到: {self.output_file}")
            return True
        except Exception as e:
            logger.error(f"保存文件失败: {e}")
            return False


def system_inspection(params=None):
    try:
        logger.info("开始执行全系统状态巡检")

        memory_threshold = params.get('memory_threshold', 70) if params else 70
        disk_threshold = params.get('disk_threshold', 80) if params else 80

        inspector = SystemInspector()

        server_monitoring = inspector.query_abnormal_servers(memory_threshold, disk_threshold)
        environment_monitoring = inspector.query_environment_monitoring()

        if server_monitoring is None:
            return {"success": False, "error": "服务器监控数据查询失败"}

        report_data = {
            'generation_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'query_parameters': {
                'memory_threshold': memory_threshold,
                'disk_threshold': disk_threshold
            },
            'abnormal_memory_ips': server_monitoring.get('abnormal_memory_ips', []),
            'abnormal_disk_ips': server_monitoring.get('abnormal_disk_ips', []),
            'server_monitoring': server_monitoring,
            'environment_monitoring': environment_monitoring
        }

        if inspector.save_to_file(report_data):
            return {
                "success": True,
                "message": "全系统状态巡检完成",
                "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                "output_file": inspector.output_file,
                "data": report_data
            }
        else:
            return {"success": False, "error": "保存巡检结果失败"}

    except Exception as e:
        logger.error(f"系统状态巡检服务异常: {e}")
        return {"success": False, "error": f"系统状态巡检服务异常: {str(e)}"}
    finally:
        if 'inspector' in locals():
            inspector.close_connection()


if __name__ == "__main__":
    result = system_inspection()
    print(json.dumps(result, ensure_ascii=False, indent=2))