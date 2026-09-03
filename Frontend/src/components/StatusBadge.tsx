interface StatusBadgeProps {
  status: string
}

export default function StatusBadge({ status }: StatusBadgeProps) {
  const s = status.toLowerCase()
  let color = 'var(--text-muted)'
  if (s === 'recovered' || s === 'successful') color = 'var(--accent-green)'
  else if (s === 'escalated' || s === 'abandoned' || s === 'overdue') color = 'var(--accent-amber)'
  else if (s === 'blocked' || s === 'failed') color = 'var(--accent-red)'
  else if (s === 'open') color = 'var(--accent-blue)'

  return (
    <span className="status-badge" style={{ color }}>
      <span className="status-indicator" style={{ background: color }} />
      {status.toUpperCase()}
    </span>
  )
}
