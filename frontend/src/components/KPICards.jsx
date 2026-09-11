import React from 'react';
import { 
  Wallet, 
  TrendingUp, 
  TrendingDown, 
  PiggyBank, 
  ShieldAlert, 
  Activity, 
  CreditCard 
} from 'lucide-react';

export default function KPICards({ summary, health, runway, debt }) {
  const sym = "₹";

  const cards = [
    {
      title: "Current Balance",
      value: `${sym}${(summary?.accounts?.[0]?.balance ?? 0).toLocaleString()}`,
      subtitle: summary?.accounts?.[0]?.bank || "No account available",
      icon: Wallet,
      color: "var(--accent-primary)",
      badge: "Active",
      badgeType: "badge-info"
    },
    {
      title: "Monthly Income",
      value: `${sym}${(summary?.income ?? 0).toLocaleString()}`,
      subtitle: "Current reporting month",
      icon: TrendingUp,
      color: "var(--accent-success)",
      badge: "Received",
      badgeType: "badge-success"
    },
    {
      title: "Monthly Expenses",
      value: `${sym}${(summary?.expenses ?? 0).toLocaleString()}`,
      subtitle: `Top: ${summary?.top_expense_category || 'None'}`,
      icon: TrendingDown,
      color: "var(--accent-danger)",
      badge: `${summary?.savings_rate ?? 0}% Saved`,
      badgeType: "badge-warning"
    },
    {
      title: "Savings Rate",
      value: `${summary?.savings_rate ?? 0}%`,
      subtitle: `Net Savings: ${sym}${(summary?.savings ?? 0).toLocaleString()}`,
      icon: PiggyBank,
      color: "var(--accent-secondary)",
      badge: (summary?.savings_rate ?? 0) >= 20 ? "Optimal (>20%)" : "Low",
      badgeType: (summary?.savings_rate ?? 0) >= 20 ? "badge-success" : "badge-warning"
    },
    {
      title: "Emergency Runway",
      value: `${runway?.runway_months ?? 0} mo`,
      subtitle: `Req: ${sym}${(summary?.recommended_emergency_fund ?? 0).toLocaleString()}`,
      icon: ShieldAlert,
      color: "var(--accent-warning)",
      badge: runway?.status || "INSUFFICIENT",
      badgeType: (runway?.runway_months ?? 0) >= 3 ? "badge-success" : "badge-warning"
    },
    {
      title: "Debt-to-Income (DTI)",
      value: `${summary?.dti_ratio ?? 0}%`,
      subtitle: `EMI: ${sym}${(debt?.monthly_emi ?? 0).toLocaleString()}/mo`,
      icon: CreditCard,
      color: "var(--accent-purple)",
      badge: (summary?.dti_ratio ?? 0) <= 20 ? "Healthy (<20%)" : "High Burden",
      badgeType: (summary?.dti_ratio ?? 0) <= 20 ? "badge-success" : "badge-danger"
    },
    {
      title: "Financial Health Score",
      value: `${summary?.health_score ?? 0}/100`,
      subtitle: `Grade ${summary?.health_grade || '-'} Standing`,
      icon: Activity,
      color: "var(--accent-primary)",
      badge: `Grade ${summary?.health_grade || '-'}`,
      badgeType: "badge-success"
    }
  ];

  return (
    <div style={{
      display: 'grid',
      gridTemplateColumns: 'repeat(auto-fit, minmax(240px, 1fr))',
      gap: '16px',
      marginBottom: '28px'
    }}>
      {cards.map((card, idx) => {
        const IconComponent = card.icon;
        return (
          <div key={idx} className="glass-card" style={{ padding: '20px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '12px' }}>
              <div style={{
                width: '40px',
                height: '40px',
                borderRadius: '10px',
                background: `rgba(99, 102, 241, 0.12)`,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                color: card.color
              }}>
                <IconComponent size={20} />
              </div>
              <span className={`badge ${card.badgeType}`}>{card.badge}</span>
            </div>
            <div style={{ fontSize: '0.85rem', color: 'var(--text-muted)', marginBottom: '4px' }}>
              {card.title}
            </div>
            <div style={{ fontSize: '1.6rem', fontWeight: '700', color: 'var(--text-main)', marginBottom: '6px' }}>
              {card.value}
            </div>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-dim)' }}>
              {card.subtitle}
            </div>
          </div>
        );
      })}
    </div>
  );
}
