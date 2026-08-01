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

    const loadMatchesList = useCallback(async () => {
        try {
            const data = await fetchMatches();
            setMatches(data);
            setNeedsAuth(false);
            setAuthError(null);
        } catch (err: any) {
            console.error('Failed to load matches:', err);
            if (err.message && (err.message.includes('Authentication required') || err.message.includes('Access Denied') || err.message.includes('fetch matches'))) {
                setNeedsAuth(true);
            }
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadMatchesList();
    }, [loadMatchesList]);

    const handleLoginSuccess = async (idToken: string) => {
        try {
            sessionStorage.setItem('beta_id_token', idToken);
            localStorage.setItem('beta_id_token', idToken);
            setAuthError(null);
            await verifyAuthToken(idToken);
            setNeedsAuth(false);
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
                        loadMatchesList();
                    }}
                    onMatchUpdated={handleMatchUpdated}
                />
            ) : (
                <DashboardView
                    matches={matches}
                    onRefreshMatches={loadMatchesList}
                    onSelectMatch={handleSelectMatch}
                    onDeleteMatch={handleDeleteMatch}
                />
            )}
        </div>
    );
}

export default App;
