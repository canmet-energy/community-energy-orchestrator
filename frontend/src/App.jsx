import { useState, useEffect } from 'react';
import {
    fetchCommunities,
    createRun,
    getRunStatus,
    getAnalysisMarkdown,
    getCommunityTotalDownloadUrl,
    getDwellingTimeseriesDownloadUrl,
} from './api';

function App() {
    // View state
    const [view, setView] = useState('search'); // 'search' | 'run' | 'results'

    // Communities data
    const [communities, setCommunities] = useState([]);
    const [loadingCommunities, setLoadingCommunities] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedCommunity, setSelectedCommunity] = useState('');
    const [showSuggestions, setShowSuggestions] = useState(false);

    // Run tracking
    const [currentRunId, setCurrentRunId] = useState(null);
    const [runStatus, setRunStatus] = useState(null);
    const [startTime, setStartTime] = useState(null);
    const [elapsedTime, setElapsedTime] = useState(0);

    // Results
    const [analysisMarkdown, setAnalysisMarkdown] = useState('');

    // Error handling
    const [error, setError] = useState(null);
    

    // Load communities when app starts
    useEffect(() => {
        async function loadCommunities() {
            try {
                setLoadingCommunities(true);
                const data = await fetchCommunities();
                setCommunities(data);
            } catch (err) {
                setError(err.message);
            } finally {
                setLoadingCommunities(false);
            }
        }
        loadCommunities();
    }, []);

    // Start run when entering run view
    useEffect(() => {
        if (view === 'run' && selectedCommunity && !currentRunId) {
            async function startRun() {
                try {
                    const run = await createRun(selectedCommunity);
                    setCurrentRunId(run.run_id);
                    setRunStatus(run.status);
                    setStartTime(Date.now());
                } catch (err) {
                    // Handle 409 Conflict specifically
                    if (err.status === 409) {
                        setError('Another analysis is already running. Please wait for it to complete and try again.');
                    } else {
                        setError(`Failed to start analysis: ${err.message}`);
                    }
                    setView('error');
                }
            }
            startRun();
        }
    }, [view, selectedCommunity, currentRunId]);

    // Poll for run status when running
    useEffect(() => {
        if (view === 'run' && currentRunId) {
            const interval = setInterval(async () => {
                try {
                    const status = await getRunStatus(currentRunId);
                    setRunStatus(status.status);

                    if (status.status === 'completed') {
                        // Load results
                        const analysis = await getAnalysisMarkdown(currentRunId);
                        setAnalysisMarkdown(analysis.markdown);
                        setView('results');
                    } else if (status.status === 'failed') {
                        setError(status.error || 'Analysis failed. Please try again.');
                        setView('error');
                    }
                } catch (err) {
                    // Network or API error during polling
                    setError(`Lost connection to server: ${err.message}. The analysis may still be running.`);
                    setView('error');
                }
            }, 3000); // Poll every 3 seconds

            return () => clearInterval(interval);
        }
    }, [view, currentRunId]);

    // Update elapsed time
    useEffect(() => {
        if (view === 'run' && startTime) {
            const interval = setInterval(() => {
                setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
            }, 1000); // Update every second

            return () => clearInterval(interval);
        }
    }, [view, startTime]);

    // Handler: Select a community from dropdown
    function handleSelectCommunity(communityName) {
        setSelectedCommunity(communityName);
        setSearchTerm(communityName);
        setShowSuggestions(false); // Hide dropdown after selection
    }

    // Handler: Start the analysis
    async function handleStartAnalysis() {
        if (!selectedCommunity) {
            setError('Please select a community');
            return;
        }

        setError(null);
        setCurrentRunId(null); // Reset run ID
        setRunStatus(null);
        setStartTime(null);
        setElapsedTime(0);
        setView('run');
    }

    // Handler: Retry the same analysis
    function handleRetry() {
        setError(null);
        setCurrentRunId(null);
        setRunStatus(null);
        setStartTime(null);
        setElapsedTime(0);
        setView('run');
    }

    // Format seconds as MM:SS
    function formatTime(seconds) {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    }

    // Handler: Start a new analysis
    function handleNewAnalysis() {
        setView('search');
        setSelectedCommunity('');
        setSearchTerm('');
        setShowSuggestions(false);
        setCurrentRunId(null);
        setRunStatus(null);
        setStartTime(null);
        setElapsedTime(0);
        setAnalysisMarkdown('');
        setError(null);
    }

    // Filter communities based on search term
    const filteredCommunities = searchTerm.length > 0
        ? communities
            .filter(c => c.name.toLowerCase().includes(searchTerm.toLowerCase()))
            .slice(0, 10) // Show max 10 suggestions
        : [];

    // SEARCH VIEW
    if (view === 'search') {
        return (
            <div className="app">
                <header>
                    <h1>Community Energy Orchestrator</h1>
                    <p>Analyze energy use for remote Canadian communities</p>
                </header>

                <main>
                    {error && (
                        <div className="error">
                            {error}
                        </div>
                    )}

                    <div className="search-box">
                        <label htmlFor="community-search">
                            Select a Community:
                        </label>
                        <input
                            id="community-search"
                            type="text"
                            value={searchTerm}
                            onChange={(e) => {
                                setSearchTerm(e.target.value);
                                setShowSuggestions(true); // Show dropdown when typing
                            }}
                            onFocus={() => searchTerm.length > 0 && setShowSuggestions(true)}
                            placeholder={loadingCommunities ? "Loading communities..." : "Start typing a community name..."}
                            autoComplete="off"
                            disabled={loadingCommunities}
                        />

                        {loadingCommunities && (
                            <p className="loading-text">Loading {communities.length || '...'} communities...</p>
                        )}

                        {!loadingCommunities && showSuggestions && filteredCommunities.length > 0 && (
                            <ul className="suggestions">
                                {filteredCommunities.map((community) => (
                                    <li
                                        key={community.name}
                                        onClick={() => handleSelectCommunity(community.name)}
                                    >
                                        <strong>{community.name}</strong>
                                        <span className="meta">
                                            {community.province_territory}
                                            {community.population && ` • Pop: ${community.population.toLocaleString()}`}
                                            {community.total_houses && ` • Houses: ${community.total_houses}`}
                                            {community.hdd && ` • HDD: ${community.hdd.toLocaleString()}`}
                                        </span>
                                    </li>
                                ))}
                            </ul>
                        )}
                    </div>

                    <button
                        onClick={handleStartAnalysis}
                        disabled={!selectedCommunity || loadingCommunities}
                        className="btn-primary"
                    >
                        Start Analysis
                    </button>

                    {selectedCommunity && (
                        <p className="selected-info">
                            Selected: <strong>{selectedCommunity}</strong>
                        </p>
                    )}

                    <div className="info-box">
                        <p><strong>Note:</strong> Analysis typically takes 3-15 minutes depending on community size.</p>
                    </div>
                </main>
            </div>
        );
    }

    // RUN VIEW
    if (view === 'run') {
        return (
            <div className="app">
                <header>
                    <h1>Community Energy Orchestrator</h1>
                </header>

                <main className="running-view">
                    <div className="spinner"></div>

                    <h2>Running Analysis for {selectedCommunity}</h2>

                    <p className="status">
                        Status: <strong>{runStatus || 'Initializing...'}</strong>
                    </p>

                    <p className="elapsed">
                        Elapsed Time: <strong>{formatTime(elapsedTime)}</strong>
                    </p>

                    <div className="info-box">
                        <p>This may take 3-15 minutes depending on community size.</p>
                        {currentRunId && (
                            <p className="run-id">
                                Run ID: <code>{currentRunId}</code>
                            </p>
                        )}
                    </div>
                </main>
            </div>
        );
    }

    // RESULTS VIEW
    if (view === 'results') {
        return (
            <div className="app">
                <header>
                    <h1>Community Energy Orchestrator</h1>
                </header>

                <main className="results-view">
                    <h2>Analysis Complete: {selectedCommunity}</h2>

                    <div className="actions">
                        <a
                            href={getCommunityTotalDownloadUrl(currentRunId)}
                            download
                            className="btn-download"
                        >
                            Download Community Total CSV
                        </a>
                        <a
                            href={getDwellingTimeseriesDownloadUrl(currentRunId)}
                            download
                            className="btn-download"
                        >
                            Download Dwelling Timeseries ZIP
                        </a>
                    </div>

                    <div className="analysis-content">
                        <h3>Analysis Report</h3>
                        <pre className="markdown-preview">{analysisMarkdown}</pre>
                    </div>

                    <button onClick={handleNewAnalysis} className="btn-primary">
                        Analyze Another Community
                    </button>
                </main>
            </div>
        );
    }

    // ===== ERROR VIEW =====
    if (view === 'error') {
        return (
            <div className="app">
                <header>
                    <h1>Community Energy Orchestrator</h1>
                </header>

                <main className="error-view">
                    <h2>Analysis Failed</h2>
                    <h3>{selectedCommunity}</h3>

                    <div className="error error-large">
                        {error || 'An unknown error occurred'}
                    </div>

                    <div className="error-actions">
                        <button onClick={handleRetry} className="btn-primary">
                            Retry Analysis
                        </button>
                        <button onClick={handleNewAnalysis} className="btn-secondary">
                            Choose Different Community
                        </button>
                    </div>

                    {currentRunId && (
                        <div className="info-box">
                            <p className="run-id">
                                Run ID: <code>{currentRunId}</code>
                            </p>
                            <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
                                You can check the backend logs for more details about this error.
                            </p>
                        </div>
                    )}
                </main>
            </div>
        );
    }

    return null;
}

export default App;
