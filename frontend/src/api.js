const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

export async function fetchCommunities() {
    const response = await fetch(`${API_BASE_URL}/communities`);

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to fetch communities: ${response.statusText}`);
    }

    return response.json();
}

export async function createRun(communityName) {
    const response = await fetch(`${API_BASE_URL}/runs`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ community_name: communityName }),
    });

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        const errorMessage = errorData.detail || `Failed to create run: ${response.statusText}`;
        
        // Add status code for specific handling
        const error = new Error(errorMessage);
        error.status = response.status;
        throw error;
    }

    return response.json();
}

export async function getRunStatus(runId) {
    const response = await fetch(`${API_BASE_URL}/runs/${runId}`);

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to fetch run status: ${response.statusText}`);
    }

    return response.json();
}

export async function getAnalysisMarkdown(runId) {
    const response = await fetch(`${API_BASE_URL}/runs/${runId}/analysis-md`);

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to fetch analysis markdown: ${response.statusText}`);
    }

    return response.json();
}

export async function getAnalysisData(runId) {
    const response = await fetch(`${API_BASE_URL}/runs/${runId}/analysis-data`);

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to fetch analysis data: ${response.statusText}`);
    }

    const result = await response.json();
    // Parse the JSON string from the data field
    return {
        ...result,
        data: JSON.parse(result.data)
    };
}

export async function getDailyLoadData(runId) {
    const response = await fetch(`${API_BASE_URL}/runs/${runId}/daily-load-data`);

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to fetch daily load data: ${response.statusText}`);
    }

    const result = await response.json();
    // Parse the JSON string from the data field
    return {
        ...result,
        data: JSON.parse(result.data)
    };
}

export async function getPeakDayHourlyData(runId) {
    const response = await fetch(`${API_BASE_URL}/runs/${runId}/peak-day-hourly-data`);

    if (!response.ok) {
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `Failed to fetch peak day hourly data: ${response.statusText}`);
    }

    const result = await response.json();
    // Parse the JSON string from the data field
    return {
        ...result,
        data: JSON.parse(result.data)
    };
}

export function getCommunityTotalDownloadUrl(runId) {
    return `${API_BASE_URL}/runs/${runId}/download/community-total`;
}

export function getDwellingTimeseriesDownloadUrl(runId) {
    return `${API_BASE_URL}/runs/${runId}/download/dwelling-timeseries`;
}

export function getAnalysisMarkdownDownloadUrl(runId) {
    return `${API_BASE_URL}/runs/${runId}/download/analysis-md`;
}
