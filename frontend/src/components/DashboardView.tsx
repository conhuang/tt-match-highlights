import React, { useState } from 'react';
import { Match, CreateMatchInput } from '../types';
import { MatchForm } from './MatchForm';
import { UploadZone } from './UploadZone';
import { MatchesList } from './MatchesList';
import { createMatch, uploadVideoMultipart } from '../services/api';
import { PlusCircle, List } from 'lucide-react';

interface DashboardViewProps {
    matches: Match[];
    onRefreshMatches: () => void;
    onSelectMatch: (matchId: string) => void;
    onDeleteMatch: (matchId: string) => void;
}

export const DashboardView: React.FC<DashboardViewProps> = ({
    matches,
    onRefreshMatches,
    onSelectMatch,
    onDeleteMatch
}) => {
    const [formData, setFormData] = useState<CreateMatchInput>({
        name: '',
        player1: '',
        player2: ''
    });
    const [selectedFile, setSelectedFile] = useState<File | null>(null);

    // Upload state
    const [uploading, setUploading] = useState(false);
    const [progressPercent, setProgressPercent] = useState(0);
    const [uploadedMB, setUploadedMB] = useState(0);
    const [totalMB, setTotalMB] = useState(0);
    const [statusText, setStatusText] = useState('');

    const handleFormChange = (field: keyof CreateMatchInput, value: string) => {
        setFormData(prev => ({ ...prev, [field]: value }));
    };

    const isFormValid =
        formData.name.trim() !== '' &&
        formData.player1.trim() !== '' &&
        formData.player2.trim() !== '' &&
        selectedFile !== null;

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        if (!selectedFile || !isFormValid || uploading) return;

        setUploading(true);
        try {
            // 1. Create match record
            const match = await createMatch({
                name: formData.name.trim(),
                player1: formData.player1.trim(),
                player2: formData.player2.trim()
            });

            // 2. Upload video file via S3/local multipart uploader
            await uploadVideoMultipart(
                match.id,
                selectedFile,
                (percent, upMB, totMB, text) => {
                    setProgressPercent(percent);
                    setUploadedMB(upMB);
                    setTotalMB(totMB);
                    setStatusText(text);
                }
            );

            // Reset form
            setFormData({ name: '', player1: '', player2: '' });
            setSelectedFile(null);
            setProgressPercent(0);
            setStatusText('');
            onRefreshMatches();
        } catch (error: any) {
            alert(error.message || 'An error occurred during match creation.');
        } finally {
            setUploading(false);
        }
    };

    return (
        <div className="dashboard-view">
            <header className="header">
                <h1>Matches Dashboard</h1>
                <p className="subtitle">Upload and score table tennis match videos with automated highlight generation</p>
            </header>

            <section className="card form-card">
                <div className="card-header">
                    <PlusCircle size={20} />
                    <h2>Create New Match</h2>
                </div>

                <form onSubmit={handleSubmit}>
                    <MatchForm formData={formData} onChange={handleFormChange} />

                    <UploadZone
                        selectedFile={selectedFile}
                        onFileSelect={setSelectedFile}
                        uploading={uploading}
                        progressPercent={progressPercent}
                        uploadedMB={uploadedMB}
                        totalMB={totalMB}
                        statusText={statusText}
                    />

                    <button
                        type="submit"
                        className="submit-btn"
                        disabled={!isFormValid || uploading}
                    >
                        {uploading ? 'Uploading Video...' : 'Create Match'}
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
