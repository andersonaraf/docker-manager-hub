from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ContainerInfo:
    id: str
    name: str
    status: str
    image: str

    @property
    def is_running(self) -> bool:
        return self.status == "running"

