"""RepoHarness 的统一异常类型。"""


class RepoHarnessError(Exception):
    """RepoHarness 所有可预期业务异常的基类。"""


class ConfigError(RepoHarnessError):
    """运行配置读取或校验失败。"""


class TaskValidationError(RepoHarnessError):
    """任务定义读取、校验或规范化失败。"""


class WorkspaceError(RepoHarnessError):
    """工作区创建、路径解析、命令执行或补丁处理失败。"""


class ToolExecutionError(RepoHarnessError):
    """工具查找、输入校验或执行失败。"""


class PermissionError(RepoHarnessError):
    """权限策略拒绝或无法确定一次操作是否允许。"""


class VerifierError(RepoHarnessError):
    """验证器执行或解析失败。"""


class ExportError(RepoHarnessError):
    """训练数据导出失败。"""
