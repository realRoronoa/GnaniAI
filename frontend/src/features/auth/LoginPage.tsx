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

        <form id="fl" noValidate onSubmit={handleSubmit} autoComplete="off">
          {/* Prevent browser / Google password autofill injection */}
          <input type="text" style={{ display: 'none' }} tabIndex={-1} aria-hidden="true" />
          <input type="password" style={{ display: 'none' }} tabIndex={-1} aria-hidden="true" />

          <label htmlFor="le">Work email</label>
          <input
            id="le"
            name="work_email_address_field"
            type="email"
            autoComplete="off"
            data-lpignore="true"
            data-form-type="other"
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
                  name="user_secret_security_code"
                  type={showPassword ? 'text' : 'password'}
                  autoComplete="new-password"
                  data-lpignore="true"
                  data-form-type="other"
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
