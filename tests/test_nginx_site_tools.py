import subprocess
from pathlib import Path as RealPath

import pytest

from ndlmpanel_agent.exceptions import ToolExecutionException
from ndlmpanel_agent.tools.ops.misc import nginx_tools


def _patchNginxPaths(monkeypatch, tmp_path):
    nginxRoot = tmp_path / "nginx"

    def fakePath(value):
        path = RealPath(value)
        if str(path).startswith("/etc/nginx"):
            return nginxRoot / path.relative_to("/etc/nginx")
        return path

    monkeypatch.setattr(nginx_tools, "Path", fakePath)
    return nginxRoot


def _patchSuccessfulCommands(monkeypatch):
    commands = []

    def fakeRunCommand(command, timeout=30, checkReturnCode=True, useSudo=False):
        commands.append(
            {
                "command": command,
                "timeout": timeout,
                "checkReturnCode": checkReturnCode,
                "useSudo": useSudo,
            }
        )

        if command == ["nginx", "-v"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="",
                stderr="nginx version: nginx/1.24.0\n",
            )

        if command == ["nginx", "-t"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="",
                stderr=(
                    "nginx: the configuration file /etc/nginx/nginx.conf "
                    "syntax is ok\n"
                ),
            )

        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(nginx_tools, "runCommand", fakeRunCommand)
    return commands


def testCreateNginxStaticSite(monkeypatch, tmp_path):
    nginxRoot = _patchNginxPaths(monkeypatch, tmp_path)
    commands = _patchSuccessfulCommands(monkeypatch)
    siteRoot = tmp_path / "www" / "example.com"
    siteRoot.mkdir(parents=True)

    result = nginx_tools.createNginxSite(
        domainName="example.com",
        mode="static",
        rootPath=str(siteRoot),
        reloadNginx=False,
        useSudo=False,
    )

    configPath = nginxRoot / "sites-available" / "example.com.conf"
    enabledPath = nginxRoot / "sites-enabled" / "example.com.conf"

    assert result.domainName == "example.com"
    assert result.mode == "static"
    assert result.isEnabled is True
    assert result.isReloaded is False
    assert configPath.exists()
    assert enabledPath.is_symlink()
    assert enabledPath.resolve() == configPath

    config = configPath.read_text(encoding="utf-8")
    assert "server_name example.com;" in config
    assert f'root "{siteRoot}";' in config
    assert "try_files $uri $uri/ =404;" in config
    assert ["nginx", "-t"] in [item["command"] for item in commands]


def testCreateNginxReverseProxySite(monkeypatch, tmp_path):
    nginxRoot = _patchNginxPaths(monkeypatch, tmp_path)
    _patchSuccessfulCommands(monkeypatch)

    result = nginx_tools.createNginxSite(
        domainName="api.example.com",
        mode="reverse_proxy",
        proxyPass="http://127.0.0.1:3000",
        enableSite=False,
        reloadNginx=False,
        useSudo=False,
    )

    configPath = nginxRoot / "sites-available" / "api.example.com.conf"
    enabledPath = nginxRoot / "sites-enabled" / "api.example.com.conf"

    assert result.mode == "reverse_proxy"
    assert result.isEnabled is False
    assert result.enabledPath is None
    assert configPath.exists()
    assert not enabledPath.exists()

    config = configPath.read_text(encoding="utf-8")
    assert "server_name api.example.com;" in config
    assert "proxy_pass http://127.0.0.1:3000;" in config
    assert "proxy_set_header X-Real-IP $remote_addr;" in config


def testCreateNginxSiteRejectsInvalidMode(monkeypatch, tmp_path):
    _patchNginxPaths(monkeypatch, tmp_path)
    _patchSuccessfulCommands(monkeypatch)

    with pytest.raises(ToolExecutionException):
        nginx_tools.createNginxSite(
            domainName="example.com",
            mode="php",
            rootPath="/var/www/example.com",
            reloadNginx=False,
            useSudo=False,
        )


def testCreateNginxSiteRollsBackEnabledSymlinkWhenNginxTestFails(
    monkeypatch,
    tmp_path,
):
    nginxRoot = _patchNginxPaths(monkeypatch, tmp_path)
    nginxTestCount = 0

    def fakeRunCommand(command, timeout=30, checkReturnCode=True, useSudo=False):
        nonlocal nginxTestCount

        if command == ["nginx", "-v"]:
            return subprocess.CompletedProcess(
                command,
                0,
                stdout="",
                stderr="nginx version: nginx/1.24.0\n",
            )

        if command == ["nginx", "-t"]:
            nginxTestCount += 1
            if nginxTestCount == 1:
                return subprocess.CompletedProcess(command, 0, stdout="", stderr="")
            raise ToolExecutionException("nginx 配置测试失败")

        return subprocess.CompletedProcess(command, 0, stdout="", stderr="")

    monkeypatch.setattr(nginx_tools, "runCommand", fakeRunCommand)

    with pytest.raises(ToolExecutionException):
        nginx_tools.createNginxSite(
            domainName="bad.example.com",
            mode="reverse_proxy",
            proxyPass="http://127.0.0.1:3000",
            reloadNginx=False,
            useSudo=False,
        )

    configPath = nginxRoot / "sites-available" / "bad.example.com.conf"
    enabledPath = nginxRoot / "sites-enabled" / "bad.example.com.conf"

    assert configPath.exists()
    assert not enabledPath.exists()
