import io
import tarfile
from pathlib import Path

import pytest

from docker_file_manager.services.errors import FileManagerError, UnsafeArchiveError
from docker_file_manager.services.transfer_service import TransferService


def archive_with(name: str, content: bytes = b"data", kind: bytes | None = None) -> io.BytesIO:
    result = io.BytesIO()
    with tarfile.open(fileobj=result, mode="w") as tar:
        info = tarfile.TarInfo(name)
        info.size = len(content)
        if kind is not None:
            info.type = kind
        tar.addfile(info, io.BytesIO(content) if info.isfile() else None)
    result.seek(0)
    return result


def test_safe_extract_writes_regular_file(tmp_path: Path):
    TransferService().safe_extract(archive_with("hello.txt", b"hello"), tmp_path, lambda: False)
    assert (tmp_path / "hello.txt").read_bytes() == b"hello"


def test_safe_extract_rejects_path_traversal(tmp_path: Path):
    with pytest.raises(UnsafeArchiveError):
        TransferService().safe_extract(archive_with("../escape.txt"), tmp_path, lambda: False)


def test_safe_extract_rejects_symlink(tmp_path: Path):
    archive = archive_with("link", b"", tarfile.SYMTYPE)
    with pytest.raises(UnsafeArchiveError):
        TransferService().safe_extract(archive, tmp_path, lambda: False)


def test_safe_extract_does_not_overwrite(tmp_path: Path):
    (tmp_path / "hello.txt").write_text("existing")
    with pytest.raises(FileManagerError, match="já existe"):
        TransferService().safe_extract(archive_with("hello.txt"), tmp_path, lambda: False)

