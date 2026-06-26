from doc_process_studio.common.infrastructure.config import resolve_env_file_path, resolve_runtime_env


def test_resolve_runtime_env_defaults_to_dev(monkeypatch) -> None:
    monkeypatch.delenv("ENV", raising=False)

    assert resolve_runtime_env() == "dev"


def test_resolve_env_file_path_uses_requested_env_name() -> None:
    assert resolve_env_file_path("prod").name == ".env.prod"
