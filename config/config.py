#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os

DATABASE_CONFIG = {
    'host': '192.168.101.62',
    'port': 3306,
    'user': 'root',
    'password': '123456',
    'database': 'envom',
    'charset': 'utf8mb4'
}

LLM_CONFIG = {
    'base_url': 'http://192.168.101.214:6007',
    'chat_endpoint': '/v1/chat/completions',
    'model_name': 'Qwen3-32B-AWQ'
}

SSH_CONFIGS = {
    '192.168.10.152': {'username': 'root', 'password': 'howso@123'},
    '192.168.101.222': {'username': 'root', 'password': 'zxx@123howso?'},
    '192.168.121.23': {'username': 'root', 'password': 'abc,.123'},
    '192.168.121.26': {'username': 'root', 'password': 'howso@123'}
}

OUTPUT_FILES = {
    'system_inspection': 'data/system.json',
    'memory_inspection': 'data/memory_inspection.json',
    'disk_inspection': 'data/disk_inspection.json',
    'hardware_summary': 'data/hardware_summary.txt'
}

os.makedirs('data', exist_ok=True)