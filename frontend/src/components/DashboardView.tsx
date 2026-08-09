import React, { useState, useEffect } from 'react';
import { Match, CreateMatchInput, ResumeSession } from '../types';
import { MatchForm } from './MatchForm';
import { UploadZone } from './UploadZone';
import { MatchesList } from './MatchesList';
import {
    createMatch,
    uploadVideoMultipart,
    getStoredResumeSession,
    abortUpload,
    runUploadQueue,
    deleteMatch
} from '../services/api';
import { PlusCircle, List, RefreshCw, LogOut } from 'lucide-react';

interface DashboardViewProps {
    matches: Match[];
    onRefreshMatches: () => void;
    onSelectMatch: (matchId: string) => void;
    onDeleteMatch: (matchId: string) => void;
    onLogout?: () => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
    matches,
    onRefreshMatches,
    onSelectMatch,
    onDeleteMatch,
    onLogout
}) => {
    const [formData, setFormData] = useState<CreateMatchInput>({
        name: '',
        player1: '',
        player2: ''
    });
    const [selectedFile, setSelectedFile] = useState<File | null>(null);
    const [resumeSession, setResumeSession] = useState<ResumeSession | null>(null);

    // Upload progress state
    const [uploading, setUploading] = useState(false);
    const [progressPercent, setProgressPercent] = useState(0);
    const [uploadedMB, setUploadedMB] = useState(0);
    const [totalMB, setTotalMB] = useState(0);
    const [statusText, setStatusText] = useState('');

    useEffect(() => {
        const stored = getStoredResumeSession();
        if (stored) {
            setResumeSession(stored);
            setFormData({
                name: stored.matchName,
                player1: stored.player1,
                player2: stored.player2
            });
        }
    }, []);

    const handleFormChange = (field: keyof CreateMatchInput, value: string) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const isResumeValid =
        resumeSession !== null &&
        selectedFile !== null &&
        selectedFile.name === resumeSession.originalFilename &&
        selectedFile.size === resumeSession.fileSize;

    const isNewMatchValid =
        formData.name.trim() !== '' &&
        formData.player1.trim() !== '' &&
        formData.player2.trim() !== '' &&
        selectedFile !== null;

    const isFormValid = resumeSession ? isResumeValid : isNewMatchValid;

    const handleDiscardResume = async () => {
        if (!resumeSession) return;
        if (!window.confirm(`Discard upload session for "${resumeSession.matchName}"? This will clean up partially uploaded chunks.`)) {
            return;
        }

        await abortUpload(resumeSession.matchId, resumeSession.uploadId, resumeSession.originalFilename);
        await deleteMatch(resumeSession.matchId).catch(() => {});

        setResumeSession(null);
        setFormData({ name: '', player1: '', player2: '' });
        setSelectedFile(null);
        onRefreshMatches();
    };

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedFile || !isFormValid || uploading) return;

        setUploading(true);

        try {
            if (resumeSession) {
                // Resume existing session
                await runUploadQueue(
                    resumeSession.matchId,
                    selectedFile,
                    resumeSession.uploadId,
                    resumeSession.parts,
                    resumeSession.originalFilename,
                    (percent, upMB, totMB, text) => {
                        setProgressPercent(percent);
                        setUploadedMB(upMB);
                        setTotalMB(totMB);
                        setStatusText(text);
                    }
                );
                setResumeSession(null);
            } else {
                // Create new match and start upload
                const match = await createMatch({
                    name: formData.name.trim(),
                    player1: formData.player1.trim(),
                    player2: formData.player2.trim()
                });

                await uploadVideoMultipart(
                    match.id,
                    selectedFile,
                    formData.name.trim(),
                    formData.player1.trim(),
                    formData.player2.trim(),
                    (percent, upMB, totMB, text) => {
                        setProgressPercent(percent);
                        setUploadedMB(upMB);
                        setTotalMB(totMB);
                        setStatusText(text);
                    }
                );
            }

            // Reset form upon completion
            setFormData({ name: '', player1: '', player2: '' });
            setSelectedFile(null);
            setProgressPercent(0);
            setStatusText('');
            onRefreshMatches();
        } catch (error: any) {
            alert(error.message || 'An error occurred during video upload.');
            const currentSession = getStoredResumeSession();
            if (currentSession) {
                setResumeSession(currentSession);
            }
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="dashboard-view">
            <header className="header header-flex">
                <div>
                    <h1>Matches Dashboard</h1>
                    <p className="subtitle">Upload and score table tennis match videos with automated highlight generation</p>
                </div>
                {onLogout && (
                    <button
                        type="button"
                        onClick={onLogout}
                        className="signout-btn"
                        title="Sign Out of Beta Session"
                    >
                        <LogOut size={15} />
                        <span>Sign Out</span>
                    </button>
                )}
            </header>

            <section className={`card form-card ${resumeSession ? 'card-resume' : ''}`}>
                <div className="card-header">
                    {resumeSession ? <RefreshCw size={20} className="resume-icon" /> : <PlusCircle size={20} />}
                    <h2>{resumeSession ? 'Resume Pending Match Upload' : 'Create New Match'}</h2>
                </div>

                <form onSubmit={handleSubmit}>
                    <fieldset disabled={Boolean(resumeSession) || uploading} className="form-fieldset">
                        <MatchForm formData={formData} onChange={handleFormChange} />
                    </fieldset>

                    <UploadZone
                        selectedFile={selectedFile}
                        onFileSelect={setSelectedFile}
                        uploading={uploading}
                        progressPercent={progressPercent}
                        uploadedMB={uploadedMB}
                        totalMB={totalMB}
                        statusText={statusText}
                        resumeSession={resumeSession}
                        onDiscardResume={handleDiscardResume}
                    />

                    <button
                        type="submit"
                        className="submit-btn"
                        disabled={!isFormValid || uploading}
                    >
                        {uploading
                            ? 'Uploading Video...'
                            : resumeSession
                            ? 'Resume Match Upload'
                            : 'Create Match'}
                    </button>
                </form>
            </section>

            <section className="matches-section">
                <div className="section-header">
                    <List size={20} />
                    <h2>Uploaded Matches ({matches.length})</h2>
                </div>
                <MatchesList
                    matches={matches}
                    onSelectMatch={onSelectMatch}
                    onDeleteMatch={onDeleteMatch}
                />
            </section>
        </div>
    );
};
