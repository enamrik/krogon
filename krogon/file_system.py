from typing import Callable, Optional, List, Any
import krogon.either as E
import os
import glob as gb
import tempfile


class FileSystem:
    def __init__(self): pass

    def with_temp_file(self, contents: str, filename: str, runner: Callable[[str], E.Either[Any, Any]]):
        with tempfile.TemporaryDirectory() as tmp_dirname:
            file_path = tmp_dirname + '/' + filename
            self.write(file_path, contents)
            return runner(file_path)

    def path_rel_to_app_dir(self, file_path: str) -> str:
        return self.path_rel_to_file(file_path, __file__)

    def path_rel_to_file(self, file_path: str, file_name: str) -> str:
        return os.path.dirname(os.path.abspath(file_name))+'/'+file_path

    def path_rel_to_cwd(self, file_path: str):
        return os.path.abspath(self.cwd()+'/'+file_path)

    def read(self, file_path: str) -> str:
        with open(file_path) as f:
            return f.read()

    def write(self, file_path: str, content: str, flags: Optional[str] = 'w') -> None:
        with open(file_path, flags) as file:
            file.write(content)

    def delete(self, file_path: str) -> None:
        if os.path.exists(file_path):
            os.remove(file_path)

    def exists(self, file_path: str) -> bool:
        return os.path.exists(file_path)

    def mkdir(self, folder: str) -> None:
        os.mkdir(folder)

    def cwd(self) -> str:
        return os.getcwd()

    def glob(self, path: str):
        return gb.glob(path)


def file_system():
    return FileSystem()
