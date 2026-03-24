import { useState, useEffect, useRef } from 'react';
import {
    fetchCommunities,
    createRun,
    getRunStatus,
    getAnalysisData,
    getDailyLoadData,
    getPeakDayHourlyData,
    getCommunityTotalDownloadUrl,
    getDwellingTimeseriesDownloadUrl,
    getAnalysisMarkdownDownloadUrl,
} from './api';
import AnalysisVisualization from './AnalysisVisualization';
import CommunityOverview from './CommunityOverview';
import DailyEnergyChart from './DailyEnergyChart';
import PeakDayChart from './PeakDayChart';

function App() {
    // View state
    const [view, setView] = useState('search'); // 'search' | 'run' | 'results'

    // Communities data
    const [communities, setCommunities] = useState([]);
    const [loadingCommunities, setLoadingCommunities] = useState(true);
    const [searchTerm, setSearchTerm] = useState('');
    const [selectedCommunity, setSelectedCommunity] = useState('');
    const [selectedCommunityData, setSelectedCommunityData] = useState(null); // Full community object
    const [showSuggestions, setShowSuggestions] = useState(false);

    // Run tracking
    const [currentRunId, setCurrentRunId] = useState(() => {
        const saved = localStorage.getItem('currentRunId');
        return saved || null;
    });
    const [runStatus, setRunStatus] = useState(null);
    const [startTime, setStartTime] = useState(null);
    const [elapsedTime, setElapsedTime] = useState(0);

    // Run history (max 5 runs)
    const [runHistory, setRunHistory] = useState(() => {
        const saved = localStorage.getItem('runHistory');
        return saved ? JSON.parse(saved) : [];
    });
    const [activeRunId, setActiveRunId] = useState(null); // Which run is being viewed
    const [copiedRunId, setCopiedRunId] = useState(null); // Track which run ID was just copied

    // Results
    const [analysisData, setAnalysisData] = useState(null);
    const [dailyLoadData, setDailyLoadData] = useState(null);
    const [peakDayData, setPeakDayData] = useState(null);

    // Energy category tab: 'heating' or 'total'
    const [energyCategory, setEnergyCategory] = useState('total');
    const savedScrollPosition = useRef(null);

    // Error handling
    const [error, setError] = useState(null);
    
    // Dark mode
    const [darkMode, setDarkMode] = useState(() => {
        // Check localStorage first
        const saved = localStorage.getItem('darkMode');
        if (saved !== null) {
            return JSON.parse(saved);
        }
        // Otherwise, check system preference
        return window.matchMedia('(prefers-color-scheme: dark)').matches;
    });

    // Apply dark mode class to root element
    useEffect(() => {
        if (darkMode) {
            document.documentElement.classList.add('dark');
        } else {
            document.documentElement.classList.remove('dark');
        }
        localStorage.setItem('darkMode', JSON.stringify(darkMode));
    }, [darkMode]);

    // Toggle dark mode
    function toggleDarkMode() {
        setDarkMode(prev => !prev);
    }

    // Copy run ID to clipboard
    function copyRunId(runId, event) {
        event.stopPropagation(); // Prevent triggering the history item click
        navigator.clipboard.writeText(runId).then(() => {
            setCopiedRunId(runId);
            setTimeout(() => setCopiedRunId(null), 2000); // Reset after 2 seconds
        }).catch(err => {
            console.error('Failed to copy run ID:', err);
        });
    }
    
    // Save run history to localStorage whenever it changes
    useEffect(() => {
        localStorage.setItem('runHistory', JSON.stringify(runHistory));
    }, [runHistory]);

    // Save current run ID to localStorage
    useEffect(() => {
        if (currentRunId) {
            localStorage.setItem('currentRunId', currentRunId);
        } else {
            localStorage.removeItem('currentRunId');
        }
    }, [currentRunId]);

    // On mount, validate that restored currentRunId is still valid
    useEffect(() => {
        if (currentRunId) {
            // Check if this run exists in history and is still active
            const runInHistory = runHistory.find(r => r.run_id === currentRunId);
            if (runInHistory && (runInHistory.status === 'completed' || runInHistory.status === 'failed')) {
                // Run is no longer active, clear it
                setCurrentRunId(null);
            }
        }
        // eslint-disable-next-line react-hooks/exhaustive-deps
    }, []); // Run only on mount - we intentionally use initial values

    // Helper: Add or update run in history
    function addToHistory(runId, communityName, status, provinceTerritoryName = '') {
        setRunHistory(prevHistory => {
            // Remove any existing run for this community
            let newHistory = prevHistory.filter(run => run.community_name !== communityName);
            
            // Add new run at the beginning
            newHistory = [{
                run_id: runId,
                community_name: communityName,
                province_territory: provinceTerritoryName,
                status: status,
                timestamp: Date.now(),
            }, ...newHistory];
            
            // Keep only last 5 runs
            return newHistory.slice(0, 5);
        });
    }

    // Helper: Update status of a run in history
    function updateHistoryStatus(runId, status) {
        setRunHistory(prevHistory => 
            prevHistory.map(run => 
                run.run_id === runId ? { ...run, status } : run
            )
        );
    }
    

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

    // Start NEW run when entering run view (only if we don't already have a currentRunId)
    useEffect(() => {
        // Only start a new run if:
        // 1. We're in the run view
        // 2. A community is selected
        // 3. We don't have a current run ID (this prevents starting when viewing existing runs)
        // 4. activeRunId is also null (we're not viewing a historical run)
        if (view === 'run' && selectedCommunity && !currentRunId && !activeRunId) {
            async function startRun() {
                try {
                    const run = await createRun(selectedCommunity);
                    setCurrentRunId(run.run_id);
                    setRunStatus(run.status);
                    setStartTime(Date.now());
                    setActiveRunId(run.run_id); // Set as active run being viewed
                    
                    // Add to history with initial status
                    addToHistory(run.run_id, selectedCommunity, run.status, selectedCommunityData?.province_territory);
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
    }, [view, selectedCommunity, currentRunId, activeRunId, selectedCommunityData]);

    // Poll for run status when running
    // This continues polling currentRunId in the background even when viewing other runs
    useEffect(() => {
        if (currentRunId) {
            const interval = setInterval(async () => {
                try {
                    const status = await getRunStatus(currentRunId);
                    setRunStatus(status.status);
                    
                    // Update history status
                    updateHistoryStatus(currentRunId, status.status);

                    if (status.status === 'completed') {
                        // Load results if this is the active run being viewed
                        if (activeRunId === currentRunId) {
                            const data = await getAnalysisData(currentRunId);
                            setAnalysisData(data.data);
                            // Also fetch daily load data and peak day data (use 'total' to match default category)
                            try {
                                const dailyData = await getDailyLoadData(currentRunId, 'total');
                                setDailyLoadData(dailyData);
                            } catch (err) {
                                console.error('Failed to load daily load data:', err);
                            }
                            try {
                                const peakData = await getPeakDayHourlyData(currentRunId, 'total');
                                setPeakDayData(peakData);
                            } catch (err) {
                                console.error('Failed to load peak day data:', err);
                            }
                            setView('results');
                        }
                        // Clear currentRunId since run is complete
                        setCurrentRunId(null);
                    } else if (status.status === 'failed') {
                        // Only show error if this is the active run being viewed
                        if (activeRunId === currentRunId) {
                            setError(status.error || 'Analysis failed. Please try again.');
                            setView('error');
                        }
                        // Clear currentRunId since run failed
                        setCurrentRunId(null);
                    }
                } catch (err) {
                    // Network or API error during polling
                    if (activeRunId === currentRunId) {
                        setError(`Lost connection to server: ${err.message}. The analysis may still be running.`);
                        setView('error');
                    }
                }
            }, 3000); // Poll every 3 seconds

            return () => clearInterval(interval);
        }
    }, [currentRunId, activeRunId]);

    // Update elapsed time
    useEffect(() => {
        if (view === 'run' && startTime && activeRunId === currentRunId) {
            const interval = setInterval(() => {
                setElapsedTime(Math.floor((Date.now() - startTime) / 1000));
            }, 1000); // Update every second

            return () => clearInterval(interval);
        }
    }, [view, startTime, activeRunId, currentRunId]);

    // Restore scroll position after category switch (when DOM has fully updated)
    useEffect(() => {
        if (savedScrollPosition.current !== null) {
            // Wait for DOM to fully render with new category data
            requestAnimationFrame(() => {
                requestAnimationFrame(() => {
                    window.scrollTo(0, savedScrollPosition.current);
                    savedScrollPosition.current = null;
                });
            });
        }
    }, [dailyLoadData, peakDayData, energyCategory]);

    // Handler: Select a community from dropdown
    function handleSelectCommunity(communityName) {
        const communityData = communities.find(c => c.name === communityName);
        setSelectedCommunity(communityName);
        setSelectedCommunityData(communityData || null);
        setSearchTerm(communityName);
        setShowSuggestions(false); // Hide dropdown after selection
    }

    // Handler: Start the analysis
    async function handleStartAnalysis() {
        if (!selectedCommunity) {
            setError('Please select a community');
            return;
        }

        // Check if there's a background run still in progress locally
        if (currentRunId && (runStatus === 'queued' || runStatus === 'running')) {
            setError(`Cannot start new analysis: A run is still in progress. Please wait for it to complete.`);
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
    async function handleRetry() {
        // Clear all previous data immediately to prevent any flashing
        setError(null);
        setAnalysisData(null);
        setDailyLoadData(null);
        setPeakDayData(null);
        
        // Reset run tracking for fresh start
        // Don't clear selectedCommunity - we're retrying the same community
        setCurrentRunId(null);
        setRunStatus(null);
        setStartTime(null);
        setElapsedTime(0);
        setActiveRunId(null);
        
        // Ensure selectedCommunityData is set (in case it was lost)
        if (selectedCommunity && !selectedCommunityData) {
            const communityData = communities.find(c => c.name === selectedCommunity);
            setSelectedCommunityData(communityData || null);
        }
        
        // The handleStartAnalysis logic will validate if another run is active
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
        setSelectedCommunityData(null);
        setSearchTerm('');
        setShowSuggestions(false);
        
        // Only clear run data if no run is currently active
        // (completed/failed runs have already cleared currentRunId via polling)
        if (!currentRunId) {
            setRunStatus(null);
            setStartTime(null);
            setElapsedTime(0);
        }
        
        setAnalysisData(null);
        setDailyLoadData(null);
        setPeakDayData(null);
        setError(null);
        setActiveRunId(null);
        setEnergyCategory('total');
    }

    // Handler: Switch energy category (heating / total) while preserving scroll position
    async function handleCategorySwitch(runId, newCategory) {
        if (newCategory === energyCategory) return;

        // Save current scroll position
        savedScrollPosition.current = window.scrollY;

        // Fetch new data BEFORE switching category to prevent flash
        let dailyData = dailyLoadData;
        let peakData = peakDayData;
        try {
            dailyData = await getDailyLoadData(runId, newCategory);
        } catch (err) {
            console.error('Failed to load daily load data:', err);
        }
        try {
            peakData = await getPeakDayHourlyData(runId, newCategory);
        } catch (err) {
            console.error('Failed to load peak day data:', err);
        }

        // Update category and data together
        setEnergyCategory(newCategory);
        setDailyLoadData(dailyData);
        setPeakDayData(peakData);
        // Scroll restoration happens in useEffect after DOM updates
    }

    // Handler: Click on a history item to view its results
    async function handleHistoryClick(historyRun) {
        setError(null);
        setActiveRunId(historyRun.run_id);
        setSelectedCommunity(historyRun.community_name);
        // Look up and set the full community data
        const communityData = communities.find(c => c.name === historyRun.community_name);
        setSelectedCommunityData(communityData || null);

        // If the run is queued or running, show the run view
        if (historyRun.status === 'queued' || historyRun.status === 'running') {
            setAnalysisData(null);
            setDailyLoadData(null);
            setPeakDayData(null);
            // Set this as the current run to resume tracking/polling
            setCurrentRunId(historyRun.run_id);
            setRunStatus(historyRun.status);
            setEnergyCategory('total');
            // Don't set startTime - we don't know when it started after refresh
            setView('run');
        } else if (historyRun.status === 'completed') {
            // Load ALL data before switching view to prevent flash
            try {
                const data = await getAnalysisData(historyRun.run_id);
                let dailyData = null;
                let peakData = null;
                try {
                    dailyData = await getDailyLoadData(historyRun.run_id, 'total');
                } catch (err) {
                    console.error('Failed to load daily load data:', err);
                }
                try {
                    peakData = await getPeakDayHourlyData(historyRun.run_id, 'total');
                } catch (err) {
                    console.error('Failed to load peak day data:', err);
                }
                // Update all state at once after data is ready
                setEnergyCategory('total');
                setAnalysisData(data.data);
                setDailyLoadData(dailyData);
                setPeakDayData(peakData);
                setView('results');
            } catch (err) {
                // Run not found on server (e.g. server restarted) - mark as stale
                console.error('Failed to load analysis data:', err);
                updateHistoryStatus(historyRun.run_id, 'failed');
                setAnalysisData(null);
                setDailyLoadData(null);
                setPeakDayData(null);
                setError('Server lost track of this run (it may have restarted). Please re-run the analysis.');
                setView('error');
            }
        } else if (historyRun.status === 'failed') {
            setAnalysisData(null);
            setDailyLoadData(null);
            setPeakDayData(null);
            setError('This run failed. Please start a new analysis.');
            setView('error');
        }
    }

    // Filter communities based on search term
    const filteredCommunities = searchTerm.length > 0
        ? communities
            .filter(c => c.name.toLowerCase().includes(searchTerm.toLowerCase()))
            .slice(0, 10) // Show max 10 suggestions
        : [];

    // Render history sidebar
    function renderHistorySidebar() {
        if (runHistory.length === 0) {
            return null;
        }

        return (
            <aside className="history-sidebar">
                <h3>Run History</h3>
                <ul className="history-list">
                    {runHistory.map((run) => {
                        const isActive = run.run_id === activeRunId;
                        const statusClass = run.status === 'completed' ? 'completed' 
                            : run.status === 'failed' ? 'failed'
                            : run.status === 'running' ? 'running'
                            : 'queued';
                        
                        return (
                            <li
                                key={run.run_id}
                                className={`history-item ${isActive ? 'active' : ''} ${statusClass}`}
                                onClick={() => handleHistoryClick(run)}
                            >
                                <div className="history-item-header">
                                    <span className="community-name">
                                        {run.community_name}{run.province_territory && (
                                            <span className="province-badge">, {run.province_territory}</span>
                                        )}
                                    </span>
                                    <span className={`status-indicator ${statusClass}`}></span>
                                </div>
                                <div className="history-item-meta">
                                    <button 
                                        className="run-id-copy-btn"
                                        onClick={(e) => copyRunId(run.run_id, e)}
                                        title={run.run_id}
                                        aria-label="Copy run ID"
                                    >
                                        {copiedRunId === run.run_id ? (
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                                            </svg>
                                        ) : (
                                            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                                                <rect x="9" y="9" width="13" height="13" rx="2" ry="2" strokeWidth={2}></rect>
                                                <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1" strokeWidth={2}></path>
                                            </svg>
                                        )}
                                    </button>
                                    <span className="status-text">{run.status}</span>
                                </div>
                                {isActive && run.status === 'completed' && (
                                    <div className="category-tabs" onClick={(e) => e.stopPropagation()}>
                                        <button
                                            className={`category-tab ${energyCategory === 'total' ? 'active' : ''}`}
                                            onClick={() => handleCategorySwitch(run.run_id, 'total')}
                                        >
                                            Total
                                        </button>
                                        <button
                                            className={`category-tab ${energyCategory === 'heating' ? 'active' : ''}`}
                                            onClick={() => handleCategorySwitch(run.run_id, 'heating')}
                                        >
                                            Heating
                                        </button>
                                    </div>
                                )}
                            </li>
                        );
                    })}
                </ul>
                <p style={{ fontSize: '0.75rem', color: 'var(--text-secondary)', marginTop: '1rem', textAlign: 'center' }}>
                    Maximum of 5 runs shown
                </p>
            </aside>
        );
    }

    // SEARCH VIEW
    if (view === 'search') {
        return (
            <div className="app">
                <header>
                    <button onClick={toggleDarkMode} className="theme-toggle" aria-label="Toggle dark mode">
                        {darkMode ? (
                            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                            </svg>
                        ) : (
                            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                            </svg>
                        )}
                    </button>
                    <h1>Community Energy Orchestrator</h1>
                    <p>Analyze energy use for remote Canadian communities</p>
                </header>
                
                <div className="content-wrapper">
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

                        {currentRunId && (runStatus === 'queued' || runStatus === 'running') && (
                            <div className="warning-box">
                                <p><strong>⚠️ Another Run In Progress</strong></p>
                                <p>
                                    A run for &ldquo;{runHistory.find(r => r.run_id === currentRunId)?.community_name || 'a community'}&rdquo; is currently {runStatus}. 
                                    Please wait for it to complete before starting a new analysis.
                                </p>
                                <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
                                    You can view the progress in the Run History sidebar or by clicking on that run.
                                </p>
                            </div>
                        )}

                        {selectedCommunity && (
                            <p className="selected-info">
                                Selected: <strong>{selectedCommunity}</strong>
                            </p>
                        )}

                        <div className="info-box">
                            <p><strong>Note:</strong> Analysis typically takes 3-15 minutes depending on community size.</p>
                        </div>
                    </main>
                    {renderHistorySidebar()}
                </div>
            </div>
        );
    }

    // RUN VIEW
    if (view === 'run') {
        return (
            <div className="app">
                <header>
                    <button onClick={toggleDarkMode} className="theme-toggle" aria-label="Toggle dark mode">
                        {darkMode ? (
                            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                            </svg>
                        ) : (
                            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                            </svg>
                        )}
                    </button>
                    <h1>Community Energy Orchestrator</h1>
                </header>
                
                <div className="content-wrapper">
                    <main className="running-view">
                        <div className="spinner"></div>

                        <h2>Running Analysis for {selectedCommunity}</h2>

                        <p className="status">
                            Status: <strong>{runStatus || 'Initializing...'}</strong>
                        </p>

                        {activeRunId === currentRunId && (
                            <p className="elapsed">
                                Elapsed Time: <strong>{startTime ? formatTime(elapsedTime) : 'Not available (page was refreshed)'}</strong>
                            </p>
                        )}

                        <div className="info-box">
                            <p>This may take 3-15 minutes depending on community size.</p>
                            {activeRunId && (
                                <p className="run-id">
                                    Run ID: <code>{activeRunId}</code>
                                </p>
                            )}
                        </div>
                    </main>
                    {renderHistorySidebar()}
                </div>
            </div>
        );
    }

    // RESULTS VIEW
    if (view === 'results') {
        return (
            <div className="app">
                <header>
                    <button onClick={toggleDarkMode} className="theme-toggle" aria-label="Toggle dark mode">
                        {darkMode ? (
                            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                            </svg>
                        ) : (
                            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                            </svg>
                        )}
                    </button>
                    <h1>Community Energy Orchestrator</h1>
                </header>
                
                <div className="content-wrapper">
                    <main className="results-view">
                        <h2>Analysis Complete: {selectedCommunity}</h2>

                        <div className="actions">
                            <a
                                href={getCommunityTotalDownloadUrl(activeRunId)}
                                download
                                className="btn-download"
                            >
                                Download Community Total CSV
                            </a>
                            <a
                                href={getDwellingTimeseriesDownloadUrl(activeRunId)}
                                download
                                className="btn-download"
                            >
                                Download Dwelling Timeseries ZIP
                            </a>
                        </div>

                        <button onClick={handleNewAnalysis} className="btn-primary">
                            Analyze Another Community
                        </button>

                        {/* Community Overview */}
                        {analysisData?.community_info && (
                            <CommunityOverview communityInfo={analysisData.community_info} />
                        )}

                        {/* Visualizations */}
                        {analysisData && (
                            <AnalysisVisualization analysisData={analysisData} category={energyCategory} />
                        )}

                        {/* Daily Energy Chart */}
                        {dailyLoadData && analysisData && (
                            <DailyEnergyChart dailyLoadData={dailyLoadData} analysisData={analysisData} category={energyCategory} />
                        )}

                        {/* Peak Day Hourly Chart */}
                        {peakDayData && (
                            <PeakDayChart peakDayData={peakDayData} category={energyCategory} />
                        )}

                        <div className="bottom-download">
                            <a
                                href={getAnalysisMarkdownDownloadUrl(activeRunId)}
                                download
                                className="btn-download"
                            >
                                Download Analysis Report (Markdown)
                            </a>
                        </div>

                        <button onClick={handleNewAnalysis} className="btn-primary">
                            Analyze Another Community
                        </button>
                    </main>
                    {renderHistorySidebar()}
                </div>
            </div>
        );
    }

    // ===== ERROR VIEW =====
    if (view === 'error') {
        return (
            <div className="app">
                <header>
                    <button onClick={toggleDarkMode} className="theme-toggle" aria-label="Toggle dark mode">
                        {darkMode ? (
                            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
                            </svg>
                        ) : (
                            <svg fill="none" viewBox="0 0 24 24" stroke="currentColor">
                                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
                            </svg>
                        )}
                    </button>
                    <h1>Community Energy Orchestrator</h1>
                </header>
                
                <div className="content-wrapper">
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

                        {activeRunId && (
                            <div className="info-box">
                                <p className="run-id">
                                    Run ID: <code>{activeRunId}</code>
                                </p>
                                <p style={{ fontSize: '0.875rem', marginTop: '0.5rem' }}>
                                    You can check the backend logs for more details about this error.
                                </p>
                            </div>
                        )}
                    </main>
                    {renderHistorySidebar()}
                </div>
            </div>
        );
    }

    return null;
}

export default App;
