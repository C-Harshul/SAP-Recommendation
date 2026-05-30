import React, { useState } from 'react'

export default function JsonPanel({ payload }) {
  const [copied, setCopied] = useState(false)

  function copyToClipboard() {
    navigator.clipboard.writeText(JSON.stringify(payload?.payload, null, 2))
    setCopied(true)
    setTimeout(() => setCopied(false), 2000)
  }

  return (
    <aside style={styles.panel}>
      <div style={styles.panelHeader}>
        <div style={styles.headerLeft}>
          <span style={styles.headerIcon}>🗂️</span>
          <div>
            <div style={styles.headerTitle}>Mock S3 Payload</div>
            <div style={styles.headerSubtitle}>community-requests / raw</div>
          </div>
        </div>
        {payload && (
          <button style={styles.copyBtn} onClick={copyToClipboard}>
            {copied ? '✓ Copied' : '📋 Copy'}
          </button>
        )}
      </div>

      {!payload ? (
        <div style={styles.empty}>
          <div style={styles.emptyIcon}>📭</div>
          <div style={styles.emptyTitle}>No submission yet</div>
          <div style={styles.emptyText}>
            Submit a request through the bot chat to see the generated JSON object here.
          </div>
        </div>
      ) : (
        <div style={styles.content}>
          {/* Metadata strip */}
          <div style={styles.metaStrip}>
            <MetaChip label="ID" value={payload.request_id} accent />
            <MetaChip label="Status" value="new" />
            <MetaChip
              label="Interview"
              value={payload.payload?.interview_opt_in ? 'Opted in ✓' : 'No'}
              success={payload.payload?.interview_opt_in}
            />
          </div>

          {/* S3 path */}
          <div style={styles.s3Path}>
            <span style={styles.s3Label}>Saved to</span>
            <code style={styles.s3Code}>{payload.mock_s3_path}</code>
          </div>

          {/* Raw JSON */}
          <div style={styles.jsonWrap}>
            <pre style={styles.json}>
              {JSON.stringify(payload.payload, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </aside>
  )
}

function MetaChip({ label, value, accent, success }) {
  const bg = accent
    ? 'var(--teams-purple)'
    : success
    ? 'var(--success-green)'
    : '#6c6c6c'
  return (
    <div style={{ ...styles.chip, background: bg }}>
      <span style={styles.chipLabel}>{label}</span>
      <span style={styles.chipValue}>{value}</span>
    </div>
  )
}

const styles = {
  panel: {
    width: 360,
    flexShrink: 0,
    background: '#1e1e2e',
    borderLeft: '1px solid #2e2e4e',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
  },
  panelHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: '14px 16px',
    borderBottom: '1px solid #2e2e4e',
    background: '#16162a',
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 10,
  },
  headerIcon: {
    fontSize: 20,
  },
  headerTitle: {
    fontSize: 13,
    fontWeight: 700,
    color: '#e0e0f0',
  },
  headerSubtitle: {
    fontSize: 10,
    color: '#7070a0',
    marginTop: 1,
  },
  copyBtn: {
    padding: '4px 10px',
    border: '1px solid #4040a0',
    borderRadius: 4,
    background: 'transparent',
    color: '#a0a0e0',
    fontSize: 11,
    cursor: 'pointer',
  },
  empty: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    padding: 32,
    gap: 12,
  },
  emptyIcon: {
    fontSize: 40,
    opacity: 0.4,
  },
  emptyTitle: {
    fontSize: 14,
    fontWeight: 600,
    color: '#6060a0',
  },
  emptyText: {
    fontSize: 12,
    color: '#4a4a80',
    textAlign: 'center',
    lineHeight: 1.5,
  },
  content: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    padding: '12px 14px 0',
    gap: 10,
  },
  metaStrip: {
    display: 'flex',
    gap: 6,
    flexWrap: 'wrap',
  },
  chip: {
    display: 'flex',
    gap: 5,
    alignItems: 'center',
    padding: '3px 8px',
    borderRadius: 12,
    fontSize: 11,
  },
  chipLabel: {
    color: 'rgba(255,255,255,0.65)',
    fontWeight: 500,
  },
  chipValue: {
    color: '#fff',
    fontWeight: 700,
  },
  s3Path: {
    display: 'flex',
    flexDirection: 'column',
    gap: 3,
  },
  s3Label: {
    fontSize: 10,
    color: '#6060a0',
    textTransform: 'uppercase',
    letterSpacing: 0.5,
    fontWeight: 600,
  },
  s3Code: {
    fontSize: 11,
    color: '#90d0a0',
    background: '#0e1a14',
    padding: '5px 8px',
    borderRadius: 4,
    fontFamily: 'monospace',
    wordBreak: 'break-all',
  },
  jsonWrap: {
    flex: 1,
    overflowY: 'auto',
    background: '#0d0d1a',
    borderRadius: 6,
    marginBottom: 12,
  },
  json: {
    fontSize: 11,
    color: '#a0e0c0',
    fontFamily: 'monospace',
    lineHeight: 1.6,
    padding: '12px 14px',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
}
