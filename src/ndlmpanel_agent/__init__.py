"""
AI Ops Agent - 智能运维 Agent 核心模块

后端使用方式:
    from ai_ops_agent import AgentOrchestrator, AgentConfiguration

    config = AgentConfiguration(llm=LLMConfiguration(...))
    agent = AgentOrchestrator(config)
    response = await agent.handle_user_message(session_id, message)
"""

from ndlmpanel_agent.config import (
    AgentConfiguration,
    LLMConfiguration,
    SafetyConfiguration,
)
from ndlmpanel_agent.models import (
    CpuInfo,
    DatabaseInstallInfo,
    DatabaseStatus,
    DiskPartitionInfo,
    DockerContainer,
    DockerInstallInfo,
    FileInfo,
    FileOperationResult,
    FileType,
    FirewallBackendType,
    FirewallPortOperationResult,
    FirewallPortRule,
    FirewallStatus,
    GpuInfo,
    LoginRecord,
    LogQueryResult,
    MemoryInfo,
    MessageRole,
    NetworkInterfaceInfo,
    NginxInstallInfo,
    NginxStatus,
    OperationResult,
    OwnerChangeResult,
    PermissionChangeResult,
    PingResult,
    PortCheckResult,
    ProcessInfo,
    ProcessKillResult,
    ProcessSortBy,
    ServiceAction,
    ServiceOperationResult,
    SystemVersion,
    UptimeInfo,
    UserInfo,
)
from ndlmpanel_agent.models.agent.chat_models import AgentResponse, ChatMessage
from ndlmpanel_agent.agent.orchestrator import AgentOrchestrator
from ndlmpanel_agent.tools import (
    addFirewallPort,
    changeOwner,
    changePermissions,
    checkDatabaseInstalled,
    checkDockerInstalled,
    checkNginxInstalled,
    checkPortConnectivity,
    createDirectory,
    createFile,
    deleteDirectory,
    deleteFile,
    getCpuInfo,
    getDatabaseStatus,
    getDiskInfo,
    getDockerContainers,
    getEnvironmentVariables,
    getFirewallStatus,
    getGpuInfo,
    getLoginHistory,
    getMemoryInfo,
    getNetworkInfo,
    getNginxStatus,
    getSystemVersion,
    getUptime,
    killProcess,
    listDirectory,
    listFirewallPorts,
    listProcesses,
    listUsers,
    manageSystemService,
    pingHost,
    querySystemLogs,
    removeFirewallPort,
    renameFileOrDirectory,
)

ALL_TOOL_FUNCTIONS = [
    # 防火墙
    getFirewallStatus,
    listFirewallPorts,
    addFirewallPort,
    removeFirewallPort,
    # 系统监控
    getCpuInfo,
    getMemoryInfo,
    getDiskInfo,
    getGpuInfo,
    getNetworkInfo,
    # 文件系统
    listDirectory,
    createFile,
    createDirectory,
    deleteFile,
    deleteDirectory,
    renameFileOrDirectory,
    changePermissions,
    changeOwner,
    # 进程
    listProcesses,
    killProcess,
    # 日志
    querySystemLogs,
    # 用户
    listUsers,
    getLoginHistory,
    # 网络诊断
    pingHost,
    checkPortConnectivity,
    # 系统信息
    getSystemVersion,
    getUptime,
    getEnvironmentVariables,
    # Docker
    checkDockerInstalled,
    getDockerContainers,
    # Nginx
    checkNginxInstalled,
    getNginxStatus,
    # 数据库
    checkDatabaseInstalled,
    getDatabaseStatus,
    # 服务管理
    manageSystemService,
]

__all__ = [
    "AgentConfiguration",
    "LLMConfiguration",
    "SafetyConfiguration",
    "AgentOrchestrator",
    "AgentResponse",
    "ChatMessage",
    # 常用实体类（models）
    "MessageRole",
    "OperationResult",
    "FirewallBackendType",
    "FirewallStatus",
    "FirewallPortRule",
    "FirewallPortOperationResult",
    "CpuInfo",
    "MemoryInfo",
    "DiskPartitionInfo",
    "GpuInfo",
    "NetworkInterfaceInfo",
    "FileType",
    "FileInfo",
    "FileOperationResult",
    "PermissionChangeResult",
    "OwnerChangeResult",
    "ProcessSortBy",
    "ProcessInfo",
    "ProcessKillResult",
    "LogQueryResult",
    "UserInfo",
    "LoginRecord",
    "PingResult",
    "PortCheckResult",
    "SystemVersion",
    "UptimeInfo",
    "DockerInstallInfo",
    "DockerContainer",
    "NginxInstallInfo",
    "NginxStatus",
    "DatabaseInstallInfo",
    "DatabaseStatus",
    "ServiceAction",
    "ServiceOperationResult",
    "ALL_TOOL_FUNCTIONS",
    # 防火墙
    "getFirewallStatus",
    "listFirewallPorts",
    "addFirewallPort",
    "removeFirewallPort",
    # 系统监控
    "getCpuInfo",
    "getMemoryInfo",
    "getDiskInfo",
    "getGpuInfo",
    "getNetworkInfo",
    # 文件系统
    "listDirectory",
    "createFile",
    "createDirectory",
    "deleteFile",
    "deleteDirectory",
    "renameFileOrDirectory",
    "changePermissions",
    "changeOwner",
    # 进程
    "listProcesses",
    "killProcess",
    # 日志
    "querySystemLogs",
    # 用户
    "listUsers",
    "getLoginHistory",
    # 网络诊断
    "pingHost",
    "checkPortConnectivity",
    # 系统信息
    "getSystemVersion",
    "getUptime",
    "getEnvironmentVariables",
    # Docker
    "checkDockerInstalled",
    "getDockerContainers",
    # Nginx
    "checkNginxInstalled",
    "getNginxStatus",
    # 数据库
    "checkDatabaseInstalled",
    "getDatabaseStatus",
    # 服务管理
    "manageSystemService",
]
