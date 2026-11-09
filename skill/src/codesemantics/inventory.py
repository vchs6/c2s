"""Deterministic, ignore-file-independent filesystem inventory."""

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path


@dataclass(frozen=True, slots=True)
class InventoryEntry:
    path: str
    kind: str
    size_bytes: int | None
    state: str
    diagnostic: str | None = None


def inventory_tree(root: Path, *, excluded_dirs: frozenset[str] = frozenset()) -> list[InventoryEntry]:
    """List every descendant without following symlinks or honoring ignore files."""
    root = root.resolve(strict=True)
    entries: list[InventoryEntry] = []

    def visit(directory: Path) -> None:
        try:
            children = sorted(directory.iterdir(), key=lambda path: path.name)
        except OSError as error:
            relative = directory.relative_to(root).as_posix()
            entries.append(InventoryEntry(relative, "directory", None, "unreadable", type(error).__name__))
            return

        if directory != root:
            relative = directory.relative_to(root).as_posix()
            entries.append(InventoryEntry(relative, "directory", None, "readable"))
        for path in children:
            relative = path.relative_to(root).as_posix()
            try:
                if path.is_symlink():
                    entries.append(InventoryEntry(relative, "symlink", None, "unfollowed"))
                elif path.is_dir():
                    if path.name in excluded_dirs:
                        continue
                    visit(path)
                elif path.is_file():
                    entries.append(InventoryEntry(relative, "file", path.stat().st_size, "readable"))
                else:
                    entries.append(InventoryEntry(relative, "other", None, "unreadable", "SPECIAL_FILE"))
            except OSError as error:
                entries.append(InventoryEntry(relative, "other", None, "unreadable", type(error).__name__))

    visit(root)
    return entries


def source_fingerprint(root: Path) -> str:
    """Hash the complete visible project tree without following symlinks."""
    root = root.resolve(strict=True)
    digest = hashlib.sha256()
    for entry in inventory_tree(root, excluded_dirs=frozenset({".git"})):
        path = root / entry.path
        digest.update(entry.path.encode("utf-8"))
        digest.update(b"\0" + entry.kind.encode("ascii") + b"\0" + entry.state.encode("ascii") + b"\0")
        if entry.kind == "file":
            try:
                file_digest = hashlib.sha256()
                with path.open("rb") as handle:
                    for chunk in iter(lambda: handle.read(1024 * 1024), b""):
                        file_digest.update(chunk)
                digest.update(file_digest.hexdigest().encode("ascii"))
            except OSError as error:
                digest.update(f"READ_ERROR:{type(error).__name__}".encode("ascii"))
        elif entry.kind == "symlink":
            try:
                digest.update(os.readlink(path).encode("utf-8", errors="surrogateescape"))
            except OSError as error:
                digest.update(f"READLINK_ERROR:{type(error).__name__}".encode("ascii"))
        digest.update(b"\n")
    return digest.hexdigest()
