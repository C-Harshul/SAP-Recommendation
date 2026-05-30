import React from 'react'

const NAV_ITEMS = [
  { icon: '💬', label: 'Chat', active: true },
  { icon: '👥', label: 'Teams' },
  { icon: '📅', label: 'Calendar' },
  { icon: '📞', label: 'Calls' },
  { icon: '📁', label: 'Files' },
]

export default function NavRail() {
  return (
    <nav style={styles.rail}>
      {/* App logo / wordmark area */}
      <div style={styles.logoArea}>
        <div style={styles.logoMark}>EG</div>
      </div>

      <div style={styles.divider} />

      {NAV_ITEMS.map((item) => (
        <button
          key={item.label}
          style={{
            ...styles.navBtn,
            ...(item.active ? styles.navBtnActive : {}),
          }}
          title={item.label}
        >
          <span style={styles.navIcon}>{item.icon}</span>
          <span style={styles.navLabel}>{item.label}</span>
        </button>
      ))}

      {/* Bottom avatar */}
      <div style={styles.avatarArea}>
        <div style={styles.avatar}>SU</div>
      </div>
    </nav>
  )
}

const styles = {
  rail: {
    width: 68,
    background: 'var(--teams-nav-bg)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    paddingTop: 8,
    paddingBottom: 12,
    flexShrink: 0,
    gap: 2,
  },
  logoArea: {
    marginBottom: 8,
    paddingBottom: 4,
  },
  logoMark: {
    width: 36,
    height: 36,
    borderRadius: 8,
    background: 'var(--teams-purple)',
    color: '#fff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontWeight: 700,
    fontSize: 13,
    letterSpacing: 0.5,
  },
  divider: {
    width: 40,
    height: 1,
    background: '#3b3b3b',
    margin: '4px 0 8px',
  },
  navBtn: {
    width: 56,
    minHeight: 52,
    background: 'transparent',
    border: 'none',
    borderRadius: 8,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 3,
    color: '#bbb',
    transition: 'background 0.15s, color 0.15s',
    padding: '6px 4px',
  },
  navBtnActive: {
    background: 'var(--teams-hover)',
    color: '#fff',
  },
  navIcon: {
    fontSize: 18,
    lineHeight: 1,
  },
  navLabel: {
    fontSize: 9,
    fontWeight: 500,
    letterSpacing: 0.2,
  },
  avatarArea: {
    marginTop: 'auto',
  },
  avatar: {
    width: 32,
    height: 32,
    borderRadius: '50%',
    background: 'var(--teams-purple)',
    color: '#fff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 11,
    fontWeight: 600,
  },
}
