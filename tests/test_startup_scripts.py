from pathlib import Path
import os
import subprocess

import pytest


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


@pytest.mark.skipif(os.name != 'posix', reason='Exercises the POSIX launcher and executable shell fixtures')
@pytest.mark.parametrize('installer_exit', [0, 42])
def test_posix_update_propagates_missing_environment_install_failure(tmp_path, installer_exit):
    """Run the real update script with local git/installer process fixtures."""
    (tmp_path / 'update.sh').write_text((ROOT / 'update.sh').read_text())
    installer = tmp_path / 'install.sh'
    installer.write_text(f'#!/bin/sh\nexit {installer_exit}\n')
    installer.chmod(0o755)
    fake_bin = tmp_path / 'bin'
    fake_bin.mkdir()
    git = fake_bin / 'git'
    git.write_text('#!/bin/sh\nexit 0\n')
    git.chmod(0o755)

    result = subprocess.run(
        ['bash', 'update.sh'], cwd=tmp_path, capture_output=True, text=True,
        env={**os.environ, 'PATH': f"{fake_bin}{os.pathsep}{os.environ['PATH']}"},
        check=False,
    )

    assert (result.returncode == 0) == (installer_exit == 0)
    assert ('Update Complete!' in result.stdout) == (installer_exit == 0)
    if installer_exit:
        assert 'Installation failed' in result.stdout


def test_windows_update_checks_missing_environment_install_status():
    """Windows execution is unavailable here; guard the specific failure branch."""
    script = (ROOT / 'update.bat').read_text()
    missing_environment_branch = script.split('if not exist venv (', 1)[1].split(') else (', 1)[0]
    assert 'call install.bat\n    if errorlevel 1 (' in missing_environment_branch
    assert 'exit /b 1' in missing_environment_branch
