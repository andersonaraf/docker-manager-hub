from __future__ import annotations

import os
import posixpath
import shutil
import tarfile
import tempfile
from collections.abc import Callable, Iterable
from pathlib import Path
from typing import Any, BinaryIO

from docker.errors import APIError

from docker_file_manager.services.container_filesystem import ContainerFileSystem
from docker_file_manager.services.errors import FileManagerError, TransferCancelled, UnsafeArchiveError

ProgressCallback = Callable[[int, int | None, str], None]
CancelCallback = Callable[[], bool]


class TransferService:
    def __init__(self, chunk_size: int = 1024 * 1024) -> None:
        self.chunk_size = chunk_size

    def download(
        self,
        container: Any,
        sources: Iterable[str],
        destination: Path,
        progress: ProgressCallback,
        cancelled: CancelCallback,
    ) -> None:
        destination = destination.resolve()
        if not destination.is_dir():
            raise FileManagerError("O destino no host não é um diretório.")
        for source in sources:
            self._check_cancel(cancelled)
            source = ContainerFileSystem.normalize(source)
            try:
                stream, metadata = container.get_archive(source)
            except APIError as exc:
                ContainerFileSystem._raise_api_error(exc)
            expected = metadata.get("size") if isinstance(metadata, dict) else None
            with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b") as archive:
                transferred = 0
                for chunk in stream:
                    self._check_cancel(cancelled)
                    archive.write(chunk)
                    transferred += len(chunk)
                    progress(transferred, expected, posix_basename(source))
                archive.seek(0)
                self.safe_extract(archive, destination, cancelled)

    def upload(
        self,
        container: Any,
        sources: Iterable[Path],
        destination: str,
        progress: ProgressCallback,
        cancelled: CancelCallback,
    ) -> None:
        destination = ContainerFileSystem.normalize(destination)
        for source in sources:
            if source.is_symlink():
                raise FileManagerError(f"Links simbólicos não são suportados: {source.name}")
            source = source.resolve(strict=True)
            if not (source.is_file() or source.is_dir()):
                raise FileManagerError(f"Tipo de arquivo não suportado: {source.name}")
            self._check_cancel(cancelled)
            self._ensure_container_destination_available(container, posixpath.join(destination, source.name))
            with tempfile.SpooledTemporaryFile(max_size=8 * 1024 * 1024, mode="w+b") as archive:
                with tarfile.open(fileobj=archive, mode="w") as tar:
                    tar.add(source, arcname=source.name, recursive=True, filter=self._safe_tar_filter)
                total = archive.tell()
                archive.seek(0)
                progress(0, total, source.name)
                try:
                    if not container.put_archive(destination, archive):
                        raise FileManagerError("O Docker não confirmou o envio do arquivo.")
                except APIError as exc:
                    ContainerFileSystem._raise_api_error(exc)
                progress(total, total, source.name)

    @staticmethod
    def _ensure_container_destination_available(container: Any, path: str) -> None:
        try:
            result = container.exec_run(["test", "-e", path], stdout=False, stderr=True)
        except APIError as exc:
            ContainerFileSystem._raise_api_error(exc)
        if result.exit_code == 0:
            raise FileManagerError(f"O destino já existe no container: {path}")
        if result.exit_code != 1:
            detail = result.output.decode("utf-8", "replace").strip() if result.output else ""
            raise FileManagerError(detail or f"Não foi possível validar o destino: {path}")

    def safe_extract(self, archive_file: BinaryIO, destination: Path, cancelled: CancelCallback) -> None:
        root = destination.resolve()
        with tarfile.open(fileobj=archive_file, mode="r:*") as tar:
            for member in tar:
                self._check_cancel(cancelled)
                target = (root / member.name).resolve()
                if target != root and root not in target.parents:
                    raise UnsafeArchiveError("O archive contém um caminho que escaparia do destino.")
                if member.issym() or member.islnk() or not (member.isfile() or member.isdir()):
                    raise UnsafeArchiveError(f"Entrada TAR não suportada por segurança: {member.name}")
                if target.exists():
                    raise FileManagerError(f"O destino já existe: {target.name}")
                if member.isdir():
                    target.mkdir(parents=True, exist_ok=False)
                    continue
                target.parent.mkdir(parents=True, exist_ok=True)
                source = tar.extractfile(member)
                if source is None:
                    raise UnsafeArchiveError(f"Não foi possível ler {member.name}.")
                with source, target.open("xb") as output:
                    shutil.copyfileobj(source, output, self.chunk_size)
                os.chmod(target, member.mode & 0o777)

    @staticmethod
    def _safe_tar_filter(info: tarfile.TarInfo) -> tarfile.TarInfo | None:
        if info.issym() or info.islnk() or not (info.isfile() or info.isdir()):
            return None
        info.uid = info.gid = 0
        info.uname = info.gname = ""
        return info

    @staticmethod
    def _check_cancel(cancelled: CancelCallback) -> None:
        if cancelled():
            raise TransferCancelled("Transferência cancelada.")


def posix_basename(path: str) -> str:
    return path.rstrip("/").rsplit("/", 1)[-1] or "/"
