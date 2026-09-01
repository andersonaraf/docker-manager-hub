class FileManagerError(Exception):
    """An error safe to display in the UI."""


class DockerUnavailableError(FileManagerError):
    pass


class PermissionDeniedError(FileManagerError):
    pass


class TransferCancelled(FileManagerError):
    pass


class UnsafeArchiveError(FileManagerError):
    pass

