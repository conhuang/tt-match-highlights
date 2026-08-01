import React, { useEffect, useState } from 'react';
import { Lock, ShieldAlert, LogIn } from 'lucide-react';

interface GoogleLoginModalProps {
    onLoginSuccess: (idToken: string, userProfile: any) => void;
    errorMessage?: string | null;
}

declare global {
    interface Window {
        google?: any;
    }
}

export const GoogleLoginModal: React.FC<GoogleLoginModalProps> = ({ onLoginSuccess, errorMessage }) => {
    const [scriptLoaded, setScriptLoaded] = useState(false);
    const [localError, setLocalError] = useState<string | null>(null);
    const [fetchedClientId, setFetchedClientId] = useState<string>('');

    const initialClientId = import.meta.env.VITE_GOOGLE_CLIENT_ID || (window as any).GOOGLE_CLIENT_ID || '';
    const clientId = initialClientId || fetchedClientId;

    useEffect(() => {
        // Fetch runtime Google Client ID from backend if not already set statically
        if (!initialClientId) {
            fetch('/api/auth/config')
                .then((res) => res.json())
                .then((data) => {
                    if (data?.google_client_id) {
                        setFetchedClientId(data.google_client_id);
                    }
                })
                .catch((err) => console.warn('Could not fetch auth config:', err));
        }

        // Dynamically load Google Identity Services SDK script
        const existingScript = document.getElementById('google-gsi-script');
        if (!existingScript) {
            const script = document.createElement('script');
            script.src = 'https://accounts.google.com/gsi/client';
            script.id = 'google-gsi-script';
            script.async = true;
            script.defer = true;
            script.onload = () => setScriptLoaded(true);
            document.body.appendChild(script);
        } else {
            setScriptLoaded(true);
        }
    }, [initialClientId]);

    useEffect(() => {
        if (scriptLoaded && window.google?.accounts?.id && clientId) {
            window.google.accounts.id.initialize({
                client_id: clientId,
                callback: (response: any) => {
                    if (response.credential) {
                        onLoginSuccess(response.credential, null);
                    } else {
                        setLocalError('Google authentication failed. Please try again.');
                    }
                }
            });

            const btnContainer = document.getElementById('google-signin-button-container');
            if (btnContainer) {
                btnContainer.innerHTML = '';
                window.google.accounts.id.renderButton(btnContainer, {
                    theme: 'filled_black',
                    size: 'large',
                    shape: 'pill',
                    text: 'signin_with',
                    width: 280
                });
            }
        }
    }, [scriptLoaded, clientId, onLoginSuccess]);

    const activeError = errorMessage || localError;

    return (
        <div className="modal-overlay" style={{ background: 'rgba(10, 15, 29, 0.92)', backdropFilter: 'blur(10px)', zIndex: 9999 }}>
            <div className="modal-content" style={{ maxWidth: '440px', padding: '2.5rem 2rem', textAlign: 'center', borderRadius: '16px', border: '1px solid rgba(255, 255, 255, 0.12)' }}>
                <div style={{ width: '56px', height: '56px', margin: '0 auto 1.25rem', background: 'rgba(99, 102, 241, 0.15)', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6366f1' }}>
                    <Lock size={28} />
                </div>

                <h2 style={{ fontSize: '1.5rem', fontWeight: 700, margin: '0 0 0.5rem', color: '#f8fafc' }}>
                    Beta Tester Sign In
                </h2>

                <p style={{ color: '#94a3b8', fontSize: '0.9rem', lineHeight: '1.5', margin: '0 0 1.75rem' }}>
                    Access to this Table Tennis Video Editor release is currently restricted to authorized Beta Testers.
                </p>

                {activeError && (
                    <div style={{ margin: '0 0 1.5rem', padding: '0.85rem 1rem', background: 'rgba(239, 68, 68, 0.12)', border: '1px solid rgba(239, 68, 68, 0.3)', borderRadius: '10px', color: '#fca5a5', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.6rem', textAlign: 'left' }}>
                        <ShieldAlert size={20} style={{ flexShrink: 0 }} />
                        <span>{activeError}</span>
                    </div>
                )}

                {clientId ? (
                    <div style={{ display: 'flex', justifyContent: 'center', margin: '1rem 0' }}>
                        <div id="google-signin-button-container" />
                    </div>
                ) : (
                    <div style={{ padding: '1rem', background: 'rgba(245, 158, 11, 0.1)', border: '1px solid rgba(245, 158, 11, 0.3)', borderRadius: '8px', color: '#fbbf24', fontSize: '0.82rem' }}>
                        <LogIn size={16} style={{ marginBottom: '4px' }} />
                        <div><strong>Note:</strong> Set <code>VITE_GOOGLE_CLIENT_ID</code> in environment to enable One-Click Google Login.</div>
                    </div>
                )}

                <div style={{ marginTop: '2rem', fontSize: '0.78rem', color: '#64748b' }}>
                    Need access? Contact the administrator to whitelist your Google email address.
                </div>
            </div>
        </div>
    );
};
