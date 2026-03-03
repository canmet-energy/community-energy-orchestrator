"""Integration tests - API + workflow behavior with CSV verification."""

import pytest

import workflow.requirements as req

pytestmark = pytest.mark.integration


def test_create_run_with_valid_community_verifies_csv(client, sample_data):
    """Test that API workflow accepts valid community and verifies against CSV"""
    # Use Ogoki which exists in CSV with 55 houses (2001-2015-single)
    community_name = sample_data["community_name"]
    requirements = req.get_community_requirements(community_name)

    # Verify Ogoki actually has houses in the CSV
    assert requirements, f"{community_name} should exist in CSV"
    assert sum(requirements.values()) > 0, f"{community_name} should have houses"

    # Create a run
    response = client.post("/runs", json={"community_name": community_name})
    # Accept 200 (queued), 201 (created), or 409 (another run active)
    assert response.status_code in [200, 201, 409]


def test_create_run_with_nonexistent_community(client):
    """Test that API workflow handles non-existent community gracefully"""
    # Verify this community doesn't exist in CSV
    fake_community = "NonExistentCommunity999"
    requirements = req.get_community_requirements(fake_community)
    assert not requirements, "Test community should not exist in CSV"

    # API should accept request but workflow will handle gracefully
    response = client.post("/runs", json={"community_name": fake_community})
    assert response.status_code in [200, 201, 409]


def test_get_analysis_for_nonexistent_run(client):
    """Test that getting analysis for invalid run returns 404"""
    response = client.get("/runs/invalid-uuid-12345/analysis-md")
    assert response.status_code == 404
