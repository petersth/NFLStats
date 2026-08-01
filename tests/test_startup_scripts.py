from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_launchers_do_not_destroy_work_or_global_credentials():
    scripts = (ROOT / "start.sh").read_text(), (ROOT / "start.bat").read_text()

    for script in scripts:
        assert "reset --hard" not in script
        assert "credentials.toml" not in script
        assert "HEAD..origin/main" in script


def test_setup_and_updates_are_explicit_and_fail_fast():
    setup_scripts = (ROOT / "setup.sh").read_text(), (ROOT / "setup.bat").read_text()
    update_scripts = (ROOT / "update.sh").read_text(), (ROOT / "update.bat").read_text()

    assert all("reset --hard" not in script for script in setup_scripts)
    assert all("pull --ff-only" in script for script in update_scripts)
    assert "exit 1" in update_scripts[0]
    assert "exit /b 1" in update_scripts[1]


def test_launchers_preserve_and_rebuild_incompatible_virtual_environments():
    posix_scripts = tuple(
        (ROOT / name).read_text()
        for name in ("install.sh", "start.sh", "update.sh")
    )
    windows_scripts = tuple(
        (ROOT / name).read_text()
        for name in ("install.bat", "start.bat", "update.bat")
    )

    assert all("sys.version_info >= (3, 12)" in script for script in posix_scripts)
    assert all("sys.version_info >= (3, 12)" in script for script in windows_scripts)
    assert "venv.incompatible." in posix_scripts[0]
    assert "venv.incompatible." in windows_scripts[0]
