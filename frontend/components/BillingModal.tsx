'use client';

import React, { useState, useEffect } from 'react';
import { useAuth } from '../lib/authContext';
import {
  getBillingPlans,
  getOrganizationUsage,
  createRazorpayOrder,
  verifyRazorpayPayment,
  SaasPlan,
  SaasUsageResponse
} from '../lib/api';
import {
  X, CreditCard, Check, Activity
} from 'lucide-react';

interface RazorpayPaymentResponse {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
}

interface RazorpayInstance {
  open: () => void;
}

interface RazorpayConstructor {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  new(options: Record<string, any>): RazorpayInstance;
}

interface BillingModalProps {
  isOpen: boolean;
  onClose: () => void;
}

export const BillingModal: React.FC<BillingModalProps> = ({ isOpen, onClose }) => {
  const { activeOrg, refreshTenantState } = useAuth();
  const [plans, setPlans] = useState<SaasPlan[]>([]);
  const [usage, setUsage] = useState<SaasUsageResponse | null>(null);
  const [billingCycle, setBillingCycle] = useState<'monthly' | 'annual'>('monthly');
  const [checkoutLoading, setCheckoutLoading] = useState<string | null>(null);
  const [successMsg, setSuccessMsg] = useState('');
  const [errorMsg, setErrorMsg] = useState('');

  useEffect(() => {
    if (isOpen && activeOrg) {
      loadBillingData();
    }
  }, [isOpen, activeOrg]);

  const loadBillingData = async () => {
    try {
      const [p, u] = await Promise.all([
        getBillingPlans(),
        getOrganizationUsage().catch(() => null)
      ]);
      setPlans(p);
      setUsage(u);
    } catch {
      setErrorMsg('Failed to load billing metrics');
    }
  };

  if (!isOpen || !activeOrg) return null;

  const handleUpgrade = async (planId: string) => {
    if (planId === activeOrg.plan) return;
    setCheckoutLoading(planId);
    setErrorMsg('');
    setSuccessMsg('');

    try {
      const checkoutInfo = await createRazorpayOrder({
        plan: planId,
        billing_cycle: billingCycle
      });

      // Check if Razorpay JS SDK is loaded on window
      if (typeof window !== 'undefined' && (window as unknown as { Razorpay?: RazorpayConstructor }).Razorpay) {
        const RazorpayClass = (window as unknown as { Razorpay: RazorpayConstructor }).Razorpay;
        const options: Record<string, unknown> = {
          key: checkoutInfo.razorpay_key_id,
          amount: checkoutInfo.amount,
          currency: checkoutInfo.currency,
          name: 'InfernoX Intelligence',
          description: `Subscription upgrade to ${planId.toUpperCase()} tier`,
          order_id: checkoutInfo.order_id,
          prefill: {
            name: checkoutInfo.prefill_name,
            email: checkoutInfo.prefill_email
          },
          theme: { color: '#f59e0b' },
          handler: async (response: RazorpayPaymentResponse) => {
            try {
              await verifyRazorpayPayment({
                razorpay_order_id: response.razorpay_order_id,
                razorpay_payment_id: response.razorpay_payment_id,
                razorpay_signature: response.razorpay_signature,
                plan: planId
              });
              setSuccessMsg(`Successfully upgraded to ${planId.toUpperCase()}!`);
              await refreshTenantState();
              loadBillingData();
            } catch {
              setErrorMsg('Payment verification failed on backend.');
            }
          }
        };
        const rzp = new RazorpayClass(options);
        rzp.open();
      } else {
        // Dev Sandbox / Demo mode verification
        const demoPaymentId = `pay_demo_${Date.now()}`;
        const demoSignature = `demo_sig_${Date.now()}`;
        await verifyRazorpayPayment({
          razorpay_order_id: checkoutInfo.order_id,
          razorpay_payment_id: demoPaymentId,
          razorpay_signature: demoSignature,
          plan: planId
        });
        setSuccessMsg(`Plan successfully updated to ${planId.toUpperCase()} tier (Sandbox Mode)!`);
        await refreshTenantState();
        loadBillingData();
      }
    } catch (err: unknown) {
      const apiErr = err as { response?: { data?: { detail?: string } } };
      setErrorMsg(apiErr?.response?.data?.detail || 'Failed to initialize subscription checkout');
    } finally {
      setCheckoutLoading(null);
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-950/80 backdrop-blur-md">
      <div className="relative w-full max-w-5xl max-h-[90vh] bg-slate-900 border border-slate-700/80 rounded-2xl shadow-2xl flex flex-col overflow-hidden animate-in fade-in zoom-in-95 duration-200">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-800 bg-slate-900/90">
          <div className="flex items-center gap-3">
            <div className="p-2 rounded-xl bg-gradient-to-br from-amber-500 to-amber-600 text-slate-950 shadow-md">
              <CreditCard size={20} />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h2 className="text-lg font-bold text-white">Subscription & Usage Metering</h2>
                <span className="text-[10px] font-bold tracking-wider px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/30 uppercase">
                  {activeOrg.plan}
                </span>
              </div>
              <p className="text-xs text-slate-400">Razorpay Enterprise Billing & Resource Limits</p>
            </div>
          </div>
          <button
            onClick={onClose}
            className="p-1.5 rounded-lg text-slate-400 hover:text-white hover:bg-slate-800 transition-colors"
          >
            <X size={18} />
          </button>
        </div>

        {/* Content Body */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6">
          {successMsg && (
            <div className="p-3.5 rounded-xl bg-emerald-500/10 border border-emerald-500/30 text-emerald-300 text-xs font-semibold">
              ✓ {successMsg}
            </div>
          )}

          {errorMsg && (
            <div className="p-3.5 rounded-xl bg-rose-500/10 border border-rose-500/30 text-rose-300 text-xs">
              ✕ {errorMsg}
            </div>
          )}

          {/* Usage Metering Section */}
          {usage && (
            <div className="p-5 rounded-2xl bg-slate-950/70 border border-slate-800 space-y-4">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Activity size={16} className="text-amber-400" />
                  <h3 className="text-xs font-bold uppercase tracking-wider text-slate-200">
                    Live System Usage (Billing Cycle: {usage.billing_period})
                  </h3>
                </div>
                <span className="text-xs text-slate-400">
                  Calculated from verified database entities
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                {Object.entries(usage.metrics).map(([key, val]) => (
                  <div key={key} className="p-3.5 rounded-xl bg-slate-900 border border-slate-800/80 space-y-2">
                    <div className="flex justify-between items-center text-xs">
                      <span className="text-slate-400 capitalize">{key.replace('_', ' ')}</span>
                      <span className="font-mono font-semibold text-slate-200">
                        {val.current_value} / {val.limit_value}
                      </span>
                    </div>
                    <div className="w-full h-1.5 bg-slate-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full transition-all duration-500 ${
                          val.usage_percent > 85
                            ? 'bg-rose-500'
                            : val.usage_percent > 60
                            ? 'bg-amber-500'
                            : 'bg-emerald-500'
                        }`}
                        style={{ width: `${val.usage_percent}%` }}
                      />
                    </div>
                    <span className="text-[10px] text-slate-500 block text-right font-medium">
                      {val.usage_percent}% utilized
                    </span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Billing Cycle Switcher */}
          <div className="flex items-center justify-center gap-3">
            <button
              onClick={() => setBillingCycle('monthly')}
              className={`px-4 py-1.5 rounded-xl text-xs font-semibold transition-all ${
                billingCycle === 'monthly'
                  ? 'bg-amber-500 text-slate-950 shadow-md'
                  : 'text-slate-400 hover:text-slate-200 bg-slate-900 border border-slate-800'
              }`}
            >
              Monthly Billing
            </button>
            <button
              onClick={() => setBillingCycle('annual')}
              className={`px-4 py-1.5 rounded-xl text-xs font-semibold flex items-center gap-1.5 transition-all ${
                billingCycle === 'annual'
                  ? 'bg-amber-500 text-slate-950 shadow-md'
                  : 'text-slate-400 hover:text-slate-200 bg-slate-900 border border-slate-800'
              }`}
            >
              <span>Annual Billing</span>
              <span className="text-[10px] uppercase font-bold px-1.5 py-0.5 rounded bg-emerald-500/20 text-emerald-300 border border-emerald-500/30">
                Save 17%
              </span>
            </button>
          </div>

          {/* Plan Cards Grid */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
            {plans.map((p) => {
              const isCurrent = (activeOrg.plan || 'free').toLowerCase() === p.id.toLowerCase();
              const price = billingCycle === 'annual' ? p.price_inr_annual : p.price_inr_monthly;
              const formattedPrice = price === 0 ? 'Free' : `₹${price.toLocaleString()}`;

              return (
                <div
                  key={p.id}
                  className={`relative p-5 rounded-2xl border transition-all flex flex-col justify-between ${
                    isCurrent
                      ? 'bg-amber-500/5 border-amber-500/40 shadow-xl shadow-amber-500/10'
                      : 'bg-slate-950/60 border-slate-800 hover:border-slate-700'
                  }`}
                >
                  {isCurrent && (
                    <div className="absolute -top-3 right-4 px-2.5 py-0.5 rounded-full bg-amber-500 text-slate-950 text-[10px] font-extrabold uppercase tracking-wider shadow">
                      Current Plan
                    </div>
                  )}

                  <div className="space-y-4">
                    <div>
                      <h4 className="text-base font-bold text-white">{p.name}</h4>
                      <div className="mt-2 flex items-baseline gap-1">
                        <span className="text-2xl font-black text-amber-400">{formattedPrice}</span>
                        {price > 0 && (
                          <span className="text-xs text-slate-400">
                            /{billingCycle === 'annual' ? 'yr' : 'mo'}
                          </span>
                        )}
                      </div>
                    </div>

                    <ul className="space-y-2 text-xs text-slate-300">
                      {p.features.map((feat, idx) => (
                        <li key={idx} className="flex items-start gap-2">
                          <Check size={14} className="text-amber-400 mt-0.5 shrink-0" />
                          <span>{feat}</span>
                        </li>
                      ))}
                    </ul>
                  </div>

                  <div className="pt-6">
                    <button
                      onClick={() => handleUpgrade(p.id)}
                      disabled={isCurrent || checkoutLoading === p.id}
                      className={`w-full py-2.5 px-4 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                        isCurrent
                          ? 'bg-slate-800 text-slate-500 cursor-not-allowed border border-slate-700'
                          : 'bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-md shadow-amber-500/20'
                      }`}
                    >
                      {checkoutLoading === p.id ? (
                        'Processing Checkout...'
                      ) : isCurrent ? (
                        'Active Workspace Tier'
                      ) : (
                        `Upgrade to ${p.name}`
                      )}
                    </button>
                  </div>
                </div>
              );
            })}
          </div>
        </div>
      </div>
    </div>
  );
};
