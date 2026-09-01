from docker_file_manager.services.container_filesystem import ContainerFileSystem


class Result:
    exit_code = 0
    output = b"\0".join([b"folder", b"d", b"4096", b"1700000000.0", b"file.txt", b"f", b"12", b"1700000001.0", b""])


class Container:
    def exec_run(self, *args, **kwargs):
        return Result()


def test_list_directory_parses_nul_delimited_find_output():
    entries = ContainerFileSystem().list_directory(Container(), "/tmp")
    assert [entry.name for entry in entries] == ["folder", "file.txt"]
    assert entries[0].is_dir
    assert entries[1].size == 12


def test_normalize_keeps_path_inside_container_root():
    assert ContainerFileSystem.normalize("../../etc") == "/etc"
    assert ContainerFileSystem.normalize("/var/../tmp") == "/tmp"
