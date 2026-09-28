class AppError(Exception):
    def __init__(self, message: str, status_code: int = 400, code: str = "app_error"):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.code = code


class ConfigError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=500, code="config_error")


class ProviderError(AppError):
    def __init__(self, message: str, status_code: int = 502):
        super().__init__(message, status_code=status_code, code="provider_error")


class TaskNotFoundError(AppError):
    def __init__(self, task_id: str):
        super().__init__(f"任务不存在: {task_id}", status_code=404, code="task_not_found")


class MediaNotFoundError(AppError):
    def __init__(self, file_id: str):
        super().__init__(f"媒体文件不存在: {file_id}", status_code=404, code="media_not_found")


class UploadTooLargeError(AppError):
    def __init__(self, max_mb: int):
        super().__init__(f"上传文件超过 {max_mb}MB 限制", status_code=413, code="upload_too_large")


class UnauthorizedError(AppError):
    def __init__(self, message: str = "缺少或无效的 API Key"):
        super().__init__(message, status_code=401, code="unauthorized")


class TaskTimeoutError(AppError):
    def __init__(self, task_id: str):
        super().__init__(f"等待任务超时: {task_id}", status_code=504, code="task_timeout")


class InvalidUploadError(AppError):
    def __init__(self, message: str):
        super().__init__(message, status_code=400, code="invalid_upload")


class ConversationNotFoundError(AppError):
    def __init__(self, conversation_id: str):
        super().__init__(
            f"会话不存在: {conversation_id}",
            status_code=404,
            code="conversation_not_found",
        )


class InvalidConversationTurnError(AppError):
    def __init__(self, message: str = "有会话时 messages 必须恰好一条 role=user"):
        super().__init__(message, status_code=400, code="invalid_conversation_turn")
