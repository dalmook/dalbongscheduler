class TaskExecutionError(Exception):
    pass


class TaskRunNotFoundError(Exception):
    pass


class TaskArtifactNotFoundError(Exception):
    pass


class InvalidParamsJsonError(Exception):
    pass


class UnsupportedTaskTypeError(Exception):
    pass
