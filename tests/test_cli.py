import subprocess
import sys

from retail_configuration_lab.cli import main


def test_baseline_command_exits_successfully_and_labels_verdicts(capsys):
    assert main(["baseline"]) == 0
    output = capsys.readouterr().out
    assert "Original modeled verdict: BUY / CONFIGURE" in output
    assert "Current lab verdict: UNTESTED" in output
    assert "Custom first-year buyer surplus: -$25,486.20" in output


def test_module_help_exits_successfully():
    result = subprocess.run(
        [sys.executable, "-m", "retail_configuration_lab", "--help"],
        check=False, capture_output=True, text=True,
    )
    assert result.returncode == 0
    assert "baseline" in result.stdout
