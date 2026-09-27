import pytest
from pulse109.config import Settings
from pulse109_worker.main import _validate_adapter_mode


@pytest.mark.parametrize("environment", ["pilot", "production"])
def test_replay_delivery_cannot_start_operational_profile(environment: str) -> None:
    settings = Settings(_env_file=None, environment=environment)
    with pytest.raises(RuntimeError, match="forbidden"):
        _validate_adapter_mode(settings, "replay", True)


def test_demo_worker_requires_explicit_replay_mode() -> None:
    settings = Settings(_env_file=None, profile="demo")
    with pytest.raises(RuntimeError, match="explicit replay"):
        _validate_adapter_mode(settings, "unavailable", True)
    _validate_adapter_mode(settings, "replay", True)
