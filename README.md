智能运维硬件巡检监控系统
项目概述
这是一个基于AI驱动的智能运维硬件巡检监控系统，采用MCP（Model Control Protocol）协议架构，集成QWEN3-32B大模型，提供全面的服务器硬件监控、巡检、分析和自动化运维服务。系统支持企业微信通知、智能报告生成、内存升级建议等功能。

核心特性

🤖 AI智能分析: 集成QWEN3-32B大模型，提供智能决策和分析

🔧 模块化架构: 基于MCP协议的微服务架构，支持15个专业运维服务

📊 全面监控: 系统、内存、硬盘、服务状态、平台性能全方位监控

📱 企业微信集成: 支持告警通知、申请审批、状态推送

📈 智能报告: 自动生成日报、周报、AI分析报告

🔄 自动化流程: 完整巡检流程自动化执行

💾 数据持久化: MySQL数据库存储，JSON文件缓存

系统架构
架构图
![image](https://github.com/user-attachments/assets/be32d90d-fa50-4780-8f34-0f04488b61df)


技术栈
后端框架

Python 3.8+
FastAPI (Web服务器)
AsyncIO (异步处理)
Paramiko (SSH连接)
PyMySQL (数据库连接)
AI/机器学习

QWEN3-32B大模型 (智能分析)
自然语言处理
智能决策引擎
数据存储

MySQL 8.0 (结构化数据)
JSON文件 (配置和缓存)
通信协议

MCP协议 (微服务通信)
HTTP/WebSocket (前端通信)
SSH (服务器连接)
企业微信API
服务详细说明
硬件巡检服务 (001-005, 011)
服务001 - 系统状态巡检
服务名: service_001_system_inspection
文件: services/system_inspection_service.py
功能:

查询MySQL数据库获取异常服务器列表
检测内存、硬盘使用率超过阈值的服务器
获取环境监控数据（温度、湿度、电池状态）
生成系统巡检报告
核心代码:

```python```

def query_abnormal_servers(self, memory_threshold=70, disk_threshold=80):
    # 查询内存异常服务器
    memory_query = """
        SELECT ip, memory_usage, memory_status, collect_time
        FROM (
            SELECT ip, memory_usage, memory_status, collect_time,
                   ROW_NUMBER() OVER (PARTITION BY ip ORDER BY collect_time DESC) as rn
            FROM howso_server_performance_metrics
            WHERE memory_usage > %s
        ) t
        WHERE t.rn = 1
    """
服务002 - 内存详细巡检
服务名: service_002_memory_inspection
文件: services/memory_inspection_service.py
功能:

SSH连接指定服务器进行详细内存检查

获取内存使用率、硬件信息、进程占用情况

分析主板信息和内存规格

生成内存升级建议

核心功能:


支持DDR4/DDR5内存类型识别
主板芯片组规格数据库(Intel/AMD)
内存插槽使用情况分析
高内存占用进程监控
服务003 - 硬盘详细巡检
服务名: service_003_disk_inspection
文件: services/disk_inspection_service.py
功能:

SSH连接服务器检查硬盘状态
获取硬盘使用率、硬件信息
SMART健康状态检测
大文件和目录占用分析
服务004 - AI智能分析报告
服务名: service_004_hardware_summary
文件: services/hardware_summary_service.py
功能:

整合内存和硬盘巡检结果
QWEN3-32B大模型智能分析
生成详细的硬件采购建议
提供优化方案和风险评估
AI提示词示例:

```python```
prompt = f"""
请基于以下硬件巡检数据，提供针对每台服务器IP的详细硬件采购建议：
1. 巡检状态分析
2. 环境监控异常分析  
3. 系统监控警报分析
4. 现有内存配置分析（按IP分别分析）
5. 内存升级建议（按IP分别建议）
...
"""
服务005 - 完整巡检流程
服务名: service_005_full_inspection
文件: services/full_inspection.py
功能:

AI智能调度执行完整巡检流程
按序执行：系统巡检→内存巡检→硬盘巡检→AI分析→升级建议
智能决策下一步操作
流程状态跟踪和错误处理
服务011 - 内存升级建议
服务名: service_011_apply_purchases
文件: services/apply_purchases.py
功能:

基于内存巡检结果生成升级建议
调用QWEN3-32B进行深度分析
生成详细的采购申请单
包含价格预估和时间规划
基础监控服务 (006-010)
服务006 - 日志智能分析
服务名: service_006_log_analysis
文件: services/base/log_analysis_service.py
功能:

智能日志文件解析
错误模式识别和关键词匹配
AI智能分析日志内容
生成问题诊断报告
服务007 - 日报生成
服务名: service_007_daily_report
文件: services/base/daily_report_service.py
功能:

生成昨日监控数据分析报告
系统状态、异常统计、风险预测
AI智能分析趋势变化
自动化报告推送
服务008 - 周报生成
服务名: service_008_weekly_report
文件: services/base/weekly_report_service.py
功能:

生成上周监控数据综合分析
趋势分析、异常统计、运维建议
长期性能指标跟踪
智能预测下周风险点
服务009 - 服务状态监控
服务名: service_009_service_monitoring
文件: services/base/server_monitoring_service.py
功能:

检测各平台服务运行状态
端口连通性测试
进程状态监控
服务健康检查
监控的服务平台:

算法中枢平台
社区平台
城管平台
数字员工平台
标注平台
训练平台
道路病害平台
服务010 - 平台性能监控
服务名: service_010_platform_monitoring
文件: services/base/platform_monitoring_service.py
功能:

获取CPU、内存、磁盘使用率
性能指标异常检测
监控数据持久化存储
实时性能告警
通知推送服务 (012-015)
服务012 - 企业微信通知
服务名: service_012_wechat_notification
文件: services/wechat/send_chat.py
功能:

企业微信消息发送
支持文本、图片、文件推送
群组和个人消息
消息记录和状态跟踪
企业微信配置:

```python```

CORP_ID = "ww568874482f006b53"
CORP_SECRET = "zJM1d6Ljk86fiK4WUptdi4gmA7Gj0RkaHDYiFW6wM8g"
AGENT_ID = "1000008"
服务013 - 内存申请通知
服务名: service_013_memory_apply_notice
文件: services/wechat/apply_notice.py
功能:

检测需要申请的内存升级
自动生成采购申请单
发送企业微信通知给审批人
申请状态跟踪
服务014 - 内存价格询问
服务名: service_014_memory_price_inquiry
文件: services/wechat/price_get.py
功能:

检测价格为空的内存升级记录
自动发送价格询问消息
支持多用户询价
价格信息收集和更新
服务015 - 内存问题解决通知
服务名: service_015_memory_resolved_notice
文件: services/wechat/solved_notice.py
功能:

检测已恢复正常的内存问题
自动发送解决通知
状态更新和记录归档
问题解决统计
数据库设计
主要数据表
服务器性能监控表

```sql```

CREATE TABLE `howso_server_performance_metrics` (
    `id` varchar(20) NOT NULL COMMENT '主键ID',
    `ip` varchar(50) NOT NULL COMMENT '服务器IP',
    `collect_time` datetime NOT NULL COMMENT '采集时间',
    `cpu_usage` decimal(5,2) DEFAULT NULL COMMENT 'CPU使用率(%)',
    `cpu_status` varchar(20) DEFAULT NULL COMMENT 'CPU状态',
    `memory_usage` decimal(5,2) DEFAULT NULL COMMENT '内存使用率(%)',
    `memory_status` varchar(20) DEFAULT NULL COMMENT '内存状态',
    `disk_usage` decimal(5,2) DEFAULT NULL COMMENT '磁盘使用率(%)',
    `disk_status` varchar(20) DEFAULT NULL COMMENT '磁盘状态',
    `network_status` varchar(20) DEFAULT NULL COMMENT '网络状态',
    `bk_cloud_id` int DEFAULT NULL COMMENT '云区域ID',
    `insert_time` datetime NOT NULL COMMENT '插入时间',
    PRIMARY KEY (`id`),
    KEY `idx_ip` (`ip`),
    KEY `idx_collect_time` (`collect_time`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
服务监控表

```sql```


CREATE TABLE plat_service_monitoring (
    id varchar(20) NOT NULL,
    batch_id varchar(50) NOT NULL,
    platform varchar(100),
    server_name varchar(100),
    server_ip varchar(50),
    service_name varchar(100),
    service_id varchar(100),
    port int,
    status varchar(20),
    process_status varchar(20),
    response_time varchar(50),
    start_cmd text,
    stop_cmd text,
    insert_time datetime,
    local_ip varchar(500),
    hostname varchar(100),
    os_type varchar(50),
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
运维分析总结表

sql

CREATE TABLE operation_analysis_summary (
    id varchar(20) NOT NULL,
    report_date date NOT NULL,
    report_type varchar(20) NOT NULL,
    operation_daily text,
    exception_analysis text,
    exception_data longtext,
    risk_prediction text,
    operation_suggestion text,
    key_focus text,
    moderate_focus text,
    created_at datetime,
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
配置文件
数据库配置
文件: utils/database.py

```python```

DATABASE_CONFIG = {
    'host': '192.168.101.62',
    'port': 3306,
    'user': 'root', 
    'password': '123456',
    'database': 'envom',
    'charset': 'utf8mb4'
}
AI模型配置
文件: config/config.py

```python```


LLM_CONFIG = {
    'base_url': 'http://192.168.101.214:6007',
    'chat_endpoint': '/v1/chat/completions',
    'model_name': 'Qwen3-32B-AWQ'
}
SSH连接配置

```python```

SSH_CONFIGS = {
    '192.168.10.152': {'username': 'root', 'password': 'howso@123'},
    '192.168.101.222': {'username': 'root', 'password': 'zxx@123howso?'},
    '192.168.121.23': {'username': 'root', 'password': 'abc,.123'},
    '192.168.121.26': {'username': 'root', 'password': 'howso@123'}
}
部署指南
环境要求
系统要求

Linux/Windows 10+
Python 3.8+
MySQL 8.0+
Python依赖

bash

pip install fastapi uvicorn
pip install paramiko pymysql
pip install requests aiohttp
pip install websockets
pip install pycryptodome

bash

git clone <repository-url>
cd smart-ops-monitoring
安装依赖
bash

pip install -r requirements.txt
配置数据库
bash

# 创建数据库
mysql -u root -p
CREATE DATABASE envom CHARACTER SET utf8mb4;

# 导入表结构
mysql -u root -p envom < database/schema.sql
配置文件
bash

# 复制配置模板
cp config/config.py.example config/config.py

# 编辑配置文件
vi config/config.py
启动服务
方式一：单独启动各服务

bash

# 启动MCP服务器
python run_server.py

# 启动Web服务器
python web_server.py

# 启动聊天代理
python chat_agent.py
方式二：使用Web控制台启动

bash

# 启动Web控制台
python web_server.py

# 访问 http://localhost:8080
# 通过界面控制各服务的启停
服务端口
服务	端口	说明
Web服务器	8080	主控制台界面
MCP服务器	8004	运维服务协议栈
企业微信接收	8003	微信消息回调
使用指南
Web控制台使用
访问控制台

浏览器访问 http://localhost:8080
查看服务状态和系统概览
启动服务

点击服务状态区域的启动按钮
建议启动顺序：MCP服务器 → Chat代理
执行巡检

在聊天界面输入："执行完整巡检"
或者："检查系统状态"
命令行使用
执行系统巡检

python

运行

import asyncio
from services.system_inspection_service import system_inspection

result = system_inspection({
    'memory_threshold': 70,
    'disk_threshold': 80
})
print(result)
执行完整巡检流程

```python```

import asyncio
from services.full_inspection import full_inspection
from run_server import MCPServer

async def main():
    server = MCPServer()
    result = await full_inspection({
        'memory_threshold': 70,
        'disk_threshold': 80
    }, server)
    print(result)

asyncio.run(main())
企业微信集成使用
发送通知消息

```python```

from services.wechat.send_chat import wechat_notification_service

result = wechat_notification_service({
    'to_user': 'llm-aitachi',
    'content': '服务器192.168.101.45内存使用率过高，请及时处理'
})
检查内存申请

```python```

from services.wechat.apply_notice import memory_apply_notification

result = memory_apply_notification()
print(result)
API接口文档
MCP协议接口
获取工具列表

json

{
    "method": "list_tools",
    "id": "request_1"
}
调用工具

json

{
    "method": "call_tool",
    "params": {
        "name": "service_001_system_inspection",
        "arguments": {
            "memory_threshold": 70,
            "disk_threshold": 80
        }
    },
    "id": "request_2"
}
Web API接口
获取服务状态

http

GET /api/service/status
执行聊天对话

http

POST /api/chat
Content-Type: application/json

{
    "message": "执行系统巡检"
}
获取AI报告

http

GET /api/ai-report
监控告警
告警阈值配置
python

运行

THRESHOLDS = {
    'cpu': 70.0,        # CPU使用率阈值
    'memory': 70.0,     # 内存使用率阈值
    'disk': 80.0,       # 磁盘使用率阈值
    'network': 95.0     # 网络使用率阈值
}
自动告警规则
内存使用率 > 70%: 发送警告通知
硬盘使用率 > 80%: 发送紧急通知
服务异常: 立即发送故障通知
温度异常: 发送环境告警
故障排除
常见问题
1. MCP服务器启动失败

bash

复制
# 检查端口占用
netstat -tulpn | grep 8004

# 检查日志
tail -f logs/mcp_server.log
2. SSH连接失败

bash

复制
# 检查网络连通性
ping 192.168.101.45

# 检查SSH配置
ssh root@192.168.101.45
3. 数据库连接失败

bash

复制
# 检查数据库状态
systemctl status mysql

# 测试连接
mysql -h 192.168.101.62 -u root -p envom
4. 企业微信通知失败

检查企业微信配置信息
验证网络连接
查看应用权限设置
日志查看
系统日志

bash

复制
tail -f logs/system.log
tail -f logs/chat_agent.log
tail -f logs/mcp_server.log
服务日志

bash

复制
# 查看特定服务日志
grep "service_001" logs/system.log
grep "ERROR" logs/*.log
开发指南
添加新服务
创建服务文件

```python```


# services/new_service.py
def new_service(params=None):
    try:
        # 服务逻辑
        return {
            "success": True,
            "message": "服务执行成功",
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e)
        }
注册服务

python


# run_server.py
def _initialize_handlers(self):
    service_handlers = {
        # ... 现有服务
        "service_016_new_service": new_service
    }
添加工具定义
python

运行

复制
# run_server.py MCPProtocol._register_tools()
"service_016_new_service": {
    "name": "service_016_new_service",
    "service_id": "016", 
    "description": "【服务016】新服务功能描述",
    "keywords": ["关键词1", "关键词2"],
    "parameters": {
        "type": "object",
        "properties": {
            "param1": {"type": "string", "description": "参数描述"}
        }
    }
}
代码规范
文件命名

服务文件：service_name_service.py
工具类：ClassName
函数名：function_name
日志规范

```python```


import logging
logger = logging.getLogger(__name__)

logger.info("信息日志")
logger.warning("警告日志")
logger.error("错误日志")
异常处理

python

运行

复制
try:
    # 业务逻辑
    pass
except Exception as e:
    logger.error(f"操作失败: {e}")
    return {"success": False, "error": str(e)}
性能优化
数据库优化
索引优化

sql

-- 性能监控表索引
CREATE INDEX idx_ip_collect_time ON howso_server_performance_metrics(ip, collect_time);
CREATE INDEX idx_memory_usage ON howso_server_performance_metrics(memory_usage);
CREATE INDEX idx_disk_usage ON howso_server_performance_metrics(disk_usage);
查询优化

使用分页查询大数据集
添加适当的WHERE条件
使用JOIN替代子查询
内存优化
数据缓存

使用JSON文件缓存频繁访问的数据
定期清理过期缓存文件
控制内存中数据的大小
连接池

使用数据库连接池
控制SSH连接的并发数
及时释放资源
安全考虑
访问控制
SSH密钥认证

python

运行

复制
# 建议使用密钥认证替代密码
ssh_key = paramiko.RSAKey.from_private_key_file('/path/to/private_key')
ssh.connect(hostname, username='root', pkey=ssh_key)
API访问控制

添加API认证机制
限制API访问频率
记录操作审计日志
数据安全
敏感信息加密

数据库密码加密存储
SSH密码使用环境变量
企业微信凭证安全管理
网络安全

使用HTTPS传输
限制服务端口访问
防火墙规则配置
版本更新
v1.0.0 (当前版本)
基础硬件巡检功能
MCP协议架构
企业微信集成
AI智能分析
后续规划
容器化部署支持
集群监控功能
更多AI模型集成
移动端支持
贡献指南
提交代码
Fork项目仓库
创建功能分支
提交代码变更
创建Pull Request
问题反馈
使用GitHub Issues报告问题
提供详细的错误信息和日志
描述复现步骤
许可证
本项目采用MIT许可证，详见LICENSE文件。

联系方式
技术支持：运维团队
企业微信群：智能运维交流群
邮箱：ops-team@company.com
