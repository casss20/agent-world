import os
from typing import Optional
from infrastructure.interfaces.base_file_provider import BaseFileProvider

class LocalFileProvider(BaseFileProvider):
    def __init__(self, base_path: str = "./uploads"):
        self.base_path = base_path
        os.makedirs(base_path, exist_ok=True)

    def initialize(self) -> bool:
        os.makedirs(self.base_path, exist_ok=True)
        return True

    async def upload(self, file: bytes, path: str, mime_type: str = None) -> str:
        full_path = os.path.join(self.base_path, path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "wb") as f:
            f.write(file)
        return full_path

    async def download(self, path: str) -> bytes:
        full_path = os.path.join(self.base_path, path)
        with open(full_path, "rb") as f:
            return f.read()

    async def delete(self, path: str) -> bool:
        full_path = os.path.join(self.base_path, path)
        if os.path.exists(full_path):
            os.remove(full_path)
            return True
        return False

    async def get_url(self, path: str, expiry: int = None) -> str:
        return os.path.join(self.base_path, path)

    async def exists(self, path: str) -> bool:
        return os.path.exists(os.path.join(self.base_path, path))

    async def health_check(self) -> bool:
        return os.path.exists(self.base_path)
