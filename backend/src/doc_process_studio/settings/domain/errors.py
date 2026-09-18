"""settings 领域错误。"""


class SettingsError(Exception):
    """settings 域基础异常。"""


class InvalidBaseUrlError(SettingsError):
    """Base URL 非法（协议不支持 / 格式错误 / 过长）。"""


class InvalidSettingValueError(SettingsError):
    """设置值非法。"""
