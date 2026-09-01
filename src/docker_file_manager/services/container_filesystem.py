from __future__ import annotations

import posixpath
from datetime import datetime, timezone
from typing import Any

from docker.errors import APIError

from docker_file_manager.models import FileEntry
from docker_file_manager.services.errors import FileManagerError, PermissionDeniedError


class ContainerFileSystem:
    """Container filesystem facade; widgets never invoke Docker operations directly."""

    _FIND_FORMAT = "%f\\0%y\\0%s\\0%T@\\0"

    def list_directory(self, container: Any, path: str) -> list[FileEntry]:
        path = self.normalize(path)
        try:
            result = container.exec_run(
                ["find", path, "-mindepth", "1", "-maxdepth", "1", "-printf", self._FIND_FORMAT],
                stdout=True,
                stderr=True,
            )
        except APIError as exc:
            self._raise_api_error(exc)
        if result.exit_code != 0:
            detail = result.output.decode("utf-8", "replace").strip()
            if "permission denied" in detail.lower():
                raise PermissionDeniedError(f"Sem permissão para listar {path}.")
            raise FileManagerError(detail or f"Não foi possível listar {path}.")
        fields = result.output.split(b"\0")
        entries: list[FileEntry] = []
        for index in range(0, len(fields) - 3, 4):
            name = fields[index].decode("utf-8", "surrogateescape")
            type_code = fields[index + 1].decode("ascii", "replace")
            try:
                size = int(fields[index + 2])
                timestamp = float(fields[index + 3])
            except ValueError:
                continue
            kind = {"d": "directory", "l": "symlink", "f": "file"}.get(type_code, "special")
            entries.append(FileEntry(name, posixpath.join(path, name), type_code == "d", size, datetime.fromtimestamp(timestamp, timezone.utc), kind))
        return sorted(entries, key=lambda entry: (not entry.is_dir, entry.name.casefold()))

    def stat(self, container: Any, path: str) -> dict[str, Any]:
        try:
            _, stat = container.get_archive(self.normalize(path))
            return stat
        except APIError as exc:
            self._raise_api_error(exc)

    @staticmethod
    def normalize(path: str) -> str:
        normalized = posixpath.normpath("/" + path.lstrip("/"))
        if not normalized.startswith("/"):
            raise FileManagerError("Caminho inválido no container.")
        return normalized

    @staticmethod
    def _raise_api_error(exc: APIError) -> None:
        detail = (getattr(exc, "explanation", None) or str(exc)).lower()
        if "permission denied" in detail:
            raise PermissionDeniedError("Permissão negada dentro do container.") from exc
        if "no such" in detail or "not found" in detail:
            raise FileManagerError("O arquivo ou diretório não existe mais.") from exc
        raise FileManagerError(f"Falha na operação do container: {getattr(exc, 'explanation', str(exc))}") from exc

