from pydantic import BaseModel


class NginxInstallInfo(BaseModel):
    isInstalled: bool
    version: str | None = None
    configPath: str | None = None


class NginxStatus(BaseModel):
    isRunning: bool
    workerProcessCount: int
    activeConnections: int | None = None
    requestsPerSecond: float | None = None


class NginxSiteCreateResult(BaseModel):
    domainName: str
    mode: str
    listenPort: int
    configPath: str
    enabledPath: str | None = None
    rootPath: str | None = None
    proxyPass: str | None = None
    isEnabled: bool
    isReloaded: bool
