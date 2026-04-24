import os
import re
import tempfile
import urllib.request
from pathlib import Path

from ndlmpanel_agent.exceptions import (
    PermissionDeniedException,
    ServiceUnavailableException,
    ToolExecutionException,
)
from ndlmpanel_agent.models.ops.misc.nginx_models import (
    NginxInstallInfo,
    NginxSiteCreateResult,
    NginxStatus,
)
from ndlmpanel_agent.tools.ops._command_runner import runCommand


_DOMAIN_PATTERN = re.compile(
    r"^(\*\.)?([A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"[A-Za-z]{2,63}$"
)
_SITE_NAME_PATTERN = re.compile(r"[^A-Za-z0-9_.-]+")
_UNSAFE_NGINX_VALUE_PATTERN = re.compile(r"[\r\n;{}]")


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


def _validateDomainName(domainName: str) -> None:
    if not _DOMAIN_PATTERN.fullmatch(domainName):
        raise ToolExecutionException(f"非法域名: {domainName}")


def _buildSafeSiteName(domainName: str) -> str:
    return _SITE_NAME_PATTERN.sub("_", domainName.lstrip("*."))


def _validateNginxValue(value: str, name: str) -> None:
    if _UNSAFE_NGINX_VALUE_PATTERN.search(value):
        raise ToolExecutionException(f"{name} 包含非法字符")


def _quoteNginxValue(value: str) -> str:
    return '"' + value.replace("\\", "\\\\").replace('"', '\\"') + '"'


def _writeConfigFile(configPath: Path, content: str, useSudo: bool) -> None:
    if useSudo:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            delete=False,
            prefix="ndlmpanel-nginx-",
            suffix=".conf",
        ) as tmpFile:
            tmpFile.write(content)
            tmpPath = tmpFile.name

        try:
            runCommand(
                ["install", "-d", "-m", "755", str(configPath.parent)],
                useSudo=True,
            )
            runCommand(
                ["install", "-m", "644", tmpPath, str(configPath)],
                useSudo=True,
            )
        finally:
            try:
                os.unlink(tmpPath)
            except OSError:
                pass
        return

    try:
        configPath.parent.mkdir(parents=True, exist_ok=True)
        configPath.write_text(content, encoding="utf-8")
    except PermissionError as e:
        raise PermissionDeniedException(f"写入 Nginx 配置失败: {configPath}", e)
    except OSError as e:
        raise ToolExecutionException(f"写入 Nginx 配置失败: {configPath}", e)


def _enableSite(configPath: Path, enabledPath: Path, useSudo: bool) -> None:
    if useSudo:
        runCommand(
            ["install", "-d", "-m", "755", str(enabledPath.parent)],
            useSudo=True,
        )
        runCommand(
            ["ln", "-sfn", str(configPath), str(enabledPath)],
            useSudo=True,
        )
        return

    try:
        enabledPath.parent.mkdir(parents=True, exist_ok=True)
        if enabledPath.is_symlink() or enabledPath.exists():
            enabledPath.unlink()
        enabledPath.symlink_to(configPath)
    except PermissionError as e:
        raise PermissionDeniedException(f"启用 Nginx 站点失败: {enabledPath}", e)
    except OSError as e:
        raise ToolExecutionException(f"启用 Nginx 站点失败: {enabledPath}", e)


def _disableSite(enabledPath: Path, useSudo: bool) -> None:
    if useSudo:
        runCommand(["rm", "-f", str(enabledPath)], useSudo=True, checkReturnCode=False)
        return

    try:
        if enabledPath.is_symlink() or enabledPath.exists():
            enabledPath.unlink()
    except OSError:
        pass


def _buildStaticSiteConfig(domainName: str, listenPort: int, rootPath: str) -> str:
    quotedRootPath = _quoteNginxValue(rootPath)
    return f"""server {{
    listen {listenPort};
    server_name {domainName};

    root {quotedRootPath};
    index index.html index.htm;

    location / {{
        try_files $uri $uri/ =404;
    }}
}}
"""


def _buildReverseProxyConfig(domainName: str, listenPort: int, proxyPass: str) -> str:
    return f"""server {{
    listen {listenPort};
    server_name {domainName};

    location / {{
        proxy_pass {proxyPass};
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }}
}}
"""


def createNginxSite(
    domainName: str,
    mode: str,
    rootPath: str | None = None,
    proxyPass: str | None = None,
    listenPort: int = 80,
    enableSite: bool = True,
    reloadNginx: bool = True,
    useSudo: bool = True,
    overwriteExisting: bool = False,
) -> NginxSiteCreateResult:
    """
    新建 Nginx 站点配置，支持纯静态网站和反向代理两种模式。

    Args:
        domainName: 站点域名，例如 example.com 或 *.example.com
        mode: 站点模式，只能是 static 或 reverse_proxy
        rootPath: static 模式的网站根目录，必须是绝对路径
        proxyPass: reverse_proxy 模式的上游地址，例如 http://127.0.0.1:3000
        listenPort: Nginx 监听端口，默认 80
        enableSite: 是否创建 sites-enabled 软链启用站点
        reloadNginx: 是否在 nginx -t 通过后 reload nginx
        useSudo: 是否使用 sudo -n 写入 /etc/nginx 并 reload 服务
        overwriteExisting: 是否允许覆盖同名配置文件，默认不覆盖
    """
    if not checkNginxInstalled().isInstalled:
        raise ServiceUnavailableException("Nginx 未安装")

    mode = mode.strip().lower()
    _validateDomainName(domainName)

    if listenPort < 1 or listenPort > 65535:
        raise ToolExecutionException("listenPort 必须在 1-65535 之间")

    if mode == "static":
        if not rootPath:
            raise ToolExecutionException("static 模式必须提供 rootPath")
        root = Path(rootPath)
        if not root.is_absolute():
            raise ToolExecutionException("rootPath 必须是绝对路径")
        _validateNginxValue(rootPath, "rootPath")
        configContent = _buildStaticSiteConfig(domainName, listenPort, rootPath)
    elif mode == "reverse_proxy":
        if not proxyPass:
            raise ToolExecutionException("reverse_proxy 模式必须提供 proxyPass")
        if not re.match(r"^https?://[^\s;{}]+$", proxyPass):
            raise ToolExecutionException("proxyPass 必须以 http:// 或 https:// 开头")
        _validateNginxValue(proxyPass, "proxyPass")
        configContent = _buildReverseProxyConfig(domainName, listenPort, proxyPass)
    else:
        raise ToolExecutionException("mode 只能是 static 或 reverse_proxy")

    siteName = _buildSafeSiteName(domainName)
    configPath = Path("/etc/nginx/sites-available") / f"{siteName}.conf"
    enabledPath = Path("/etc/nginx/sites-enabled") / f"{siteName}.conf"

    if not overwriteExisting and (configPath.exists() or enabledPath.exists()):
        raise ToolExecutionException(f"Nginx 站点已存在: {siteName}.conf")

    _writeConfigFile(configPath, configContent, useSudo=useSudo)

    isEnabled = False
    if enableSite:
        _enableSite(configPath, enabledPath, useSudo=useSudo)
        isEnabled = True

    try:
        runCommand(["nginx", "-t"], useSudo=useSudo)
    except ToolExecutionException:
        if isEnabled and not overwriteExisting:
            _disableSite(enabledPath, useSudo=useSudo)
        raise

    isReloaded = False
    if reloadNginx:
        try:
            runCommand(["systemctl", "reload", "nginx"], useSudo=useSudo)
        except ToolExecutionException:
            runCommand(["nginx", "-s", "reload"], useSudo=useSudo)
        isReloaded = True

    return NginxSiteCreateResult(
        domainName=domainName,
        mode=mode,
        listenPort=listenPort,
        configPath=str(configPath),
        enabledPath=str(enabledPath) if isEnabled else None,
        rootPath=rootPath if mode == "static" else None,
        proxyPass=proxyPass if mode == "reverse_proxy" else None,
        isEnabled=isEnabled,
        isReloaded=isReloaded,
    )
