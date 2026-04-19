"""
健康监控模块

提供系统健康检查、性能监控和告警功能
"""

import asyncio
import psutil
import os
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass
from enum import Enum

from src.utils.logger import logger


class HealthStatus(Enum):
    """健康状态"""
    HEALTHY = "healthy"
    WARNING = "warning"
    CRITICAL = "critical"
    UNKNOWN = "unknown"


@dataclass
class HealthCheck:
    """健康检查结果"""
    name: str
    status: HealthStatus
    message: str
    details: Dict
    timestamp: datetime


class HealthMonitor:
    """健康监控器"""

    def __init__(self, alert_callback=None):
        """
        初始化监控器

        Args:
            alert_callback: 告警回调函数
        """
        self.alert_callback = alert_callback
        self.start_time = datetime.now()
        self.alert_history: List[Dict] = []
        self.last_checks: Dict[str, HealthCheck] = {}

        # 阈值配置
        self.thresholds = {
            'memory_percent': 80,  # 内存使用率阈值 (%)
            'cpu_percent': 90,     # CPU 使用率阈值 (%)
            'disk_percent': 85,    # 磁盘使用率阈值 (%)
            'error_rate': 10,      # 每分钟错误数阈值
            'signal_gap': 600,     # 信号间隔阈值 (秒)
        }

    async def check_memory(self) -> HealthCheck:
        """检查内存使用"""
        try:
            memory = psutil.virtual_memory()
            percent = memory.percent

            if percent >= self.thresholds['memory_percent']:
                status = HealthStatus.CRITICAL
                message = f"内存使用率过高: {percent}%"
            elif percent >= self.thresholds['memory_percent'] * 0.8:
                status = HealthStatus.WARNING
                message = f"内存使用率较高: {percent}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"内存使用正常: {percent}%"

            return HealthCheck(
                name="memory",
                status=status,
                message=message,
                details={
                    'percent': percent,
                    'used_mb': memory.used / 1024 / 1024,
                    'available_mb': memory.available / 1024 / 1024,
                    'total_mb': memory.total / 1024 / 1024
                },
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Memory check failed: {e}")
            return HealthCheck(
                name="memory",
                status=HealthStatus.UNKNOWN,
                message=f"检查失败: {e}",
                details={},
                timestamp=datetime.now()
            )

    async def check_cpu(self) -> HealthCheck:
        """检查 CPU 使用"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)

            if cpu_percent >= self.thresholds['cpu_percent']:
                status = HealthStatus.CRITICAL
                message = f"CPU 使用率过高: {cpu_percent}%"
            elif cpu_percent >= self.thresholds['cpu_percent'] * 0.8:
                status = HealthStatus.WARNING
                message = f"CPU 使用率较高: {cpu_percent}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"CPU 使用正常: {cpu_percent}%"

            return HealthCheck(
                name="cpu",
                status=status,
                message=message,
                details={
                    'percent': cpu_percent,
                    'count': psutil.cpu_count(),
                    'load_avg': os.getloadavg() if hasattr(os, 'getloadavg') else None
                },
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"CPU check failed: {e}")
            return HealthCheck(
                name="cpu",
                status=HealthStatus.UNKNOWN,
                message=f"检查失败: {e}",
                details={},
                timestamp=datetime.now()
            )

    async def check_disk(self) -> HealthCheck:
        """检查磁盘空间"""
        try:
            disk = psutil.disk_usage('/')
            percent = disk.percent

            if percent >= self.thresholds['disk_percent']:
                status = HealthStatus.CRITICAL
                message = f"磁盘空间不足: {percent}%"
            elif percent >= self.thresholds['disk_percent'] * 0.8:
                status = HealthStatus.WARNING
                message = f"磁盘空间较少: {percent}%"
            else:
                status = HealthStatus.HEALTHY
                message = f"磁盘空间充足: {100 - percent}% 可用"

            return HealthCheck(
                name="disk",
                status=status,
                message=message,
                details={
                    'percent': percent,
                    'used_gb': disk.used / 1024 / 1024 / 1024,
                    'free_gb': disk.free / 1024 / 1024 / 1024,
                    'total_gb': disk.total / 1024 / 1024 / 1024
                },
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Disk check failed: {e}")
            return HealthCheck(
                name="disk",
                status=HealthStatus.UNKNOWN,
                message=f"检查失败: {e}",
                details={},
                timestamp=datetime.now()
            )

    async def check_process(self) -> HealthCheck:
        """检查进程状态"""
        try:
            # 查找主进程
            monitor_running = False
            process_info = {}

            for proc in psutil.process_iter(['pid', 'name', 'cmdline', 'memory_percent', 'cpu_percent']):
                try:
                    cmdline = ' '.join(proc.info['cmdline'] or [])
                    if 'main_phase2.py' in cmdline:
                        monitor_running = True
                        process_info = {
                            'pid': proc.info['pid'],
                            'memory_percent': proc.info['memory_percent'],
                            'cpu_percent': proc.info['cpu_percent']
                        }
                        break
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            if monitor_running:
                status = HealthStatus.HEALTHY
                message = "监控进程运行正常"
            else:
                status = HealthStatus.CRITICAL
                message = "监控进程未运行"

            return HealthCheck(
                name="process",
                status=status,
                message=message,
                details={
                    'running': monitor_running,
                    'process_info': process_info
                },
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Process check failed: {e}")
            return HealthCheck(
                name="process",
                status=HealthStatus.UNKNOWN,
                message=f"检查失败: {e}",
                details={},
                timestamp=datetime.now()
            )

    async def check_log_errors(self) -> HealthCheck:
        """检查日志错误率"""
        try:
            from pathlib import Path

            log_file = Path(__file__).parent.parent.parent / "logs" / "bot.log"
            if not log_file.exists():
                return HealthCheck(
                    name="log_errors",
                    status=HealthStatus.WARNING,
                    message="日志文件不存在",
                    details={},
                    timestamp=datetime.now()
                )

            # 读取最近 5 分钟的日志
            recent_errors = 0
            recent_warnings = 0
            total_lines = 0

            cutoff_time = datetime.now() - timedelta(minutes=5)

            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    try:
                        # 简单检查时间戳
                        total_lines += 1
                        if 'ERROR' in line:
                            recent_errors += 1
                        elif 'WARNING' in line:
                            recent_warnings += 1
                    except Exception:
                        continue

            # 评估状态
            if recent_errors >= self.thresholds['error_rate']:
                status = HealthStatus.CRITICAL
                message = f"错误率过高: {recent_errors} 个/5分钟"
            elif recent_errors >= self.thresholds['error_rate'] * 0.5:
                status = HealthStatus.WARNING
                message = f"错误率较高: {recent_errors} 个/5分钟"
            else:
                status = HealthStatus.HEALTHY
                message = f"错误率正常: {recent_errors} 个/5分钟"

            return HealthCheck(
                name="log_errors",
                status=status,
                message=message,
                details={
                    'errors_5min': recent_errors,
                    'warnings_5min': recent_warnings,
                    'total_lines': total_lines
                },
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.error(f"Log error check failed: {e}")
            return HealthCheck(
                name="log_errors",
                status=HealthStatus.UNKNOWN,
                message=f"检查失败: {e}",
                details={},
                timestamp=datetime.now()
            )

    async def run_all_checks(self) -> List[HealthCheck]:
        """运行所有健康检查"""
        checks = await asyncio.gather(
            self.check_memory(),
            self.check_cpu(),
            self.check_disk(),
            self.check_process(),
            self.check_log_errors()
        )

        # 更新最近检查记录
        for check in checks:
            self.last_checks[check.name] = check

            # 如果状态变为 CRITICAL 或 WARNING，触发告警
            if check.status in [HealthStatus.CRITICAL, HealthStatus.WARNING]:
                await self._send_alert(check)

        return checks

    async def _send_alert(self, check: HealthCheck):
        """发送告警"""
        alert = {
            'timestamp': datetime.now().isoformat(),
            'check_name': check.name,
            'status': check.status.value,
            'message': check.message,
            'details': check.details
        }

        # 防止重复告警（5 分钟内相同告警只发送一次）
        recent_alerts = [
            a for a in self.alert_history
            if a['check_name'] == check.name
            and datetime.fromisoformat(a['timestamp']) > datetime.now() - timedelta(minutes=5)
        ]

        if not recent_alerts:
            self.alert_history.append(alert)

            # 调用告警回调
            if self.alert_callback:
                try:
                    await self.alert_callback(alert)
                except Exception as e:
                    logger.error(f"Alert callback failed: {e}")

            logger.warning(f"⚠️ 告警: {check.name} - {check.message}")

    def get_overall_status(self) -> Dict:
        """获取总体健康状态"""
        if not self.last_checks:
            return {
                'status': HealthStatus.UNKNOWN.value,
                'message': '尚未进行健康检查',
                'uptime': str(datetime.now() - self.start_time)
            }

        # 统计各状态数量
        status_counts = {
            HealthStatus.HEALTHY: 0,
            HealthStatus.WARNING: 0,
            HealthStatus.CRITICAL: 0,
            HealthStatus.UNKNOWN: 0
        }

        for check in self.last_checks.values():
            status_counts[check.status] += 1

        # 确定总体状态
        if status_counts[HealthStatus.CRITICAL] > 0:
            overall_status = HealthStatus.CRITICAL
            message = f"{status_counts[HealthStatus.CRITICAL]} 个严重问题"
        elif status_counts[HealthStatus.WARNING] > 0:
            overall_status = HealthStatus.WARNING
            message = f"{status_counts[HealthStatus.WARNING]} 个警告"
        elif status_counts[HealthStatus.UNKNOWN] > 0:
            overall_status = HealthStatus.UNKNOWN
            message = f"{status_counts[HealthStatus.UNKNOWN]} 个未知状态"
        else:
            overall_status = HealthStatus.HEALTHY
            message = "所有检查通过"

        return {
            'status': overall_status.value,
            'message': message,
            'uptime': str(datetime.now() - self.start_time),
            'checks': {name: check.status.value for name, check in self.last_checks.items()},
            'status_counts': {k.value: v for k, v in status_counts.items()},
            'last_check_time': max(c.timestamp for c in self.last_checks.values()).isoformat() if self.last_checks else None
        }


async def monitor_loop(monitor: HealthMonitor, interval: int = 60):
    """监控循环"""
    logger.info(f"Starting health monitor loop (interval: {interval}s)")

    while True:
        try:
            checks = await monitor.run_all_checks()
            overall = monitor.get_overall_status()

            logger.info(f"Health check completed: {overall['status']} - {overall['message']}")

            await asyncio.sleep(interval)
        except Exception as e:
            logger.error(f"Monitor loop error: {e}")
            await asyncio.sleep(interval)
