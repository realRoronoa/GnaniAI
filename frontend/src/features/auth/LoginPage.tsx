import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { useAuth } from '@/features/auth/AuthContext';
import { getRoleHomeRoute } from '@/routes/ProtectedRoute';
import api, { getErrorMessage } from '@/services/api';

const CLINIC_TEAM_IMG =
  'https://images.pexels.com/photos/6129507/pexels-photo-6129507.jpeg?auto=compress&cs=tinysrgb&w=1400';

export const LoginPage: React.FC = () => {
  const { login } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isForgot, setIsForgot] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [note, setNote] = useState<{ text: string; type?: 'good' | 'bad' } | null>(null);
  const [emailErr, setEmailErr] = useState('');
  const [passErr, setPassErr] = useState('');

  const from = (location.state as any)?.from?.pathname;

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setNote(null);
    setEmailErr('');
    setPassErr('');

    const emailTrimmed = email.trim();
    if (!/^\S+@\S+\.\S+$/.test(emailTrimmed)) {
      setEmailErr('Enter a valid email address.');
      return;
    }
    if (!isForgot && !password) {
      setPassErr('Enter your password.');
      return;
    }

    setIsLoading(true);

    try {
      if (isForgot) {
        await api.post('/auth/password/forgot', { email: emailTrimmed });
        setNote({
          text: 'If this email is registered, a reset link has been sent.',
          type: 'good',
        });
      } else {
        const response = await api.post('/auth/login', {
          email: emailTrimmed,
          password,
        });

        const { access_token, refresh_token, token_type = 'bearer', user } = response.data;
        login({ access_token, refresh_token, token_type }, user);
        navigate(from || getRoleHomeRoute(user.role), { replace: true });
      }
    } catch (err: any) {
      setNote({
        text: getErrorMessage(err) || 'Email or password is incorrect.',
        type: 'bad',
      });
    } finally {
      setIsLoading(false);
    }
  };

  const handleQuickDemoLogin = async (demoEmail: string, demoPass: string) => {
    setEmail(demoEmail);
    setPassword(demoPass);
    setNote(null);
    setEmailErr('');
    setPassErr('');
    setIsLoading(true);

    try {
      const response = await api.post('/auth/login', {
        email: demoEmail,
        password: demoPass,
      });
      const { access_token, refresh_token, token_type = 'bearer', user } = response.data;
      login({ access_token, refresh_token, token_type }, user);
      navigate(from || getRoleHomeRoute(user.role), { replace: true });
    } catch (err: any) {
      setNote({
        text: getErrorMessage(err) || 'Instant demo login failed.',
        type: 'bad',
      });
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <div className="view" style={{ position: 'relative', minHeight: '100vh', display: 'grid' }}>
      <div className="vside">
        <img src={CLINIC_TEAM_IMG} alt="" />
        <div className="cap">
          <span className="logo" style={{ color: '#F4EDE0' }}>
            Arogya<b>Scribe</b>
          </span>
          <p>The doctor talks. The doctor decides.</p>
        </div>
      </div>

      <div className="vform">
        <Link to="/" className="back" style={{ display: 'inline-block', textDecoration: 'none' }}>
          &larr; Back to website
        </Link>
        <h2 id="lt">{isForgot ? 'Reset password' : 'Sign in'}</h2>
        <p className="lead">
          One sign-in for all staff. Your role is set by your organization.
        </p>

        {/* 1-Click Operational Demo Accounts Bar (Super Admin excluded for security) */}
        {((import.meta as any).env?.VITE_ENABLE_DEMO_BAR !== 'false') && (
          <div
            style={{
              background: 'var(--surface)',
              border: '1.5px solid var(--line)',
              borderRadius: '12px',
              padding: '12px',
              margin: '18px 0',
            }}
          >
            <div
              style={{
                fontSize: '0.72rem',
                fontWeight: 700,
                textTransform: 'uppercase',
                letterSpacing: '0.1em',
                color: 'var(--text-2)',
                marginBottom: '8px',
                display: 'flex',
                justifyContent: 'space-between',
              }}
            >
              <span>1-Click Clinic Staff Demo:</span>
              <span style={{ color: 'var(--accent-2)' }}>Seeded</span>
            </div>
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '8px' }}>
              <button
                type="button"
                disabled={isLoading}
                onClick={() => handleQuickDemoLogin('orgadmin@arogyacare.in', 'OrgAdmin@123')}
                style={{
                  padding: '8px 10px',
                  borderRadius: '8px',
                  border: '1px solid var(--line)',
                  background: 'var(--surface-2)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: '0.8rem',
                }}
              >
                <b>Org Admin</b>
                <br />
                <small style={{ color: 'var(--text-2)' }}>Clinic Owner</small>
              </button>
              <button
                type="button"
                disabled={isLoading}
                onClick={() => handleQuickDemoLogin('reception@arogyacare.in', 'Reception@123')}
                style={{
                  padding: '8px 10px',
                  borderRadius: '8px',
                  border: '1px solid var(--line)',
                  background: 'var(--surface-2)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: '0.8rem',
                }}
              >
                <b>Receptionist</b>
                <br />
                <small style={{ color: 'var(--text-2)' }}>Front Desk</small>
              </button>
              <button
                type="button"
                disabled={isLoading}
                onClick={() => handleQuickDemoLogin('dr.sharma@arogyacare.in', 'Doctor@123')}
                style={{
                  padding: '8px 10px',
                  borderRadius: '8px',
                  border: '1px solid var(--line)',
                  background: 'var(--surface-2)',
                  cursor: 'pointer',
                  textAlign: 'left',
                  fontSize: '0.8rem',
                }}
              >
                <b>Doctor</b>
                <br />
                <small style={{ color: 'var(--text-2)' }}>Dr. Sharma</small>
              </button>
            </div>
            <div style={{ fontSize: '0.68rem', color: 'var(--text-2)', marginTop: '8px', textAlign: 'center' }}>
              Platform Super Admin logs in via private credentials (never auto-filled).
            </div>
          </div>
        )}

        <form id="fl" noValidate onSubmit={handleSubmit}>
          <label htmlFor="le">Work email</label>
          <input
            id="le"
            type="email"
            autoComplete="username"
            required
            value={email}
            onChange={(e) => setEmail(e.target.value)}
          />
          <div className="err" id="lee">
            {emailErr}
          </div>

          {!isForgot && (
            <div id="lpw">
              <label htmlFor="lp">Password</label>
              <div className="pw">
                <input
                  id="lp"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="current-password"
                  required
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                />
                <button
                  type="button"
                  className="eye"
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  onClick={() => setShowPassword(!showPassword)}
                >
                  {showPassword ? 'Hide' : 'Show'}
                </button>
              </div>
              <div className="err" id="lpe">
                {passErr}
              </div>
            </div>
          )}

          {note && (
            <div
              className={`note ${note.type === 'good' ? 'good' : note.type === 'bad' ? 'bad' : ''}`}
              role="alert"
            >
              {note.text}
            </div>
          )}

          <button
            className="btn p"
            id="lb"
            type="submit"
            disabled={isLoading}
            style={{ width: '100%', marginTop: '10px' }}
          >
            {isLoading ? 'Please wait…' : isForgot ? 'Send reset link' : 'Sign in'}
          </button>

          <p style={{ marginTop: '14px' }}>
            <a
              href="#"
              id="fg"
              onClick={(e) => {
                e.preventDefault();
                setIsForgot(!isForgot);
                setNote(null);
              }}
            >
              {isForgot ? 'Back to sign in' : 'Forgot password?'}
            </a>
          </p>
        </form>

        <p className="ev" style={{ marginTop: '18px' }}>
          New organization? <Link to="/">Get started</Link>. There is no patient login.
        </p>
      </div>
    </div>
  );
};
