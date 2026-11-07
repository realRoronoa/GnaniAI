import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '@/features/auth/AuthContext';
import { getRoleHomeRoute } from '@/routes/ProtectedRoute';
import api, { getErrorMessage } from '@/services/api';
import { SubscriptionPlan } from '@/types';

// Pexels fallback images matching index.html
const IMGS = {
  heroDoctor: 'https://images.pexels.com/photos/4266934/pexels-photo-4266934.jpeg?auto=compress&cs=tinysrgb&w=1400',
  consultationPatient: 'https://images.pexels.com/photos/5327864/pexels-photo-5327864.jpeg?auto=compress&cs=tinysrgb&w=800',
  doctorTechnology: 'https://images.pexels.com/photos/5407243/pexels-photo-5407243.jpeg?auto=compress&cs=tinysrgb&w=800',
  receptionAppointment: 'https://images.pexels.com/photos/6809657/pexels-photo-6809657.jpeg?auto=compress&cs=tinysrgb&w=1400',
  doctorProfile: 'https://images.pexels.com/photos/32428850/pexels-photo-32428850.jpeg?auto=compress&cs=tinysrgb&w=1400',
  receptionist: 'https://images.pexels.com/photos/4269203/pexels-photo-4269203.jpeg?auto=compress&cs=tinysrgb&w=1400',
  clinicTeam: 'https://images.pexels.com/photos/6129507/pexels-photo-6129507.jpeg?auto=compress&cs=tinysrgb&w=1400',
};

const STEPS_DATA = [
  'A patient walks in. Staff will use the clinic\'s existing flow.',
  'Reception searches for the patient or adds a new record, books the visit and assigns a doctor.',
  'The doctor opens the record, confirms consent, and starts recording.',
  'AI prepares a transcript and two report drafts. All are marked as drafts.',
  'The doctor reviews facts, edits both reports and approves them.',
  'An approved PDF is stored in the record. Authorized staff download it and share it by WhatsApp or email by hand.',
];

const DEFAULT_PLANS: SubscriptionPlan[] = [
  {
    id: 'starter',
    code: 'STARTER',
    name: 'Starter',
    description: 'For independent clinics.',
    monthly_price: 4999,
    annual_price: 49990,
    max_doctors: 2,
    max_receptionists: 1,
    max_branches: 1,
    monthly_consultation_limit: 250,
    audio_storage_mb_limit: 25600,
    included_features_json: [
      'Up to 2 doctors',
      '1 receptionist',
      '250 consultations/month',
      '25 GB private storage',
      'Reception queue and appointments',
      'Consent-first recording',
      'Doctor report and patient summary PDFs',
    ],
    is_active: true,
  },
  {
    id: 'professional',
    code: 'PROFESSIONAL',
    name: 'Professional',
    description: 'For growing clinics.',
    monthly_price: 14999,
    annual_price: 149990,
    max_doctors: 10,
    max_receptionists: 4,
    max_branches: 3,
    monthly_consultation_limit: 1000,
    audio_storage_mb_limit: 102400,
    included_features_json: [
      'Up to 10 doctors',
      '4 receptionists',
      '1,000 consultations/month',
      '100 GB private storage',
      'Multiple clinic locations',
      'Hindi patient summaries',
      'Staff and appointment management',
      'Extended audit history',
    ],
    is_active: true,
  },
  {
    id: 'enterprise',
    code: 'ENTERPRISE',
    name: 'Enterprise',
    description: 'For hospitals and medical centres.',
    monthly_price: 49999,
    annual_price: 499990,
    max_doctors: 25,
    max_receptionists: 10,
    max_branches: 10,
    monthly_consultation_limit: 3000,
    audio_storage_mb_limit: 512000,
    included_features_json: [
      'Up to 25 doctors',
      '10 receptionists',
      '3,000 consultations/month',
      '500 GB private storage',
      'Multiple branches',
      'Advanced audit logs',
      'Priority support',
      'Centralized organization management',
    ],
    is_active: true,
  },
];

export const LandingPage: React.FC = () => {
  const navigate = useNavigate();
  const { login } = useAuth();

  // Navigation mobile menu
  const [menuOpen, setMenuOpen] = useState(false);

  // Modal Views
  const [activeView, setActiveView] = useState<'login' | 'register' | null>(null);

  // Before / After Slider
  const [sliderVal, setSliderVal] = useState(50);

  // 5 Tabs State
  const [activeTab, setActiveTab] = useState(0);
  const [factVerified, setFactVerified] = useState(false);
  const [demoApproved, setDemoApproved] = useState(false);

  // 6 Steps State
  const [currentStep, setCurrentStep] = useState(0);

  // Pricing State
  const [billing, setBilling] = useState<'monthly' | 'annual'>('monthly');
  const [chosenPlan, setChosenPlan] = useState('professional');
  const [plans, setPlans] = useState<SubscriptionPlan[]>(DEFAULT_PLANS);

  useEffect(() => {
    let isMounted = true;
    api
      .get('/plans/public')
      .then((res) => {
        if (isMounted && Array.isArray(res.data) && res.data.length > 0) {
          setPlans(res.data);
        }
      })
      .catch(() => {});
    return () => {
      isMounted = false;
    };
  }, []);

  // Sign In Form State
  const [loginEmail, setLoginEmail] = useState('');
  const [loginPassword, setLoginPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [isForgot, setIsForgot] = useState(false);
  const [loginLoading, setLoginLoading] = useState(false);
  const [loginNote, setLoginNote] = useState<{ text: string; type?: 'good' | 'bad' } | null>(null);
  const [loginEmailErr, setLoginEmailErr] = useState('');
  const [loginPassErr, setLoginPassErr] = useState('');

  // Register Form State
  const [regOrg, setRegOrg] = useState('');
  const [regType, setRegType] = useState('Clinic');
  const [regCity, setRegCity] = useState('');
  const [regName, setRegName] = useState('');
  const [regEmail, setRegEmail] = useState('');
  const [regPassword, setRegPassword] = useState('');
  const [regConfirmPassword, setRegConfirmPassword] = useState('');
  const [regPlan, setRegPlan] = useState('professional');
  const [regBilling, setRegBilling] = useState<'monthly' | 'annual'>('monthly');
  const [regTerms, setRegTerms] = useState(false);
  const [regLoading, setRegLoading] = useState(false);
  const [regError, setRegError] = useState('');
  const [regNote, setRegNote] = useState<{ text: string; type?: 'good' | 'bad' } | null>(null);

  // Promotional Coupon State
  const [regCoupon, setRegCoupon] = useState('');
  const [couponValidation, setCouponValidation] = useState<{
    valid: boolean;
    message: string;
    final_monthly?: number;
    final_annual?: number;
  } | null>(null);
  const [isValidatingCoupon, setIsValidatingCoupon] = useState(false);

  const handleValidateCoupon = async () => {
    if (!regCoupon.trim()) {
      setCouponValidation(null);
      return;
    }
    setIsValidatingCoupon(true);
    try {
      const res = await api.post('/plans/validate-coupon', {
        coupon_code: regCoupon.trim().toUpperCase(),
        plan_code: regPlan.toUpperCase(),
      });
      setCouponValidation({
        valid: res.data.valid,
        message: res.data.message,
        final_monthly: Number(res.data.final_price_monthly),
        final_annual: Number(res.data.final_price_annual),
      });
    } catch (err) {
      setCouponValidation({
        valid: false,
        message: 'Could not validate promo code.',
      });
    } finally {
      setIsValidatingCoupon(false);
    }
  };

  // Intersection observer for .rv elements
  useEffect(() => {
    const observer = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add('in');
            observer.unobserve(e.target);
          }
        });
      },
      { threshold: 0.12 }
    );
    document.querySelectorAll('.rv').forEach((el) => observer.observe(el));
    return () => observer.disconnect();
  }, []);

  // Escape key handler for views
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        setActiveView(null);
        document.body.style.overflow = '';
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  const openView = (view: 'login' | 'register', planId?: string) => {
    if (planId) {
      setChosenPlan(planId);
      setRegPlan(planId);
    }
    setMenuOpen(false);
    setActiveView(view);
    document.body.style.overflow = 'hidden';
  };

  const closeViews = () => {
    setActiveView(null);
    document.body.style.overflow = '';
  };

  // Sign in submit handler
  const handleLoginSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoginNote(null);
    setLoginEmailErr('');
    setLoginPassErr('');

    const emailTrimmed = loginEmail.trim();
    if (!/^\S+@\S+\.\S+$/.test(emailTrimmed)) {
      setLoginEmailErr('Enter a valid email address.');
      return;
    }
    if (!isForgot && !loginPassword) {
      setLoginPassErr('Enter your password.');
      return;
    }

    setLoginLoading(true);

    try {
      if (isForgot) {
        await api.post('/auth/password/forgot', { email: emailTrimmed });
        setLoginNote({ text: 'If this email is registered, a reset link has been sent.', type: 'good' });
      } else {
        const response = await api.post('/auth/login', {
          email: emailTrimmed,
          password: loginPassword,
        });

        const { access_token, refresh_token, token_type = 'bearer', user } = response.data;
        login({ access_token, refresh_token, token_type }, user);
        document.body.style.overflow = '';
        navigate(getRoleHomeRoute(user.role), { replace: true });
      }
    } catch (err: any) {
      setLoginNote({
        text: getErrorMessage(err) || 'Email or password is incorrect.',
        type: 'bad',
      });
    } finally {
      setLoginLoading(false);
    }
  };

  // 1-Click Instant Demo Login
  const instantDemoLogin = async (email: string, pass: string) => {
    setLoginEmail(email);
    setLoginPassword(pass);
    setLoginNote(null);
    setLoginEmailErr('');
    setLoginPassErr('');
    setLoginLoading(true);

    try {
      const response = await api.post('/auth/login', {
        email: email,
        password: pass,
      });

      const { access_token, refresh_token, token_type = 'bearer', user } = response.data;
      login({ access_token, refresh_token, token_type }, user);
      document.body.style.overflow = '';
      navigate(getRoleHomeRoute(user.role), { replace: true });
    } catch (err: any) {
      setLoginNote({
        text: getErrorMessage(err) || 'Instant demo login failed.',
        type: 'bad',
      });
    } finally {
      setLoginLoading(false);
    }
  };

  // Register submit handler
  const handleRegisterSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setRegError('');
    setRegNote(null);

    if (!regOrg.trim() || !regCity.trim() || !regName.trim()) {
      setRegError('Fill in organization, city and your name.');
      return;
    }
    if (!/^\S+@\S+\.\S+$/.test(regEmail.trim())) {
      setRegError('Enter a valid work email.');
      return;
    }
    if (regPassword.length < 8) {
      setRegError('Password must be at least 8 characters.');
      return;
    }
    if (regPassword !== regConfirmPassword) {
      setRegError('Passwords do not match.');
      return;
    }
    if (!regTerms) {
      setRegError('Please accept the terms to continue.');
      return;
    }

    setRegLoading(true);

    try {
      await api.post('/organizations/register', {
        name: regOrg,
        org_type: regType === 'Independent practice' ? 'CLINIC' : regType.toUpperCase(),
        contact_email: regEmail,
        contact_phone: 'N/A',
        address: regCity,
        admin_full_name: regName,
        requested_plan: regPlan.toUpperCase(),
        requested_billing_cycle: regBilling.toUpperCase(),
        coupon_code: regCoupon.trim().toUpperCase() || undefined,
      });

      setRegNote({
        text: 'Your request has been received! Our Platform Owner team has been notified via email and dashboard, and will connect with you shortly to activate your Organization Admin account.',
        type: 'good',
      });
      // Clear sensitive form fields
      setRegPassword('');
      setRegConfirmPassword('');
    } catch (err) {
      setRegNote({
        text: getErrorMessage(err) || 'We could not submit this. Please check your details.',
        type: 'bad',
      });
    } finally {
      setRegLoading(false);
    }
  };

  return (
    <div>
      {/* Rough SVG Filter for Approved Stamp */}
      <svg width="0" height="0" style={{ position: 'absolute' }} aria-hidden="true">
        <filter id="rough">
          <feTurbulence baseFrequency="0.85" numOctaves="2" result="n" />
          <feDisplacementMap in="SourceGraphic" in2="n" scale="2.4" />
        </filter>
      </svg>

      {/* Navigation */}
      <nav aria-label="Main" className="main-nav">
        <a className="logo" href="#top">
          Arogya<b>Scribe</b>
        </a>
        <button
          className="burger"
          aria-label="Open menu"
          aria-expanded={menuOpen}
          onClick={() => setMenuOpen(!menuOpen)}
        >
          &#9776;
        </button>
        <ul className={menuOpen ? 'open' : ''}>
          <li>
            <a href="#approach" onClick={() => setMenuOpen(false)}>
              Features
            </a>
          </li>
          <li>
            <a href="#how" onClick={() => setMenuOpen(false)}>
              How it works
            </a>
          </li>
          <li>
            <a href="#pricing" onClick={() => setMenuOpen(false)}>
              Pricing
            </a>
          </li>
          <li>
            <a href="#trust" onClick={() => setMenuOpen(false)}>
              About
            </a>
          </li>
          <li>
            <a
              href="#"
              onClick={(e) => {
                e.preventDefault();
                openView('login');
              }}
            >
              Sign in
            </a>
          </li>
          <li>
            <a
              className="btn p"
              href="#"
              onClick={(e) => {
                e.preventDefault();
                openView('register');
              }}
            >
              Get started
            </a>
          </li>
        </ul>
      </nav>

      {/* Hero Section */}
      <section className="hero wrap" id="top" style={{ maxWidth: 'none' }}>
        <div>
          <p className="eyebrow">AI-assisted clinical documentation</p>
          <h1>
            The doctor talks. <em>The doctor <span className="uw">decides.<svg className="ul" viewBox="0 0 300 14" preserveAspectRatio="none" aria-hidden="true"><path d="M3 9c40-8 90-8 140-4s100 4 154-2"/></svg></span></em>
          </h1>
          <p className="lead">
            ArogyaScribe turns a consultation into a draft report. Every word is checked and approved by the doctor before it becomes a record.
          </p>
          <div className="acts">
            <a
              className="btn p"
              href="#"
              onClick={(e) => {
                e.preventDefault();
                openView('register');
              }}
            >
              Request an onboarding talk
            </a>
            <a className="btn" href="#approach">
              See the product
            </a>
          </div>
        </div>

        <div className="stagew">
          <div className="hand" aria-hidden="true">
            you check every word
            <svg viewBox="0 0 60 50">
              <path d="M8 4c20 2 38 12 40 38M40 34l8 9 7-11" />
            </svg>
          </div>
          <div
            className="stage"
            role="img"
            aria-label="Photograph of an Indian doctor in a consultation room"
          >
            <img src={IMGS.heroDoctor} alt="Indian doctor in a consultation room" />
          </div>
          <div className="float ui">
            <div className="row">
              <b>
                Rohan Verma <small>(sample patient)</small>
              </b>
              <span className="pill rec">
                <span className="dot" />
                Recording · 04:12
              </span>
            </div>
            <div className="wave" aria-hidden="true">
              {Array.from({ length: 40 }).map((_, i) => (
                <i
                  key={i}
                  style={{
                    animationDelay: `${((i * 0.07) % 1.1).toFixed(2)}s`,
                    animationDuration: `${(0.8 + (i % 5) * 0.15).toFixed(2)}s`,
                  }}
                />
              ))}
            </div>
            <span className="pill ok">Patient consent noted</span>
          </div>
        </div>
      </section>

      {/* The Problem Section */}
      <section className="alt rv" id="problem">
        <div className="wrap">
          <p className="eyebrow">The problem</p>
          <h2>
            After every visit, <em>the second job begins.</em>
          </h2>
          <p className="lead">
            Notes, summaries and medicine instructions take time that doctors would rather spend with patients.
          </p>

          <div className="ba" id="ba">
            {/* Left side: Manual */}
            <div className="side manual">
              <div className="pane">
                <span className="chip">Manual notes · after clinic hours</span>
                <div className="pol">
                  <img alt="Doctor with a patient" src={IMGS.consultationPatient} loading="lazy" />
                </div>
                <div className="stack">
                  <i />
                  <i />
                  <i>
                    <svg viewBox="0 0 170 190" fill="none" stroke="#172820" strokeWidth="2" strokeLinecap="round">
                      <path d="M18 40c20-10 30 8 50-2s30 6 60-2M18 70c25-8 35 10 60 0s40 8 70-2M18 100c18-6 40 8 55-1M18 130c30-10 50 8 75 0" />
                      <path d="M30 160l110-20" stroke="#8a3b2e" />
                    </svg>
                  </i>
                </div>
                <div className="sticky-note">Still writing up notes…</div>
              </div>
            </div>

            {/* Right side: ArogyaScribe */}
            <div
              className="side auto"
              id="baR"
              style={{ clipPath: `inset(0 0 0 ${sliderVal}%)` }}
            >
              <div className="pane">
                <span className="chip">With ArogyaScribe</span>
                <div className="pol">
                  <img alt="Doctor using a computer" src={IMGS.doctorTechnology} loading="lazy" />
                </div>
                <div className="docs">
                  <div className="mdoc">
                    <b>Clinical report</b>
                    <s />
                    <s />
                    <s />
                    <span className="pill ai">AI draft</span>
                  </div>
                  <div className="mdoc">
                    <b className="hi">मरीज़ सारांश</b>
                    <s />
                    <s />
                    <s />
                    <span className="pill ai">AI draft</span>
                  </div>
                </div>
                <div className="wave" aria-hidden="true" style={{ width: '100%' }}>
                  {Array.from({ length: 40 }).map((_, i) => (
                    <i
                      key={i}
                      style={{
                        animationDelay: `${((i * 0.07) % 1.1).toFixed(2)}s`,
                        animationDuration: `${(0.8 + (i % 5) * 0.15).toFixed(2)}s`,
                      }}
                    />
                  ))}
                </div>
                <span className="pill ok">Doctor reviews and approves</span>
              </div>
            </div>

            {/* Split Handle */}
            <div className="hd" id="hd" style={{ left: `${sliderVal}%` }}>
              <span>&#8596;</span>
            </div>

            <input
              className="bar"
              id="rg"
              type="range"
              min="5"
              max="95"
              value={sliderVal}
              onChange={(e) => setSliderVal(Number(e.target.value))}
              aria-label="Drag to compare manual notes with ArogyaScribe"
            />
            <span className="hint">Drag to compare</span>
          </div>
        </div>
      </section>

      {/* The Product Section */}
      <section className="dark rv" id="approach">
        <div className="wrap">
          <p className="eyebrow">The product</p>
          <h2>
            From voice to approved report, <em>one clear path.</em>
          </h2>

          <div className="photos">
            <figure>
              <img alt="Doctor talking with a patient" src={IMGS.consultationPatient} loading="lazy" />
            </figure>
            <figure>
              <img alt="Doctor using a computer during work" src={IMGS.doctorTechnology} loading="lazy" />
            </figure>
            <figure>
              <img alt="Reception staff helping with an appointment" src={IMGS.receptionAppointment} loading="lazy" />
            </figure>
          </div>

          <div className="tabs" role="tablist">
            {['1 Record', '2 Transcript', '3 Verify', '4 Two reports', '5 Approve'].map((label, idx) => (
              <button
                key={idx}
                className="tab"
                role="tab"
                aria-selected={activeTab === idx}
                onClick={() => setActiveTab(idx)}
              >
                {label}
              </button>
            ))}
          </div>

          {/* Panel 1 */}
          <div className={`panel ${activeTab === 0 ? 'on' : ''}`}>
            <div>
              <h3>Record, with consent first</h3>
              <p>The patient's consent is shown before recording starts. Sample data only.</p>
            </div>
            <div className="ui">
              <div className="row">
                <b>Sana Iyer · 34 · F</b>
                <span className="pill ok">Consent given</span>
              </div>
              <div className="wave">
                {Array.from({ length: 30 }).map((_, i) => (
                  <i key={i} />
                ))}
              </div>
              <div className="row">
                <span className="pill rec">
                  <span className="dot" />
                  Recording
                </span>
                <b>06:48</b>
              </div>
            </div>
          </div>

          {/* Panel 2 */}
          <div className={`panel ${activeTab === 1 ? 'on' : ''}`}>
            <div>
              <h3>A transcript the doctor can fix</h3>
              <p>Speaker labels and times. Every line can be edited.</p>
            </div>
            <div className="ui">
              <div className="seg">
                <small>Doctor · 00:12</small>
                <br />
                How long have you had the cough?
              </div>
              <div className="seg">
                <small>Patient · 00:18</small>
                <br />
                About ten days. <span className="hi">रात में ज़्यादा होती है।</span>
              </div>
              <div className="seg">
                <small>Doctor · 00:31</small>
                <br />
                Any fever?
              </div>
              <div className="row" style={{ marginTop: '10px' }}>
                <span className="pill">&#9654; Play audio</span>
                <span className="pill">&#9998; Edit</span>
              </div>
            </div>
          </div>

          {/* Panel 3 */}
          <div className={`panel ${activeTab === 2 ? 'on' : ''}`}>
            <div>
              <h3>Every fact shows its source</h3>
              <p>AI suggests facts from the transcript. The doctor checks each one. Medicine details always need an explicit check.</p>
            </div>
            <div className="ui">
              <div className={`fact ${factVerified ? 'v' : ''}`} id="f1">
                <div className="row">
                  <b>Cough: 10 days, worse at night</b>
                  <span className={`pill ${factVerified ? 'ok' : 'ai'}`}>
                    {factVerified ? 'Doctor verified' : 'AI draft'}
                  </span>
                </div>
                <div className="ev">
                  Evidence: <mark>"About ten days… रात में ज़्यादा"</mark> (00:18)
                </div>
              </div>
              <div className="fact">
                <div className="row">
                  <b>Medicine instruction</b>
                  <span className="pill warn">Doctor must review</span>
                </div>
                <div className="ev">Not filled by AI as final. Doctor enters or confirms.</div>
              </div>
              <button
                className="btn"
                style={{ padding: '8px 16px', marginTop: '10px' }}
                disabled={factVerified}
                onClick={() => setFactVerified(true)}
              >
                {factVerified ? 'Verified (demo)' : 'Mark first fact verified'}
              </button>
            </div>
          </div>

          {/* Panel 4 */}
          <div className={`panel ${activeTab === 3 ? 'on' : ''}`}>
            <div>
              <h3>Two reports, two readers</h3>
              <p>One for clinical use. One in simple words, in the patient's language.</p>
            </div>
            <div className="ui two">
              <div>
                <span className="pill ai">Draft</span>
                <br />
                <b>Clinical report</b>
                <br />
                Chief complaint, history, doctor's notes.
              </div>
              <div>
                <span className="pill ai">Draft · Hindi</span>
                <br />
                <b className="hi">मरीज़ के लिए सारांश</b>
                <br />
                <span className="hi">आपकी खांसी के बारे में डॉक्टर की बातें।</span>
              </div>
            </div>
          </div>

          {/* Panel 5 */}
          <div className={`panel ${activeTab === 4 ? 'on' : ''}`}>
            <div>
              <h3>Only the doctor approves</h3>
              <p>Nothing is final until the doctor says so. A PDF is made after approval and shared by staff by hand.</p>
            </div>
            <div className="ui">
              <div className="row">
                <b>Final review</b>
                <span className={`pill ${demoApproved ? 'ok' : ''}`} id="st">
                  {demoApproved ? 'Approved by doctor · v1' : 'Draft · not approved'}
                </span>
              </div>
              <p style={{ margin: '12px 0', color: 'var(--text-2)' }}>
                Reports: Clinical v1, Patient summary v1
              </p>
              <div className={`stamp ${demoApproved ? 'on' : ''}`} id="stp" aria-hidden="true">
                Approved
                <small>by doctor · demo</small>
              </div>
              <button
                className="btn p"
                id="ap"
                disabled={demoApproved}
                onClick={() => setDemoApproved(true)}
              >
                {demoApproved ? 'Approved (demo)' : 'Approve as doctor (demo)'}
              </button>
              <p className="ev" style={{ marginTop: '8px' }}>
                Demo only. Nothing is saved or sent.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* How It Works Section */}
      <section className="rv" id="how">
        <div className="wrap">
          <p className="eyebrow">How it works</p>
          <h2>
            Six steps, <em>one record.</em>
          </h2>

          <div className="steps" id="steps">
            <i id="bar" style={{ width: `${(currentStep / 5) * 90}%` }} />
            {['Patient arrives', 'Reception', 'Consent + record', 'AI drafts', 'Doctor approves', 'PDF shared'].map(
              (stepName, idx) => (
                <button
                  key={idx}
                  className={`stp ${idx < currentStep ? 'done' : ''}`}
                  aria-current={currentStep === idx}
                  onClick={() => setCurrentStep(idx)}
                >
                  <b>{idx + 1}</b>
                  {stepName}
                </button>
              )
            )}
          </div>

          <div className="stepbox" id="sb" aria-live="polite">
            <h3 style={{ fontSize: '1.2rem', marginBottom: '8px' }}>Step {currentStep + 1}</h3>
            <p>{STEPS_DATA[currentStep]}</p>
          </div>
        </div>
      </section>

      {/* Built for Staff Section */}
      <section className="alt rv" id="roles">
        <div className="wrap">
          <p className="eyebrow">Built for staff</p>
          <h2>
            Made for the people <em>in the clinic.</em>
          </h2>
          <p className="lead">Patients are records. They do not log in.</p>

          <div className="roles">
            <div className="role">
              <div className="img">
                <img src={IMGS.doctorProfile} alt="doctor at work in a clinic" loading="lazy" />
              </div>
              <div>
                <h3>Doctors</h3>
                <p>Record, review and approve. Final say stays with them.</p>
              </div>
            </div>

            <div className="role">
              <div className="img">
                <img src={IMGS.receptionist} alt="reception at work in a clinic" loading="lazy" />
              </div>
              <div>
                <h3>Receptionists</h3>
                <p>Find or add patients, book visits, assign doctors, manage the queue.</p>
              </div>
            </div>

            <div className="role">
              <div className="img">
                <img src={IMGS.clinicTeam} alt="clinic team at work in a clinic" loading="lazy" />
              </div>
              <div>
                <h3>Organization admins</h3>
                <p>Manage doctors, staff and the organization's records.</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Pricing Section */}
      <section className="alt rv" id="pricing">
        <div className="wrap">
          <p className="eyebrow">Pricing</p>
          <h2>
            Simple plans, <em>per organization.</em>
          </h2>
          <p className="lead">Starting prices. To be confirmed by the owner before launch.</p>

          <div className="bill" role="group" aria-label="Billing frequency">
            <button
              aria-pressed={billing === 'monthly'}
              onClick={() => setBilling('monthly')}
            >
              Monthly
            </button>
            <button
              aria-pressed={billing === 'annual'}
              onClick={() => setBilling('annual')}
            >
              Annual
            </button>
          </div>

          <div className="plans" id="plans">
            {plans.map((p) => {
              const isPopular = p.code === 'PROFESSIONAL';
              const monthlyNum = Number(p.monthly_price) || 0;
              const annualNum = Number(p.annual_price) || monthlyNum * 10;
              const features = p.included_features_json && p.included_features_json.length > 0
                ? p.included_features_json
                : [
                    `Up to ${p.max_doctors} doctors`,
                    `${p.max_receptionists} receptionist${p.max_receptionists > 1 ? 's' : ''}`,
                    `${p.monthly_consultation_limit || 250} consultations/month`,
                    `${Math.round((p.audio_storage_mb_limit || 1024) / 1024)} GB private storage`,
                    'Reception queue and appointments',
                    'Consent-first recording',
                    'Doctor report and patient summary PDFs',
                  ];

              return (
                <div key={p.id || p.code} className={`plan ${isPopular ? 'pop ring-2 ring-accent-2/60' : ''}`}>
                  {isPopular && (
                    <span className="pill soon" style={{ background: '#1c4d32', color: '#a3e6b5', borderColor: '#2d6a4f' }}>
                      Recommended
                    </span>
                  )}
                  <h3>{p.name}</h3>
                  <p>{p.description || (p.code === 'STARTER' ? 'For independent clinics.' : p.code === 'PROFESSIONAL' ? 'For growing clinics.' : 'For hospitals and medical centres.')}</p>
                  {billing === 'monthly' ? (
                    <div className="pr">
                      ₹{monthlyNum.toLocaleString('en-IN')}
                      <small> / month</small>
                    </div>
                  ) : (
                    <div className="pr">
                      ₹{annualNum.toLocaleString('en-IN')}
                      <small> / year</small>
                    </div>
                  )}
                  <ul>
                    {features.map((item, idx) => (
                      <li key={idx}>{item}</li>
                    ))}
                  </ul>
                  <button
                    className={`btn ${isPopular ? '' : 'p'}`}
                    onClick={() => openView('register', p.code.toLowerCase())}
                  >
                    Choose {p.name}
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* Trust and Oversight */}
      <section className="rv" id="trust">
        <div className="wrap">
          <p className="eyebrow">Trust and oversight</p>
          <h2>
            AI drafts. <em>Humans decide.</em>
          </h2>
          <div className="trust">
            <div className="ui">
              <h3>Draft or approved, always clear</h3>
              <div className="fact">
                <span className="pill ai">AI draft</span> Purple edge, not final.
              </div>
              <div className="fact v">
                <span className="pill ok">Doctor approved</span> Green edge, version saved.
              </div>
            </div>
            <div className="ui">
              <h3>Consent and access</h3>
              <p>Consent is shown before recording. Access depends on role. Each approval makes a new report version.</p>
              <p className="ev" style={{ marginTop: '10px' }}>
                We make no legal or compliance claims in this prototype.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Future Ideas Section */}
      <section className="dark rv">
        <div className="wrap">
          <p className="eyebrow">Future ideas</p>
          <h2>
            What may come <em>next.</em>
          </h2>
          <p>None of these are in the current MVP.</p>
          <div className="fut">
            <div>
              <span className="pill soon">Coming soon</span>
              <h3>Online booking</h3>
            </div>
            <div>
              <span className="pill soon">Coming soon</span>
              <h3>Appointment integration</h3>
            </div>
            <div>
              <span className="pill soon">Coming soon</span>
              <h3>WhatsApp delivery</h3>
            </div>
            <div>
              <span className="pill soon">Coming soon</span>
              <h3>Email delivery</h3>
            </div>
            <div>
              <span className="pill soon">Coming soon</span>
              <h3>Reminders</h3>
            </div>
            <div>
              <span className="pill soon">Coming soon</span>
              <h3>Advanced AI help</h3>
            </div>
            <div>
              <span className="pill soon">Coming soon</span>
              <h3>Voice summaries</h3>
            </div>
            <div>
              <span className="pill soon">Coming soon</span>
              <h3>Clinic analytics</h3>
            </div>
          </div>
        </div>
      </section>

      {/* CTA Section */}
      <section className="cta rv alt">
        <div className="wrap">
          <h2>Give doctors their time back.</h2>
          <a
            className="btn p"
            href="#"
            onClick={(e) => {
              e.preventDefault();
              openView('register');
            }}
          >
            Request an onboarding discussion
          </a>
        </div>
      </section>

      {/* Footer */}
      <footer>
        <div className="wrap">
          <div>
            <a className="logo" style={{ color: '#F4EDE0' }} href="#top">
              Arogya<b>Scribe</b>
            </a>
            <p>[Company name placeholder]</p>
            <p>[Address placeholder]</p>
          </div>
          <div>
            <a href="#approach">Product</a>
            <a href="#how">How it works</a>
            <a href="#trust">Trust</a>
          </div>
          <div>
            <a href="#">[Privacy placeholder]</a>
            <a href="#">[Contact email placeholder]</a>
          </div>
        </div>
      </footer>

      {/* Integrated Sign-in View (#v-login) */}
      <div
        className="view"
        id="v-login"
        role="dialog"
        aria-modal="true"
        aria-labelledby="lt"
        hidden={activeView !== 'login'}
      >
        <div className="vside">
          <img src={IMGS.clinicTeam} alt="" />
          <div className="cap">
            <span className="logo" style={{ color: '#F4EDE0' }}>
              Arogya<b>Scribe</b>
            </span>
            <p>The doctor talks. The doctor decides.</p>
          </div>
        </div>

        <div className="vform">
          <button className="back" onClick={closeViews}>
            &larr; Back to website
          </button>
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
                  disabled={loginLoading}
                  onClick={() => instantDemoLogin('orgadmin@arogyacare.in', 'OrgAdmin@123')}
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
                  disabled={loginLoading}
                  onClick={() => instantDemoLogin('reception@arogyacare.in', 'Reception@123')}
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
                  disabled={loginLoading}
                  onClick={() => instantDemoLogin('dr.sharma@arogyacare.in', 'Doctor@123')}
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

          <form id="fl" noValidate onSubmit={handleLoginSubmit}>
            <label htmlFor="le">Work email</label>
            <input
              id="le"
              type="email"
              autoComplete="username"
              required
              value={loginEmail}
              onChange={(e) => setLoginEmail(e.target.value)}
            />
            <div className="err" id="lee">
              {loginEmailErr}
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
                    value={loginPassword}
                    onChange={(e) => setLoginPassword(e.target.value)}
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
                  {loginPassErr}
                </div>
              </div>
            )}

            {loginNote && (
              <div
                className={`note ${loginNote.type === 'good' ? 'good' : loginNote.type === 'bad' ? 'bad' : ''}`}
                role="alert"
              >
                {loginNote.text}
              </div>
            )}

            <button
              className="btn p"
              id="lb"
              type="submit"
              disabled={loginLoading}
              style={{ width: '100%', marginTop: '10px' }}
            >
              {loginLoading ? 'Please wait…' : isForgot ? 'Send reset link' : 'Sign in'}
            </button>

            <p style={{ marginTop: '14px' }}>
              <a
                href="#"
                id="fg"
                onClick={(e) => {
                  e.preventDefault();
                  setIsForgot(!isForgot);
                  setLoginNote(null);
                }}
              >
                {isForgot ? 'Back to sign in' : 'Forgot password?'}
              </a>
            </p>
          </form>

          <p className="ev" style={{ marginTop: '18px' }}>
            New organization?{' '}
            <a
              href="#"
              onClick={(e) => {
                e.preventDefault();
                openView('register');
              }}
            >
              Get started
            </a>
            . There is no patient login.
          </p>
        </div>
      </div>

      {/* Integrated Organization Registration View (#v-register) */}
      <div
        className="view"
        id="v-register"
        role="dialog"
        aria-modal="true"
        aria-labelledby="rt"
        hidden={activeView !== 'register'}
      >
        <div className="vside">
          <img src={IMGS.receptionist} alt="" />
          <div className="cap">
            <span className="logo" style={{ color: '#F4EDE0' }}>
              Arogya<b>Scribe</b>
            </span>
            <p>Set up your clinic or hospital.</p>
          </div>
        </div>

        <div className="vform">
          <button className="back" onClick={closeViews}>
            &larr; Back to website
          </button>
          <h2 id="rt">Get started</h2>
          <p className="lead">
            This registers an organization, not a patient. You become its organization admin.
          </p>

          <form id="fr" noValidate onSubmit={handleRegisterSubmit}>
            <div className="g2">
              <div>
                <label htmlFor="on">Organization name</label>
                <input
                  id="on"
                  required
                  value={regOrg}
                  onChange={(e) => setRegOrg(e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="ot">Type</label>
                <select
                  id="ot"
                  value={regType}
                  onChange={(e) => setRegType(e.target.value)}
                >
                  <option>Independent practice</option>
                  <option>Clinic</option>
                  <option>Hospital</option>
                  <option>Medical centre</option>
                </select>
              </div>
              <div>
                <label htmlFor="oc">City</label>
                <input
                  id="oc"
                  required
                  value={regCity}
                  onChange={(e) => setRegCity(e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="fn">Your full name</label>
                <input
                  id="fn"
                  required
                  value={regName}
                  onChange={(e) => setRegName(e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="re">Work email</label>
                <input
                  id="re"
                  type="email"
                  required
                  value={regEmail}
                  onChange={(e) => setRegEmail(e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="rp">Password (min 8 characters)</label>
                <input
                  id="rp"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={regPassword}
                  onChange={(e) => setRegPassword(e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="rc">Confirm password</label>
                <input
                  id="rc"
                  type="password"
                  autoComplete="new-password"
                  required
                  value={regConfirmPassword}
                  onChange={(e) => setRegConfirmPassword(e.target.value)}
                />
              </div>
              <div>
                <label htmlFor="rpl">Plan</label>
                <select
                  id="rpl"
                  value={regPlan}
                  onChange={(e) => setRegPlan(e.target.value)}
                >
                  {plans.map((p) => (
                    <option key={p.id || p.code} value={p.code.toLowerCase()}>
                      {p.name} (₹{Number(p.monthly_price).toLocaleString('en-IN')}/month)
                    </option>
                  ))}
                </select>
              </div>
              <div>
                <label htmlFor="rb">Billing</label>
                <select
                  id="rb"
                  value={regBilling}
                  onChange={(e) => setRegBilling(e.target.value as any)}
                >
                  <option value="monthly">Monthly</option>
                  <option value="annual">Annual (contact us)</option>
                </select>
              </div>
              <div style={{ gridColumn: 'span 2' }}>
                <label htmlFor="rcp">Promotional Coupon (Optional)</label>
                <div style={{ display: 'flex', gap: '8px' }}>
                  <input
                    id="rcp"
                    type="text"
                    placeholder="e.g. WELCOME20, CLINIC2000, SPECIAL999"
                    value={regCoupon}
                    onChange={(e) => {
                      setRegCoupon(e.target.value.toUpperCase());
                      setCouponValidation(null);
                    }}
                    style={{ textTransform: 'uppercase', fontFamily: 'monospace', fontWeight: 600 }}
                  />
                  <button
                    type="button"
                    className="btn"
                    style={{ whiteSpace: 'nowrap' }}
                    onClick={handleValidateCoupon}
                    disabled={isValidatingCoupon || !regCoupon.trim()}
                  >
                    {isValidatingCoupon ? 'Checking…' : 'Apply'}
                  </button>
                </div>
                {couponValidation && (
                  <div
                    style={{
                      fontSize: '0.78rem',
                      fontWeight: 600,
                      marginTop: '6px',
                      color: couponValidation.valid ? '#166534' : '#991b1b',
                    }}
                  >
                    {couponValidation.valid ? '✓ ' : '✕ '}
                    {couponValidation.message}
                    {couponValidation.valid && couponValidation.final_monthly !== undefined && (
                      <span style={{ marginLeft: '6px', fontWeight: 700 }}>
                        Discounted rate: ₹{couponValidation.final_monthly.toLocaleString('en-IN')}/month
                      </span>
                    )}
                  </div>
                )}
              </div>
            </div>

            <label className="chk">
              <input
                type="checkbox"
                id="tc"
                checked={regTerms}
                onChange={(e) => setRegTerms(e.target.checked)}
              />{' '}
              I accept the terms and privacy policy [links to be added]
            </label>

            {regError && (
              <div className="err" id="re2">
                {regError}
              </div>
            )}
            {regNote && (
              <div
                className={`note ${regNote.type === 'good' ? 'good' : regNote.type === 'bad' ? 'bad' : ''}`}
                role="alert"
              >
                {regNote.text}
              </div>
            )}

            <button
              className="btn p"
              id="rbtn"
              type="submit"
              disabled={regLoading}
              style={{ width: '100%', marginTop: '10px' }}
            >
              {regLoading ? 'Please wait…' : 'Request onboarding'}
            </button>
            <p className="ev" style={{ marginTop: '8px' }}>
              No payment is taken here. Accounts are activated after review.
            </p>
          </form>
        </div>
      </div>
    </div>
  );
};
