import React, { useEffect, useState } from 'react';
import { AppLayout } from '@/components/layout/AppLayout';
import { Card } from '@/components/common/Card';
import { Button } from '@/components/common/Button';
import { Modal } from '@/components/common/Modal';
import { StatusBadge } from '@/components/common/StatusBadge';
import api, { getErrorMessage } from '@/services/api';
import { SubscriptionPlan, Organization, DiscountCoupon } from '@/types';
import {
  CreditCard,
  CheckCircle2,
  ShieldCheck,
  Zap,
  Tag,
  Sliders,
  Eye,
  Save,
  Sparkles,
  Info,
} from 'lucide-react';

export const PlansBillingPage: React.FC = () => {
  const [plans, setPlans] = useState<SubscriptionPlan[]>([]);
  const [organizations, setOrganizations] = useState<Organization[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Activation Form State
  const [selectedOrgId, setSelectedOrgId] = useState('');
  const [selectedPlanCode, setSelectedPlanCode] = useState('STARTER');
  const [billingCycle, setBillingCycle] = useState<'MONTHLY' | 'ANNUAL'>('MONTHLY');
  const [isTrial, setIsTrial] = useState(false);
  const [durationMonths, setDurationMonths] = useState(1);

  // Pricing Studio State
  const [editingPlanId, setEditingPlanId] = useState<string>('');
  const [studioCode, setStudioCode] = useState<string>('STARTER');
  const [studioName, setStudioName] = useState('Starter');
  const [studioDescription, setStudioDescription] = useState('For independent clinics.');
  const [studioMonthlyPrice, setStudioMonthlyPrice] = useState<number>(4999);
  const [studioAnnualPrice, setStudioAnnualPrice] = useState<number>(49990);
  const [studioMaxDoctors, setStudioMaxDoctors] = useState<number>(2);
  const [studioMaxReceptionists, setStudioMaxReceptionists] = useState<number>(1);
  const [studioMaxBranches, setStudioMaxBranches] = useState<number>(1);
  const [studioConsultations, setStudioConsultations] = useState<number>(250);
  const [studioStorageMb, setStudioStorageMb] = useState<number>(25600);
  const [studioFeaturesText, setStudioFeaturesText] = useState<string>('');
  const [isSavingPlan, setIsSavingPlan] = useState(false);
  const [planSaveSuccess, setPlanSaveSuccess] = useState<string | null>(null);

  // Coupon Simulator & DB Management State
  const [coupons, setCoupons] = useState<DiscountCoupon[]>([]);
  const [couponCode, setCouponCode] = useState('');
  const [couponType, setCouponType] = useState<'NONE' | 'PERCENTAGE' | 'FLAT_INR' | 'FIXED_OVERRIDE_INR'>('NONE');
  const [couponValue, setCouponValue] = useState<number>(0);
  const [isCreatingCoupon, setIsCreatingCoupon] = useState(false);
  const [newCouponCode, setNewCouponCode] = useState('');
  const [newCouponDesc, setNewCouponDesc] = useState('');
  const [newCouponType, setNewCouponType] = useState<'PERCENTAGE' | 'FLAT_INR'>('PERCENTAGE');
  const [newCouponVal, setNewCouponVal] = useState<number>(10);
  const [newCouponMaxRedemptions, setNewCouponMaxRedemptions] = useState<number>(100);
  const [couponFeedback, setCouponFeedback] = useState<string | null>(null);

  const selectPlanForStudio = (p: SubscriptionPlan) => {
    setEditingPlanId(p.id);
    setStudioCode(p.code);
    setStudioName(p.name);
    setStudioDescription(
      p.description ||
        (p.code === 'STARTER'
          ? 'For independent clinics.'
          : p.code === 'PROFESSIONAL'
          ? 'For growing clinics.'
          : 'For hospitals and medical centres.')
    );
    setStudioMonthlyPrice(Number(p.monthly_price) || 0);
    setStudioAnnualPrice(Number(p.annual_price) || (Number(p.monthly_price) * 10) || 0);
    setStudioMaxDoctors(p.max_doctors);
    setStudioMaxReceptionists(p.max_receptionists);
    setStudioMaxBranches(p.max_branches);
    setStudioConsultations(p.monthly_consultation_limit || 250);
    setStudioStorageMb(p.audio_storage_mb_limit || 25600);
    setStudioFeaturesText((p.included_features_json || []).join('\n'));
    setPlanSaveSuccess(null);
  };

  const fetchData = async () => {
    setIsLoading(true);
    try {
      const [plansRes, orgsRes, couponsRes] = await Promise.all([
        api.get('/platform/plans').catch(() => ({ data: [] })),
        api.get('/platform/organizations').catch(() => ({ data: [] })),
        api.get('/platform/coupons').catch(() => ({ data: [] })),
      ]);
      const planList: SubscriptionPlan[] = Array.isArray(plansRes.data) ? plansRes.data : [];
      setPlans(planList);
      if (planList.length > 0 && !editingPlanId) {
        selectPlanForStudio(planList[0]);
      }
      const orgList = Array.isArray(orgsRes.data) ? orgsRes.data : [];
      setOrganizations(orgList);
      if (orgList.length > 0 && !selectedOrgId) {
        setSelectedOrgId(orgList[0].id);
      }
      const couponList = Array.isArray(couponsRes.data) ? couponsRes.data : [];
      setCoupons(couponList);
    } catch (err) {
      console.error('Failed to load plans data:', err);
    } finally {
      setIsLoading(false);
    }
  };

  const handleCreateCoupon = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!newCouponCode.trim()) return;
    setIsCreatingCoupon(true);
    setCouponFeedback(null);
    try {
      await api.post('/platform/coupons', {
        code: newCouponCode.trim().toUpperCase(),
        description: newCouponDesc.trim() || undefined,
        discount_type: newCouponType,
        discount_value: Number(newCouponVal),
        applicable_plan_codes: ['STARTER', 'PROFESSIONAL', 'ENTERPRISE'],
        max_redemptions: Number(newCouponMaxRedemptions) || 100,
        is_active: true,
      });
      setCouponFeedback(`Coupon ${newCouponCode.toUpperCase()} successfully created in DB!`);
      setNewCouponCode('');
      setNewCouponDesc('');
      fetchData();
    } catch (err) {
      setCouponFeedback(`Failed to create coupon: ${getErrorMessage(err)}`);
    } finally {
      setIsCreatingCoupon(false);
    }
  };

  const handleToggleCouponActive = async (coupon: DiscountCoupon) => {
    try {
      await api.patch(`/platform/coupons/${coupon.id}`, {
        is_active: !coupon.is_active,
      });
      fetchData();
    } catch (err) {
      alert(`Failed to update coupon status: ${getErrorMessage(err)}`);
    }
  };

  const applyCouponToStudio = (c: DiscountCoupon) => {
    setCouponCode(c.code);
    setCouponType(c.discount_type as any);
    setCouponValue(Number(c.discount_value));
  };

  useEffect(() => {
    fetchData();
  }, []);

  const computeEffectivePrice = () => {
    const base = Number(studioMonthlyPrice) || 0;
    if (couponType === 'PERCENTAGE' && couponValue > 0) {
      return Math.max(0, Math.round(base * (1 - couponValue / 100)));
    }
    if (couponType === 'FLAT_INR' && couponValue > 0) {
      return Math.max(0, Math.round(base - couponValue));
    }
    if (couponType === 'FIXED_OVERRIDE_INR' && couponValue > 0) {
      return Math.max(0, couponValue);
    }
    return base;
  };

  const effectivePrice = computeEffectivePrice();
  const isDiscounted = couponType !== 'NONE' && effectivePrice < Number(studioMonthlyPrice);

  const handleSavePlanToProduction = async () => {
    if (!editingPlanId) return;
    setIsSavingPlan(true);
    setPlanSaveSuccess(null);
    setError(null);
    try {
      const featuresArray = studioFeaturesText
        .split('\n')
        .map((s) => s.trim())
        .filter(Boolean);

      await api.patch(`/platform/plans/${editingPlanId}`, {
        name: studioName,
        description: studioDescription,
        monthly_price: Number(studioMonthlyPrice),
        annual_price: Number(studioAnnualPrice),
        max_doctors: Number(studioMaxDoctors),
        max_receptionists: Number(studioMaxReceptionists),
        max_branches: Number(studioMaxBranches),
        monthly_consultation_limit: Number(studioConsultations),
        audio_storage_mb_limit: Number(studioStorageMb),
        included_features_json: featuresArray,
      });

      setPlanSaveSuccess('Plan successfully updated in production database! Public landing page will immediately reflect new price.');
      fetchData();
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSavingPlan(false);
    }
  };

  const handleActivateSubscription = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!selectedOrgId) {
      setError('Please select an organization.');
      return;
    }

    setIsSubmitting(true);
    setError(null);
    setSuccessMessage(null);

    try {
      const targetPlan = plans.find((p) => p.code === selectedPlanCode || p.id === selectedPlanCode) || plans[0];
      await api.post('/platform/subscriptions/activate', {
        organization_id: selectedOrgId,
        plan_id: targetPlan ? targetPlan.id : selectedPlanCode,
        billing_cycle: billingCycle,
        duration_days: Number(durationMonths) * 30,
      });

      setSuccessMessage('Subscription successfully activated!');
      setTimeout(() => {
        setIsModalOpen(false);
        setSuccessMessage(null);
      }, 1500);
    } catch (err) {
      setError(getErrorMessage(err));
    } finally {
      setIsSubmitting(false);
    }
  };

  return (
    <AppLayout>
      <div className="space-y-8">
        {/* Header */}
        <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.14em] text-accent mb-1">
              PLATFORM CONSOLE
            </div>
            <h1 className="font-serif text-3xl font-bold text-ink">Plans & Billing</h1>
            <p className="text-sm text-text-2 mt-1">
              Live production subscription plans, quota limits, promo pricing studio, and manual tenant activations.
            </p>
          </div>
          <Button
            variant="primary"
            leftIcon={<Zap className="w-4 h-4" />}
            onClick={() => setIsModalOpen(true)}
          >
            Activate Subscription (Dev/Manual)
          </Button>
        </div>

        {/* Current Active Production Plans Grid */}
        <div>
          <div className="flex items-center justify-between mb-4">
            <h2 className="font-serif text-xl font-bold text-ink">Active Production Plans</h2>
            <span className="text-xs text-text-2">Click any plan to open Live Pricing & Coupon Studio</span>
          </div>

          <div className="grid md:grid-cols-3 gap-6">
            {plans.map((plan) => {
              const isSelected = plan.id === editingPlanId;
              const isPopular = plan.code === 'PROFESSIONAL';
              return (
                <div
                  key={plan.id}
                  onClick={() => selectPlanForStudio(plan)}
                  className={`bg-surface rounded-xl border p-6 flex flex-col justify-between shadow-card cursor-pointer transition-all ${
                    isSelected
                      ? 'border-2 border-accent shadow-md bg-surface-2/40'
                      : isPopular
                      ? 'border-2 border-accent-2/60'
                      : 'border-line hover:border-text-2'
                  }`}
                >
                  <div>
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-semibold uppercase tracking-wider text-text-2 font-mono">
                          {plan.code}
                        </span>
                        {isPopular && (
                          <span className="text-[10px] font-bold px-2 py-0.5 rounded-full bg-emerald-900/60 text-emerald-200 border border-emerald-700/50">
                            Recommended
                          </span>
                        )}
                      </div>
                      <StatusBadge status={plan.is_active ? 'ACTIVE' : 'SUSPENDED'} />
                    </div>

                    <h3 className="font-serif text-2xl font-bold text-ink mt-2">{plan.name}</h3>
                    <p className="text-xs text-text-2 mt-0.5">{plan.description || 'Clinic subscription plan'}</p>

                    <div className="mt-4 flex items-baseline gap-1">
                      <span className="text-3xl font-bold text-ink font-mono">
                        &#8377;{Number(plan.monthly_price)?.toLocaleString('en-IN') ?? '—'}
                      </span>
                      <span className="text-xs text-text-2">/month</span>
                    </div>

                    <div className="mt-6 pt-4 border-t border-line/40 space-y-2 text-xs text-text-2">
                      <div className="flex justify-between">
                        <span>Doctors Allowed:</span>
                        <strong className="text-ink font-mono">{plan.max_doctors}</strong>
                      </div>
                      <div className="flex justify-between">
                        <span>Receptionists:</span>
                        <strong className="text-ink font-mono">{plan.max_receptionists}</strong>
                      </div>
                      <div className="flex justify-between">
                        <span>Branches Allowed:</span>
                        <strong className="text-ink font-mono">{plan.max_branches}</strong>
                      </div>
                      <div className="flex justify-between">
                        <span>Monthly Consultations:</span>
                        <strong className="text-ink font-mono">
                          {Number(plan.monthly_consultation_limit || plan.max_consultations_per_month)?.toLocaleString('en-IN') ?? '250'}
                        </strong>
                      </div>
                      <div className="flex justify-between">
                        <span>Private Storage:</span>
                        <strong className="text-ink font-mono">
                          {Math.round((plan.audio_storage_mb_limit || 1024) / 1024)} GB
                        </strong>
                      </div>
                    </div>
                  </div>

                  <div className="mt-6 pt-4 border-t border-line/40 flex gap-2">
                    <Button
                      variant={isSelected ? 'primary' : 'outline'}
                      size="sm"
                      className="w-full text-xs"
                      onClick={(e) => {
                        e.stopPropagation();
                        selectPlanForStudio(plan);
                      }}
                    >
                      {isSelected ? 'Editing in Studio ↓' : 'Configure & Test Coupon'}
                    </Button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Platform Owner Pricing & Coupon Studio */}
        <div className="bg-surface rounded-2xl border border-line p-6 shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between pb-6 border-b border-line/60 gap-4">
            <div>
              <div className="flex items-center gap-2">
                <Sliders className="w-5 h-5 text-accent" />
                <h2 className="font-serif text-2xl font-bold text-ink">
                  Platform Owner Pricing & Coupon Studio
                </h2>
              </div>
              <p className="text-xs text-text-2 mt-1">
                Configure plan prices, quotas, and simulate promotional coupons. Changes save directly to the database and update the public landing page in real-time.
              </p>
            </div>
            {editingPlanId && (
              <Button
                variant="primary"
                leftIcon={<Save className="w-4 h-4" />}
                onClick={handleSavePlanToProduction}
                isLoading={isSavingPlan}
              >
                Save Plan Changes to Production
              </Button>
            )}
          </div>

          {planSaveSuccess && (
            <div className="mt-4 p-3 rounded-lg bg-emerald-50 border border-emerald-300 text-emerald-800 text-xs font-semibold flex items-center gap-2">
              <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
              <span>{planSaveSuccess}</span>
            </div>
          )}

          <div className="grid lg:grid-cols-12 gap-8 mt-6">
            {/* Left 7 Columns: Form Controls */}
            <div className="lg:col-span-7 space-y-6">
              {/* Plan Tabs */}
              <div>
                <label className="block text-xs font-semibold uppercase tracking-wider text-text-2 mb-2">
                  Select Plan to Configure
                </label>
                <div className="flex gap-2">
                  {plans.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => selectPlanForStudio(p)}
                      className={`px-4 py-2 text-xs font-bold rounded-lg border transition-all ${
                        p.id === editingPlanId
                          ? 'bg-ink text-surface border-ink shadow-sm'
                          : 'bg-surface-2 text-text-2 border-line hover:text-ink'
                      }`}
                    >
                      {p.name} (&#8377;{Number(p.monthly_price).toLocaleString('en-IN')})
                    </button>
                  ))}
                </div>
              </div>

              {/* Basic Details */}
              <div className="grid sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs font-semibold text-text mb-1">Plan Name</label>
                  <input
                    type="text"
                    value={studioName}
                    onChange={(e) => setStudioName(e.target.value)}
                    className="w-full px-3 py-2 bg-surface-2 border border-line rounded text-sm text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                  />
                </div>
                <div>
                  <label className="block text-xs font-semibold text-text mb-1">Target Audience / Description</label>
                  <input
                    type="text"
                    value={studioDescription}
                    onChange={(e) => setStudioDescription(e.target.value)}
                    className="w-full px-3 py-2 bg-surface-2 border border-line rounded text-sm text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                  />
                </div>
              </div>

              {/* Price Controls */}
              <div className="grid sm:grid-cols-2 gap-4 p-4 rounded-xl bg-surface-2/60 border border-line/60">
                <div>
                  <label className="block text-xs font-semibold text-text mb-1">Monthly Price (&#8377; INR) *</label>
                  <div className="relative">
                    <span className="absolute left-3 top-2 text-text-2 text-sm">&#8377;</span>
                    <input
                      type="number"
                      min={0}
                      step={100}
                      value={studioMonthlyPrice}
                      onChange={(e) => setStudioMonthlyPrice(Number(e.target.value))}
                      className="w-full pl-8 pr-3 py-2 bg-surface border border-line rounded text-sm font-bold text-ink focus:outline-none focus:ring-1 focus:ring-ink font-mono"
                    />
                  </div>
                </div>
                <div>
                  <label className="block text-xs font-semibold text-text mb-1">Annual Price (&#8377; INR)</label>
                  <div className="relative">
                    <span className="absolute left-3 top-2 text-text-2 text-sm">&#8377;</span>
                    <input
                      type="number"
                      min={0}
                      step={500}
                      value={studioAnnualPrice}
                      onChange={(e) => setStudioAnnualPrice(Number(e.target.value))}
                      className="w-full pl-8 pr-3 py-2 bg-surface border border-line rounded text-sm font-bold text-ink focus:outline-none focus:ring-1 focus:ring-ink font-mono"
                    />
                  </div>
                </div>
              </div>

              {/* Quotas & Seat Limits */}
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                <div>
                  <label className="block text-[11px] font-semibold text-text-2 mb-1">Max Doctors</label>
                  <input
                    type="number"
                    min={1}
                    value={studioMaxDoctors}
                    onChange={(e) => setStudioMaxDoctors(Number(e.target.value))}
                    className="w-full px-3 py-1.5 bg-surface-2 border border-line rounded text-sm text-ink font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-text-2 mb-1">Max Receptionists</label>
                  <input
                    type="number"
                    min={0}
                    value={studioMaxReceptionists}
                    onChange={(e) => setStudioMaxReceptionists(Number(e.target.value))}
                    className="w-full px-3 py-1.5 bg-surface-2 border border-line rounded text-sm text-ink font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-text-2 mb-1">Max Branches</label>
                  <input
                    type="number"
                    min={1}
                    value={studioMaxBranches}
                    onChange={(e) => setStudioMaxBranches(Number(e.target.value))}
                    className="w-full px-3 py-1.5 bg-surface-2 border border-line rounded text-sm text-ink font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-text-2 mb-1">Monthly Consultations</label>
                  <input
                    type="number"
                    min={50}
                    step={50}
                    value={studioConsultations}
                    onChange={(e) => setStudioConsultations(Number(e.target.value))}
                    className="w-full px-3 py-1.5 bg-surface-2 border border-line rounded text-sm text-ink font-mono"
                  />
                </div>
                <div>
                  <label className="block text-[11px] font-semibold text-text-2 mb-1">Storage (MB)</label>
                  <input
                    type="number"
                    min={1024}
                    step={1024}
                    value={studioStorageMb}
                    onChange={(e) => setStudioStorageMb(Number(e.target.value))}
                    className="w-full px-3 py-1.5 bg-surface-2 border border-line rounded text-sm text-ink font-mono"
                  />
                </div>
              </div>

              {/* Features List */}
              <div>
                <label className="block text-xs font-semibold text-text mb-1">
                  Feature Bullets (1 item per line)
                </label>
                <textarea
                  rows={4}
                  value={studioFeaturesText}
                  onChange={(e) => setStudioFeaturesText(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-2 border border-line rounded text-xs font-mono text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                  placeholder="Up to 2 doctors&#10;1 receptionist&#10;250 consultations/month"
                />
              </div>

              {/* Promo Coupon Simulator */}
              <div className="p-4 rounded-xl bg-accent-2/10 border border-accent-2/40 space-y-3">
                <div className="flex items-center gap-2">
                  <Tag className="w-4 h-4 text-accent" />
                  <span className="text-xs font-bold uppercase tracking-wider text-ink">
                    Promo Coupon Simulator (Preview Discounted Customer Rate)
                  </span>
                </div>

                <div className="grid sm:grid-cols-3 gap-3">
                  <div>
                    <label className="block text-[11px] font-semibold text-text-2 mb-1">Promo Code</label>
                    <input
                      type="text"
                      placeholder="e.g. DIWALI50"
                      value={couponCode}
                      onChange={(e) => setCouponCode(e.target.value.toUpperCase())}
                      className="w-full px-3 py-1.5 bg-surface border border-line rounded text-xs uppercase font-mono font-bold text-ink"
                    />
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold text-text-2 mb-1">Discount Type</label>
                    <select
                      value={couponType}
                      onChange={(e) => setCouponType(e.target.value as any)}
                      className="w-full px-3 py-1.5 bg-surface border border-line rounded text-xs text-ink"
                    >
                      <option value="NONE">No Coupon</option>
                      <option value="PERCENTAGE">PERCENTAGE (% off)</option>
                      <option value="FLAT_INR">FLAT_INR (&#8377; off)</option>
                      <option value="FIXED_OVERRIDE_INR">FIXED_OVERRIDE_INR (Fixed &#8377;)</option>
                    </select>
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold text-text-2 mb-1">
                      {couponType === 'PERCENTAGE' ? 'Discount %' : 'Discount Amount (&#8377;)'}
                    </label>
                    <input
                      type="number"
                      min={0}
                      disabled={couponType === 'NONE'}
                      value={couponValue}
                      onChange={(e) => setCouponValue(Number(e.target.value))}
                      className="w-full px-3 py-1.5 bg-surface border border-line rounded text-xs font-mono font-bold text-ink disabled:opacity-50"
                    />
                  </div>
                </div>

                {isDiscounted && (
                  <div className="text-xs font-semibold text-emerald-800 flex items-center gap-1.5">
                    <Sparkles className="w-3.5 h-3.5 text-emerald-600" />
                    <span>
                      Coupon "{couponCode || 'PROMO'}" applied! Customer saves &#8377;
                      {(Number(studioMonthlyPrice) - effectivePrice).toLocaleString('en-IN')} / month.
                    </span>
                  </div>
                )}
              </div>
            </div>

            {/* Right 5 Columns: Live Customer Pricing Card Preview */}
            <div className="lg:col-span-5 flex flex-col items-center">
              <div className="w-full max-w-sm">
                <div className="flex items-center gap-1.5 mb-2 text-xs font-semibold uppercase tracking-wider text-text-2">
                  <Eye className="w-3.5 h-3.5 text-accent" />
                  <span>Live Customer Pricing Card Preview</span>
                </div>

                {/* The Preview Card */}
                <div
                  className={`rounded-2xl border p-6 flex flex-col justify-between shadow-lg relative ${
                    studioCode === 'PROFESSIONAL'
                      ? 'bg-ink text-surface border-accent-2'
                      : 'bg-surface text-ink border-line'
                  }`}
                >
                  {studioCode === 'PROFESSIONAL' && (
                    <span className="absolute -top-3 right-6 px-3 py-0.5 rounded-full text-[11px] font-bold bg-emerald-900/90 text-emerald-100 border border-emerald-600 shadow-sm">
                      Recommended
                    </span>
                  )}

                  <div>
                    <h3 className={`font-serif text-2xl font-bold ${studioCode === 'PROFESSIONAL' ? 'text-white' : 'text-ink'}`}>
                      {studioName}
                    </h3>
                    <p className={`text-xs mt-1 ${studioCode === 'PROFESSIONAL' ? 'text-surface/80' : 'text-text-2'}`}>
                      {studioDescription}
                    </p>

                    <div className="mt-5 flex items-baseline gap-2">
                      {isDiscounted ? (
                        <>
                          <span className="text-3xl font-bold font-mono text-emerald-400">
                            &#8377;{effectivePrice.toLocaleString('en-IN')}
                          </span>
                          <span className="text-sm line-through text-text-2/70 font-mono">
                            &#8377;{Number(studioMonthlyPrice).toLocaleString('en-IN')}
                          </span>
                        </>
                      ) : (
                        <span className={`text-3xl font-bold font-mono ${studioCode === 'PROFESSIONAL' ? 'text-white' : 'text-ink'}`}>
                          &#8377;{Number(studioMonthlyPrice).toLocaleString('en-IN')}
                        </span>
                      )}
                      <span className={`text-xs ${studioCode === 'PROFESSIONAL' ? 'text-surface/70' : 'text-text-2'}`}>
                        / month
                      </span>
                    </div>

                    {isDiscounted && (
                      <div className="mt-1 text-[11px] font-bold text-emerald-400 uppercase tracking-wide">
                        ★ {couponCode || 'PROMO'} APPLIED
                      </div>
                    )}

                    <ul className="mt-5 space-y-2 text-xs border-t border-line/30 pt-4">
                      {studioFeaturesText
                        .split('\n')
                        .map((s) => s.trim())
                        .filter(Boolean)
                        .map((f, i) => (
                          <li key={i} className="flex items-center gap-2">
                            <span className="text-emerald-500 font-bold">&#10003;</span>
                            <span className={studioCode === 'PROFESSIONAL' ? 'text-surface/90' : 'text-text'}>
                              {f}
                            </span>
                          </li>
                        ))}
                    </ul>
                  </div>

                  <div className="mt-6 pt-4 border-t border-line/30">
                    <button
                      type="button"
                      disabled
                      className={`w-full py-2.5 px-4 rounded-lg font-bold text-xs uppercase tracking-wider text-center shadow-sm cursor-not-allowed ${
                        studioCode === 'PROFESSIONAL'
                          ? 'bg-accent-2 text-ink'
                          : 'bg-ink text-surface'
                      }`}
                    >
                      Choose {studioName}
                    </button>
                    <div className="mt-2 text-[10px] text-center text-text-2">
                      Customer preview • Instant DB sync
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Persisted Promotional Coupons (Super Admin DB Managed) */}
        <div className="bg-surface rounded-2xl border border-line p-6 shadow-sm space-y-6">
          <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4 border-b border-line pb-4">
            <div>
              <div className="flex items-center gap-2">
                <Tag className="w-5 h-5 text-accent" />
                <h3 className="font-serif text-xl font-bold text-ink">
                  Promotional Discount Coupons (Database Persisted)
                </h3>
              </div>
              <p className="text-xs text-text-2 mt-1">
                Manage promotional codes stored in PostgreSQL. Validated in real-time during clinic registration and subscription checkout.
              </p>
            </div>
          </div>

          {couponFeedback && (
            <div className="p-3 bg-accent-2/20 border border-accent-2 text-xs font-semibold text-ink rounded-lg">
              {couponFeedback}
            </div>
          )}

          {/* Quick Create Coupon Mini-Form */}
          <form onSubmit={handleCreateCoupon} className="p-4 bg-surface-2 rounded-xl border border-line grid grid-cols-1 sm:grid-cols-5 gap-3 items-end">
            <div>
              <label className="block text-[11px] font-bold text-text uppercase mb-1">Coupon Code *</label>
              <input
                required
                type="text"
                placeholder="e.g. MONSOON30"
                value={newCouponCode}
                onChange={(e) => setNewCouponCode(e.target.value.toUpperCase())}
                className="w-full px-3 py-1.5 bg-surface border border-line rounded text-xs font-mono font-bold text-ink"
              />
            </div>
            <div>
              <label className="block text-[11px] font-bold text-text uppercase mb-1">Description</label>
              <input
                type="text"
                placeholder="e.g. Monsoon 30% Off"
                value={newCouponDesc}
                onChange={(e) => setNewCouponDesc(e.target.value)}
                className="w-full px-3 py-1.5 bg-surface border border-line rounded text-xs text-ink"
              />
            </div>
            <div>
              <label className="block text-[11px] font-bold text-text uppercase mb-1">Discount Type</label>
              <select
                value={newCouponType}
                onChange={(e) => setNewCouponType(e.target.value as any)}
                className="w-full px-3 py-1.5 bg-surface border border-line rounded text-xs text-ink"
              >
                <option value="PERCENTAGE">PERCENTAGE (% off)</option>
                <option value="FLAT_INR">FLAT_INR (&#8377; off)</option>
              </select>
            </div>
            <div>
              <label className="block text-[11px] font-bold text-text uppercase mb-1">
                Value {newCouponType === 'PERCENTAGE' ? '(%)' : '(&#8377;)'} *
              </label>
              <input
                required
                type="number"
                min={1}
                value={newCouponVal}
                onChange={(e) => setNewCouponVal(Number(e.target.value))}
                className="w-full px-3 py-1.5 bg-surface border border-line rounded text-xs font-mono font-bold text-ink"
              />
            </div>
            <div>
              <Button type="submit" variant="primary" size="sm" className="w-full" isLoading={isCreatingCoupon}>
                Create Coupon
              </Button>
            </div>
          </form>

          {/* Coupons Table */}
          <div className="overflow-x-auto border border-line rounded-xl">
            <table className="w-full text-left text-xs">
              <thead className="bg-surface-2 text-text-2 uppercase text-[10px] tracking-wider border-b border-line">
                <tr>
                  <th className="py-3 px-4">Coupon Code</th>
                  <th className="py-3 px-4">Description</th>
                  <th className="py-3 px-4">Discount</th>
                  <th className="py-3 px-4">Applicable Plans</th>
                  <th className="py-3 px-4">Redemptions</th>
                  <th className="py-3 px-4">Status</th>
                  <th className="py-3 px-4 text-right">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-line">
                {coupons.length === 0 ? (
                  <tr>
                    <td colSpan={7} className="py-6 text-center text-text-2">
                      No active discount coupons found in database. Create one above!
                    </td>
                  </tr>
                ) : (
                  coupons.map((c) => (
                    <tr key={c.id} className="hover:bg-surface-2/40 transition-colors">
                      <td className="py-3 px-4 font-mono font-bold text-ink flex items-center gap-2">
                        <Tag className="w-3.5 h-3.5 text-accent" />
                        <span>{c.code}</span>
                      </td>
                      <td className="py-3 px-4 text-text">{c.description || '—'}</td>
                      <td className="py-3 px-4 font-mono font-semibold text-emerald-800">
                        {c.discount_type === 'PERCENTAGE'
                          ? `${Number(c.discount_value)}% OFF`
                          : `&#8377;${Number(c.discount_value).toLocaleString('en-IN')} OFF`}
                      </td>
                      <td className="py-3 px-4 text-text-2">
                        {c.applicable_plan_codes && c.applicable_plan_codes.length > 0
                          ? c.applicable_plan_codes.join(', ')
                          : 'ALL PLANS'}
                      </td>
                      <td className="py-3 px-4 font-mono text-text">
                        {c.current_redemptions} / {c.max_redemptions}
                      </td>
                      <td className="py-3 px-4">
                        <span
                          className={`px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider ${
                            c.is_active
                              ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                              : 'bg-zinc-100 text-zinc-600 border border-zinc-300'
                          }`}
                        >
                          {c.is_active ? 'Active' : 'Deactivated'}
                        </span>
                      </td>
                      <td className="py-3 px-4 text-right space-x-2">
                        <button
                          type="button"
                          onClick={() => applyCouponToStudio(c)}
                          className="px-2 py-1 rounded bg-accent-2/20 hover:bg-accent-2/40 text-ink font-semibold text-[11px]"
                        >
                          Simulate
                        </button>
                        <button
                          type="button"
                          onClick={() => handleToggleCouponActive(c)}
                          className="px-2 py-1 rounded border border-line hover:bg-surface-2 text-text text-[11px]"
                        >
                          {c.is_active ? 'Deactivate' : 'Activate'}
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        </div>

        {/* Subscription Activation Modal */}
        <Modal
          isOpen={isModalOpen}
          onClose={() => {
            setIsModalOpen(false);
            setError(null);
            setSuccessMessage(null);
          }}
          title="Manual Subscription Activation"
          subtitle="Provision or extend an active subscription for any tenant organization."
          maxWidth="md"
        >
          {successMessage ? (
            <div className="py-6 text-center space-y-2">
              <CheckCircle2 className="w-10 h-10 text-status-approved mx-auto" />
              <div className="font-semibold text-ink text-sm">{successMessage}</div>
            </div>
          ) : (
            <form onSubmit={handleActivateSubscription} className="space-y-4">
              {error && (
                <div className="p-3 rounded-md bg-status-rec-bg border border-status-err/30 text-xs text-status-err font-medium">
                  {error}
                </div>
              )}

              <div>
                <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                  Target Organization *
                </label>
                <select
                  required
                  value={selectedOrgId}
                  onChange={(e) => setSelectedOrgId(e.target.value)}
                  className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                >
                  {organizations.map((org) => (
                    <option key={org.id} value={org.id}>
                      {org.name} ({org.contact_email})
                    </option>
                  ))}
                </select>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                    Plan *
                  </label>
                  <select
                    value={selectedPlanCode}
                    onChange={(e) => setSelectedPlanCode(e.target.value)}
                    className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                  >
                    {plans.map((p) => (
                      <option key={p.id} value={p.code}>
                        {p.name} (&#8377;{Number(p.monthly_price).toLocaleString('en-IN')})
                      </option>
                    ))}
                  </select>
                </div>

                <div>
                  <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                    Billing Cycle
                  </label>
                  <select
                    value={billingCycle}
                    onChange={(e) => setBillingCycle(e.target.value as any)}
                    className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                  >
                    <option value="MONTHLY">Monthly</option>
                    <option value="ANNUAL">Annual</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-xs font-semibold text-text uppercase tracking-wider mb-1">
                    Duration (Months)
                  </label>
                  <input
                    type="number"
                    min={1}
                    max={36}
                    value={durationMonths}
                    onChange={(e) => setDurationMonths(Number(e.target.value))}
                    className="w-full px-3 py-2 bg-surface-2/60 border border-line rounded text-sm text-ink focus:outline-none focus:ring-1 focus:ring-ink"
                  />
                </div>

                <div className="flex items-center pt-5">
                  <label className="flex items-center gap-2 cursor-pointer text-xs font-medium text-ink">
                    <input
                      type="checkbox"
                      checked={isTrial}
                      onChange={(e) => setIsTrial(e.target.checked)}
                      className="rounded border-line text-accent focus:ring-accent"
                    />
                    <span>Mark as Free Trial</span>
                  </label>
                </div>
              </div>

              <div className="pt-2 flex justify-end gap-2">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => setIsModalOpen(false)}
                >
                  Cancel
                </Button>
                <Button type="submit" variant="primary" isLoading={isSubmitting}>
                  Confirm Activation
                </Button>
              </div>
            </form>
          )}
        </Modal>
      </div>
    </AppLayout>
  );
};
