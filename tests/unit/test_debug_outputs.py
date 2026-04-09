"""Unit tests for debug and validation functions."""

import pytest

pytestmark = pytest.mark.unit


# Note: Location code validation tests were removed as of March 2026.
# The weather location change process was simplified to only modify
# Region/English and Location/English fields (the only fields h2k-hpxml uses).
# Location codes are no longer validated or modified.
#
# If you need to test debug_timeseries_outputs, see integration tests.

