from realitydb._proxy import DocumentFile
from dataclasses import dataclass, field

@dataclass
class DummyObject:
    name: str = field(default="dummy")
    value: int = field(default=0)

class TestDocumentFile(DocumentFile[DummyObject]):
    def __init__(self, name: str = "dummy.txt"):
        super().__init__()
        self.name = name  # Ensure 'name' is available
        self.file = self.__load__()

    def __load__(self) -> DummyObject:
        return DummyObject(value=10)

    def extract_text(self):
        for chunk in ["Hello", "world"]:
            yield chunk

    def extract_images(self):
        for image in [b"image1", b"image2"]:
            yield image

import pytest
from unittest.mock import patch

@patch('os.path.getsize', return_value=1024)  # Mock file size
@patch('mimetypes.guess_type', return_value=('text/plain', None))  # Mock MIME type
def test_document_file(mock_mime, mock_getsize):
    file = TestDocumentFile(name="dummy.txt")
    assert file.value == 10

@patch('os.path.getsize', return_value=1024)
@patch('mimetypes.guess_type', return_value=('text/plain', None))
def test_document_file_extract_text(mock_mime, mock_getsize):
    file = TestDocumentFile(name="dummy.txt")
    assert list(file.extract_text()) == ["Hello", "world"]

@patch('os.path.getsize', return_value=1024)
@patch('mimetypes.guess_type', return_value=('text/plain', None))
def test_document_file_extract_images(mock_mime, mock_getsize):
    file = TestDocumentFile(name="dummy.txt")
    assert list(file.extract_images()) == [b"image1", b"image2"]
