import { useState, useEffect, useCallback } from 'react';
import { Match } from './types';
import { fetchMatches, fetchMatch, deleteMatch } from './services/api';
import { DashboardView } from './components/DashboardView';
import { WorkspaceView } from './components/WorkspaceView';
import './index.css';

export function App() {
    const [matches, setMatches] = useState<Match[]>([]);
    const [currentMatch, setCurrentMatch] = useState<Match | null>(null);
    const [loading, setLoading] = useState(true);

    const loadMatchesList = useCallback(async () => {
        try {
            const data = await fetchMatches();
            setMatches(data);
        } catch (err) {
            console.error('Failed to load matches:', err);
        } finally {
            setLoading(false);
        }
    }, []);

    useEffect(() => {
        loadMatchesList();
    }, [loadMatchesList]);

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
        className: "loading-screen";
        return (
            <div className="loading-screen">
                <div className="spinner" />
                <p>Loading Table Tennis Editor...</p>
            </div>
        );
    }

    return (
        <div className={`app-container ${currentMatch ? 'workspace-active' : ''}`}>
            {currentMatch ? (
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
