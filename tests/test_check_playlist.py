"""Tests for playlist validation startup errors (missing/unsupported files)."""

import pytest

from pyradio.validate_playlist import check_playlist


def test_check_playlist_missing_csv_exits_cleanly(capsys):
    """A missing .csv playlist must produce a clean error, not a traceback."""
    with pytest.raises(SystemExit) as exc_info:
        check_playlist("does-not-exist.csv", no_color=True, verbose=False)
    assert exc_info.value.code == 1
    out, _ = capsys.readouterr()
    assert 'Cannot open "does-not-exist.csv" for reading.' in out
    assert "Traceback" not in out


def test_check_playlist_unsupported_file_type_exits_cleanly(capsys):
    """A non-playlist file must produce a clean error, not a traceback."""
    with pytest.raises(SystemExit) as exc_info:
        check_playlist("stations.txt", no_color=True, verbose=False)
    assert exc_info.value.code == 1
    out, _ = capsys.readouterr()
    assert "Unsupported file type" in out
    assert "Traceback" not in out
