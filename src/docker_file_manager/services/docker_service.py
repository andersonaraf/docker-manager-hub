from __future__ import annotations

from typing import Any

import docker
from docker.errors import APIError, DockerException, NotFound

from docker_file_manager.models import ContainerInfo
from docker_file_manager.services.errors import DockerUnavailableError, FileManagerError, PermissionDeniedError


class DockerService:
    def __init__(self, client: Any | None = None) -> None:
        try:
            self.client = client or docker.from_env()
        except DockerException as exc:
            raise self._friendly_error(exc) from exc

    def ping(self) -> None:
        try:
            self.client.ping()
        except DockerException as exc:
            raise self._friendly_error(exc) from exc

    def list_containers(self) -> list[ContainerInfo]:
        try:
            containers = self.client.containers.list(all=True)
        except DockerException as exc:
            raise self._friendly_error(exc) from exc
        result = []
        for item in containers:
            tags = item.image.tags if item.image else []
            image_name = tags[0] if tags else (item.image.short_id if item.image else "<desconhecida>")
            result.append(ContainerInfo(item.id, item.name, item.status, image_name))
        return sorted(result, key=lambda c: (not c.is_running, c.name.casefold()))

    def get_container(self, container_id: str) -> Any:
        try:
            return self.client.containers.get(container_id)
        except NotFound as exc:
            raise FileManagerError("O container não existe mais.") from exc
        except DockerException as exc:
            raise self._friendly_error(exc) from exc

    @staticmethod
    def _friendly_error(exc: Exception) -> FileManagerError:
        message = str(exc).lower()
        if "permission denied" in message:
            return PermissionDeniedError("Sem permissão para acessar o Docker. Adicione o usuário ao grupo docker ou ajuste o socket.")
        if isinstance(exc, APIError):
            return FileManagerError(f"O Docker recusou a operação: {exc.explanation}")
        return DockerUnavailableError("Não foi possível conectar ao Docker local. Verifique se o serviço está em execução.")
