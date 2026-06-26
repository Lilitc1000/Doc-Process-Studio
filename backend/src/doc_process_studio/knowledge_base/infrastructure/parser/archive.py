import logging
import os
import shutil
import tempfile
import zipfile
from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS = {".pdf", ".docx", ".doc", ".xlsx", ".xls"}


@dataclass
class ExtractedFile:
    relative_path: str
    file_name: str
    file_bytes: bytes
    file_type: str


def _detect_file_type(file_name: str) -> str:
    ext = Path(file_name).suffix.lower()
    type_map = {
        ".pdf": "pdf",
        ".docx": "docx",
        ".doc": "docx",
        ".xlsx": "xlsx",
        ".xls": "xlsx",
    }
    return type_map.get(ext, "")


def extract_archive(file_bytes: bytes, file_name: str) -> list[ExtractedFile]:
    extracted: list[ExtractedFile] = []
    ext = Path(file_name).suffix.lower()

    if ext == ".zip":
        extracted = _extract_zip(file_bytes, file_name)
    elif ext == ".rar":
        extracted = _extract_rar(file_bytes, file_name)
    elif ext == ".7z":
        extracted = _extract_7z(file_bytes, file_name)
    else:
        logger.warning("Unsupported archive format: %s", file_name)

    return extracted


def _extract_zip(file_bytes: bytes, archive_name: str) -> list[ExtractedFile]:
    results: list[ExtractedFile] = []
    try:
        with zipfile.ZipFile(BytesIO(file_bytes)) as zf:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                file_type = _detect_file_type(info.filename)
                if not file_type:
                    continue
                try:
                    data = zf.read(info.filename)
                    if data:
                        clean_name = Path(info.filename).name
                        results.append(
                            ExtractedFile(
                                relative_path=info.filename,
                                file_name=clean_name,
                                file_bytes=data,
                                file_type=file_type,
                            )
                        )
                except Exception:
                    logger.warning("Failed to read %s from zip", info.filename, exc_info=True)
    except Exception:
        logger.warning("Failed to extract zip: %s", archive_name, exc_info=True)
    return results


def _extract_rar(file_bytes: bytes, archive_name: str) -> list[ExtractedFile]:
    results: list[ExtractedFile] = []
    try:
        import rarfile

        tmp_dir = tempfile.mkdtemp()
        tmp_archive = os.path.join(tmp_dir, archive_name)
        with open(tmp_archive, "wb") as f:
            f.write(file_bytes)
        try:
            with rarfile.RarFile(tmp_archive) as rf:
                for info in rf.infolist():
                    if info.is_dir():
                        continue
                    file_type = _detect_file_type(info.filename)
                    if not file_type:
                        continue
                    try:
                        data = rf.read(info.filename)
                        if data:
                            clean_name = Path(info.filename).name
                            results.append(
                                ExtractedFile(
                                    relative_path=info.filename,
                                    file_name=clean_name,
                                    file_bytes=data,
                                    file_type=file_type,
                                )
                            )
                    except Exception:
                        logger.warning("Failed to read %s from rar", info.filename, exc_info=True)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
    except ImportError:
        logger.warning("rarfile not installed, cannot extract RAR: %s", archive_name)
    except Exception:
        logger.warning("Failed to extract rar: %s", archive_name, exc_info=True)
    return results


def _extract_7z(file_bytes: bytes, archive_name: str) -> list[ExtractedFile]:
    results: list[ExtractedFile] = []
    try:
        import py7zr

        tmp_dir = tempfile.mkdtemp()
        tmp_archive = os.path.join(tmp_dir, archive_name)
        with open(tmp_archive, "wb") as f:
            f.write(file_bytes)
        try:
            with py7zr.SevenZipFile(tmp_archive, mode="r") as sz:
                for name, bio in sz.readall().items():
                    file_type = _detect_file_type(name)
                    if not file_type:
                        continue
                    try:
                        data = bio.read()
                        if data:
                            clean_name = Path(name).name
                            results.append(
                                ExtractedFile(
                                    relative_path=name,
                                    file_name=clean_name,
                                    file_bytes=data,
                                    file_type=file_type,
                                )
                            )
                    except Exception:
                        logger.warning("Failed to read %s from 7z", name, exc_info=True)
        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
    except ImportError:
        logger.warning("py7zr not installed, cannot extract 7z: %s", archive_name)
    except Exception:
        logger.warning("Failed to extract 7z: %s", archive_name, exc_info=True)
    return results
