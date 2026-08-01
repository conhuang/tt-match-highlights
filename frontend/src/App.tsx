import { useState, useEffect, useCallback } from 'react';
import { Match } from './types';
import { fetchMatches, fetchMatch, deleteMatch, verifyAuthToken } from './services/api';
import { DashboardView } from './components/DashboardView';
import { WorkspaceView } from './components/WorkspaceView';
import { GoogleLoginModal } from './components/GoogleLoginModal';
import './index.css';

export function App() {
    const [matches, setMatches] = useState<Match[]>([]);
    const [currentMatch, setCurrentMatch] = useState<Match | null>(null);
    const [loading, setLoading] = useState(true);
    const [needsAuth, setNeedsAuth] = useState(false);
    const [authError, setAuthError] = useState<string | null>(null);

    const navigateTo = (path: string) => {
        if (window.location.pathname !== path) {
            window.history.pushState({}, '', path);
        }
    };

    const handleLogout = () => {
        sessionStorage.removeItem('beta_id_token');
        localStorage.removeItem('beta_id_token');
        setNeedsAuth(true);
        setCurrentMatch(null);
        setMatches([]);
        navigateTo('/login');
    };

    const syncRouteFromPath = useCallback(async () => {
        const path = window.location.pathname;

        if (needsAuth) {
            if (path !== '/login') navigateTo('/login');
            return;
        }

        if (path.startsWith('/matches/')) {
            const matchId = path.split('/matches/')[1];
            if (matchId) {
                try {
                    const match = await fetchMatch(matchId);
                    setCurrentMatch(match);
                    setNeedsAuth(false);
                    return;
                } catch (err: any) {
                    console.error('Failed to load deep-linked match:', err);
                    if (err.message && (err.message.includes('Authentication required') || err.message.includes('Access Denied'))) {
                        setNeedsAuth(true);
                        navigateTo('/login');
                        return;
                    }
                }
            }
        }

        if (path === '/login') {
            if (!needsAuth) {
                navigateTo('/matches');
            }
        } else if (path === '/' || path === '/matches') {
            setCurrentMatch(null);
            if (path !== '/matches') navigateTo('/matches');
        }
    }, [needsAuth]);

    const loadMatchesList = useCallback(async () => {
        try {
            const data = await fetchMatches();
            setMatches(data);
            setNeedsAuth(false);
            setAuthError(null);
            
            const path = window.location.pathname;
            if (path === '/' || path === '/login') {
                navigateTo('/matches');
            } else if (path.startsWith('/matches/')) {
                const matchId = path.split('/matches/')[1];
                if (matchId) {
                    const match = data.find(m => m.id === matchId);
                    if (match) setCurrentMatch(match);
                }
            }
        } catch (err: any) {
            console.error('Failed to load matches:', err);
            setNeedsAuth(true);
            navigateTo('/login');
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadMatchesList();
    }, [loadMatchesList]);

    useEffect(() => {
        const handlePopState = () => {
            syncRouteFromPath();
        };
        window.addEventListener('popstate', handlePopState);
        return () => window.removeEventListener('popstate', handlePopState);
    }, [syncRouteFromPath]);

    const handleLoginSuccess = async (idToken: string) => {
        try {
            sessionStorage.setItem('beta_id_token', idToken);
            localStorage.setItem('beta_id_token', idToken);
            setAuthError(null);
            await verifyAuthToken(idToken);
            setNeedsAuth(false);
            navigateTo('/matches');
            await loadMatchesList();
        } catch (err: any) {
            setAuthError(err.message || 'Access Denied: Your email is not authorized for this Beta.');
        }
    };

    const handleSelectMatch = async (matchId: string) => {
        try {
            const match = await fetchMatch(matchId);
            if (!match.video_filename) {
                alert('This match does not have an uploaded video yet. Please complete the video upload first.');
                return;
            }
            setCurrentMatch(match);
            navigateTo(`/matches/${matchId}`);
        } catch (err: any) {
            alert(err.message || 'Error entering match workspace.');
        }
    };

    const handleDeleteMatch = async (matchId: string) => {
        if (!window.confirm('Are you sure you want to delete this match and its video files?')) {
            return;
        }

        try {
            await deleteMatch(matchId);
            if (currentMatch?.id === matchId) {
                setCurrentMatch(null);
                navigateTo('/matches');
            }
            await loadMatchesList();
        } catch (err: any) {
            alert(err.message || 'Could not delete match.');
        }
    };

    const handleMatchUpdated = (updatedMatch: Match) => {
        setCurrentMatch(updatedMatch);
        setMatches(prev => prev.map(m => m.id === updatedMatch.id ? updatedMatch : m));
    };

    if (loading) {
        return (
            <div className="loading-screen">
                <div className="spinner" />
                <p>Loading Table Tennis Editor...</p>
            </div>
        );
    }

    return (
        <div className={`app-container ${currentMatch ? 'workspace-active' : ''}`}>
            {needsAuth ? (
                <GoogleLoginModal
                    onLoginSuccess={handleLoginSuccess}
                    errorMessage={authError}
                />
            ) : currentMatch ? (
                <WorkspaceView
                    currentMatch={currentMatch}
                    onBack={() => {
                        setCurrentMatch(null);
                        navigateTo('/matches');
                        loadMatchesList();
                    }}
                    onMatchUpdated={handleMatchUpdated}
                    onLogout={handleLogout}
                />
            ) : (
                <DashboardView
                    matches={matches}
                    onRefreshMatches={loadMatchesList}
                    onSelectMatch={handleSelectMatch}
                    onDeleteMatch={handleDeleteMatch}
                    onLogout={handleLogout}
                />
            )}
        </div>
    );
}

export default App;
