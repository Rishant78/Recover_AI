interface RiskGaugeProps {
  score: number
  level: string
}

export default function RiskGauge({ score, level }: RiskGaugeProps) {
  const radius = 40
  const circumference = 2 * Math.PI * radius
  const progress = (score / 100) * circumference

  const color =
    level === 'high' ? 'var(--accent-red)' :
    level === 'medium' ? 'var(--accent-amber)' :
    level === 'low' ? 'var(--accent-green)' :
    'var(--text-muted)'

  return (
    <div className="risk-gauge">
      <div className="risk-gauge-ring">
        <svg width="100" height="100" viewBox="0 0 100 100">
          <circle
            cx="50" cy="50" r={radius}
            fill="none"
            stroke="var(--border-primary)"
            strokeWidth="6"
          />
          <circle
            cx="50" cy="50" r={radius}
            fill="none"
            stroke={color}
            strokeWidth="6"
            strokeDasharray={circumference}
            strokeDashoffset={circumference - progress}
            strokeLinecap="round"
            style={{ transition: 'stroke-dashoffset 0.8s ease' }}
          />
        </svg>
        <div className="risk-gauge-value" style={{ color }}>
          {score}
        </div>
      </div>
      <div className="risk-gauge-label" style={{ color }}>
        {level === 'none' ? 'No Risk' : `${level} risk`}
      </div>
    </div>
  )
}
