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
        <div className="modal-backdrop">
            <div className="modal-content auth-modal-card">
                <div className="auth-modal-icon-badge">
                    <Lock size={28} />
                </div>

                <h2 className="auth-modal-title">
                    Beta Tester Sign In
                </h2>

                <p className="auth-modal-subtitle">
                    Access to this Table Tennis Video Editor release is currently restricted to authorized Beta Testers.
                </p>

                {activeError && (
                    <div className="auth-modal-error">
                        <ShieldAlert size={20} className="icon-btn-base" />
                        <span>{activeError}</span>
                    </div>
                )}

                {clientId ? (
                    <div className="auth-modal-btn-wrap">
                        <div id="google-signin-button-container" />
                    </div>
                ) : (
                    <div className="auth-modal-warning">
                        <LogIn size={16} style={{ marginBottom: '4px' }} />
                        <div><strong>Note:</strong> Set <code>VITE_GOOGLE_CLIENT_ID</code> in environment to enable One-Click Google Login.</div>
                    </div>
                )}

                <div className="auth-modal-footer-text">
                    Need access? Contact the administrator to whitelist your Google email address.
                </div>
            </div>
        </div>
    );
};
