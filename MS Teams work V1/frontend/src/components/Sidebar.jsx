import React from 'react'

export default function Sidebar({ channels, activeChannel, onSelect }) {
  return (
    <aside style={styles.sidebar}>
      <div style={styles.header}>
        <span style={styles.headerTitle}>Chat</span>
        <button style={styles.iconBtn} title="New chat">✏️</button>
      </div>

      <div style={styles.searchBar}>
        <span style={styles.searchIcon}>🔍</span>
        <input
          style={styles.searchInput}
          type="text"
          placeholder="Search"
          readOnly
        />
      </div>

      <div style={styles.sectionLabel}>RECENT</div>

      <ul style={styles.list}>
        {channels.map((ch) => {
          const isActive = ch.id === activeChannel.id
          return (
            <li
              key={ch.id}
              style={{
                ...styles.item,
                ...(isActive ? styles.itemActive : {}),
              }}
              onClick={() => onSelect(ch)}
            >
              <div style={styles.avatarWrap}>
                <div
                  style={{
                    ...styles.avatar,
                    background: ch.type === 'bot' ? 'var(--teams-purple)' : 'var(--teams-purple-dark)',
                  }}
                >
                  {ch.avatar}
                </div>
                {ch.type === 'bot' && <span style={styles.botBadge}>🤖</span>}
              </div>
              <div style={styles.info}>
                <div style={styles.nameRow}>
                  <span style={styles.name}>{ch.name}</span>
                  {ch.unread > 0 && (
                    <span style={styles.unreadDot}>{ch.unread}</span>
                  )}
                </div>
                <span style={styles.subtitle}>{ch.subtitle}</span>
              </div>
            </li>
          )
        })}
      </ul>
    </aside>
  )
}

const styles = {
  sidebar: {
    width: 280,
    background: 'var(--teams-sidebar-bg)',
    display: 'flex',
    flexDirection: 'column',
    flexShrink: 0,
    borderRight: '1px solid #3b3b3b',
    color: '#fff',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '16px 16px 8px',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: 600,
    color: '#fff',
  },
  iconBtn: {
    background: 'transparent',
    border: 'none',
    fontSize: 16,
    cursor: 'pointer',
    padding: 4,
    borderRadius: 4,
  },
  searchBar: {
    display: 'flex',
    alignItems: 'center',
    margin: '4px 12px 8px',
    background: '#3b3b3b',
    borderRadius: 6,
    padding: '6px 10px',
    gap: 8,
  },
  searchIcon: { fontSize: 13, opacity: 0.7 },
  searchInput: {
    background: 'transparent',
    border: 'none',
    outline: 'none',
    color: '#ccc',
    fontSize: 13,
    flex: 1,
  },
  sectionLabel: {
    fontSize: 10,
    fontWeight: 600,
    color: '#888',
    letterSpacing: 0.8,
    padding: '4px 16px 6px',
  },
  list: {
    listStyle: 'none',
    overflowY: 'auto',
    flex: 1,
  },
  item: {
    display: 'flex',
    alignItems: 'center',
    gap: 12,
    padding: '10px 14px',
    cursor: 'pointer',
    borderRadius: 6,
    margin: '1px 6px',
    transition: 'background 0.12s',
  },
  itemActive: {
    background: 'var(--teams-active)',
  },
  avatarWrap: {
    position: 'relative',
    flexShrink: 0,
  },
  avatar: {
    width: 40,
    height: 40,
    borderRadius: '50%',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 13,
    fontWeight: 700,
    color: '#fff',
  },
  botBadge: {
    position: 'absolute',
    bottom: -2,
    right: -2,
    fontSize: 12,
    background: '#1f1f1f',
    borderRadius: '50%',
    lineHeight: 1,
  },
  info: {
    flex: 1,
    minWidth: 0,
  },
  nameRow: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  name: {
    fontSize: 13,
    fontWeight: 600,
    color: '#fff',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    maxWidth: 160,
  },
  subtitle: {
    fontSize: 11,
    color: '#aaa',
    whiteSpace: 'nowrap',
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    display: 'block',
    marginTop: 2,
  },
  unreadDot: {
    background: 'var(--teams-purple)',
    color: '#fff',
    fontSize: 10,
    fontWeight: 700,
    borderRadius: 10,
    padding: '1px 5px',
    minWidth: 18,
    textAlign: 'center',
  },
}
