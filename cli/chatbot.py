from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path

import orjson
import pathspec
from openai import OpenAI


@dataclass
class FileNode:
    path: str = ""
    type: str = ""
    content: str | list[FileNode] = field(default_factory=list)
    root_path: Path = field(
        default_factory=lambda: Path(__file__).parent.parent, repr=False
    )
    spec: pathspec.PathSpec | None = field(default=None, repr=False)

    def __post_init__(self):
        if self.spec is None:
            self.spec = self._load_gitignore()
        # Use root_path if self.path is empty
        self._build_node(Path(self.path or self.root_path))

    def _load_gitignore(self) -> pathspec.PathSpec | None:
        gitignore_file = self.root_path / ".gitignore"
        if gitignore_file.exists():
            with gitignore_file.open("r") as f:
                gitignore_patterns = f.read().splitlines()
            return pathspec.PathSpec.from_lines("gitwildmatch", gitignore_patterns)
        else:
            return None

    def _build_node(self, path: Path):
        relative_path = path.relative_to(self.root_path)
        # Ignore .git folder
        if relative_path == Path(".git") or str(relative_path).startswith(".git/"):
            self.type = "ignored"
            self.content = None
            return

        # Check if the path matches .gitignore patterns
        if self.spec and self.spec.match_file(str(relative_path)):
            self.type = "ignored"
            self.content = None
            return

        self.path = str(relative_path)
        if path.is_dir():
            self.type = "directory"
            self.content = []
            for child in sorted(path.iterdir()):
                child_node = FileNode(
                    path=str(child), root_path=self.root_path, spec=self.spec
                )
                if child_node.type != "ignored":
                    self.content.append(child_node)
        else:
            self.type = "file"
            try:
                self.content = path.read_text()
            except Exception:
                self.content = "[Binary file]"

    def to_dict(self):
        if isinstance(self.content, list):
            content = [child.to_dict() for child in self.content]
        else:
            content = self.content
        return {"path": self.path, "type": self.type, "content": content}

    def to_json(self) -> str:
        return orjson.dumps(self.to_dict()).decode()


ai = OpenAI()


def chatbot(user_id: str = str(uuid.uuid4())):
    messages = [
        {
            "role": "user",
            "content": f"Here is the project on json format:\n {FileNode().to_json()}",
        },
        {
            "role": "assistant",
            "content": "I am a senior Software Engineer. I will help you with your code. Give me a minute to deeply understand the codebase and I will provide you with code enhancements",
        },
    ]
    while True:
        message = input()
        messages.append({"role": "user", "content": message})
        response = ai.chat.completions.create(
            model="gpt-4o",
            messages=messages,  # type: ignore
            user=user_id,
            max_tokens=8192,
            stream=True,
        )
        for chunk in response:
            print(chunk.choices[0].delta.content, end="", flush=True)
        print()


if __name__ == "__main__":
    chatbot()
