import re
import urllib.request

from ndlmpanel_agent.exceptions import (
    ServiceUnavailableException,
    ToolExecutionException,
)
from ndlmpanel_agent.models.ops.misc.nginx_models import NginxInstallInfo, NginxStatus,NginxSiteCreateResult
from ndlmpanel_agent.tools.ops._command_runner import runCommand

def checkNginxInstalled() -> NginxInstallInfo:
    try:
        result = runCommand(["nginx", "-v"], checkReturnCode=False)
        output = result.stderr.strip() or result.stdout.strip()

        version = None
        vMatch = re.search(r"nginx/([\d.]+)", output)
        if vMatch:
            version = vMatch.group(1)

        configPath = None
        testResult = runCommand(["nginx", "-t"], checkReturnCode=False)
        cMatch = re.search(r"configuration file (\S+)", testResult.stderr)
        if cMatch:
            configPath = cMatch.group(1)

        return NginxInstallInfo(
            isInstalled=True, version=version, configPath=configPath
        )
    except ToolExecutionException:
        return NginxInstallInfo(isInstalled=False)


def getNginxStatus() -> NginxStatus:
    if not checkNginxInstalled().isInstalled:
        raise ServiceUnavailableException("Nginx 未安装")

    isRunning = False
    workerCount = 0

    try:
        result = runCommand(["systemctl", "is-active", "nginx"], checkReturnCode=False)
        isRunning = result.stdout.strip() == "active"
    except ToolExecutionException:
        pass

    if isRunning:
        try:
            result = runCommand(
                ["pgrep", "-c", "-f", "nginx: worker"], checkReturnCode=False
            )
            workerCount = int(result.stdout.strip())
        except (ToolExecutionException, ValueError):
            pass

    # 尝试读取 stub_status 获取连接数
    activeConnections = None
    try:
        resp = urllib.request.urlopen("http://127.0.0.1/nginx_status", timeout=2)
        content = resp.read().decode()
        connMatch = re.search(r"Active connections:\s*(\d+)", content)
        if connMatch:
            activeConnections = int(connMatch.group(1))
    except Exception:
        pass

    return NginxStatus(
        isRunning=isRunning,
        workerProcessCount=workerCount,
        activeConnections=activeConnections,
        requestsPerSecond=None,
    )

def buildStaticSiteConfig(domain: str, rootPath: str, listenPort: int = 80) -> str:
    return f"""server {{
    listen {listenPort};
    server_name {domain};
    root {rootPath};
    index index.html;
    location / {{
        try_files $uri $uri/ =404;
    }}
}}"""

def buildProxyConfig(domain: str, proxyPass: str, listenPort: int) -> str:
    return f"""server {{
    listen {listenPort};
    server_name {domain};
    location / {{
        proxy_pass {proxyPass};
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }}
}}"""

def createNginxSite(
        domain: str,
        mode: str,
        listenPort: int,
        rootPath: str | None = None,
        proxyPass: str | None = None
)-> NginxSiteCreateResult:
    mode = mode.strip().lower()
    if mode == "static":
        if not rootPath:
            raise ToolExecutionException("静态站点必须提供 rootPath")
        configContent = buildStaticSiteConfig(domain, rootPath, listenPort)
    elif mode == "reverse_proxy":
        if not proxyPass:
            raise ToolExecutionException("反向代理必须提供 proxyPass")
        configContent = buildProxyConfig(domain, proxyPass, listenPort)
    else:
        raise ToolExecutionException("不支持的模式")
    
    siteName = domain.replace("*.", "").replace("/", "_")
    configPath = f"/etc/nginx/sites-available/{siteName}.conf"
    enabledPath = f"/etc/nginx/sites-enabled/{siteName}.conf"
    return NginxSiteCreateResult(
        domain=domain,
        mode=mode,
        listenPort=listenPort,
        configPath=configPath,
        enabledPath=enabledPath,
        rootPath=rootPath if mode == "static" else None,
        proxyPass=proxyPass if mode == "reverse_proxy" else None,
        isEnabled=False,
        isReloaded=False,
    )   