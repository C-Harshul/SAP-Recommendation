import React, { useState, useRef, useEffect } from 'react'
import AdaptiveCardForm from './AdaptiveCardForm.jsx'

/**
 * REAL TEAMS INTEGRATION NOTE:
 * In a real Teams bot, this entire component is replaced by:
 * - The Teams client chat UI (provided by Microsoft)
 * - A Bot Framework Activity handler that sends Adaptive Cards and processes Action.Submit
 * - The conversation flow (bot turns) maps directly to this component's `messages` state shape
 *
 * Porting guide:
 * 1. PERSONAL BOT flow → implement in bot's onMessage() handler
 * 2. BUSINESS UNIT flow → implement as a Message Extension / Action command
 * 3. AdaptiveCardForm → replace with the JSON in backend/adaptive-cards/community-request-card.json
 */

// ─── Seed messages for each channel ───────────────────────────────────────────

const PERSONAL_BOT_SEED = [
  {
    id: 'bot-0',
    role: 'bot',
    type: 'text',
    text: "Hi! I'm the Experience Garage bot. Share any feature idea or product request and I'll capture it for the product team. 💡",
    ts: relativeTs(-120),
  },
]

const BUSINESS_UNIT_SEED = [
  {
    id: 'bu-0',
    role: 'user',
    displayName: 'Priya R.',
    avatar: 'PR',
    type: 'text',
    text: 'Has anyone tried the new Data Challenges section? The dataset variety is great.',
    ts: relativeTs(-600),
  },
  {
    id: 'bu-1',
    role: 'user',
    displayName: 'James L.',
    avatar: 'JL',
    type: 'text',
    text: 'Yes! Though I keep wishing there was a leaderboard to see how others are approaching the same challenge.',
    ts: relativeTs(-540),
  },
  {
    id: 'bu-2',
    role: 'user',
    displayName: 'Fatima K.',
    avatar: 'FK',
    type: 'text',
    text: 'The ML Workbench is useful, but I wish there was a guided no-code path for business users.',
    ts: relativeTs(-300),
    submittable: true,
    prefill: {
      raw_request: 'The ML Workbench is useful, but I wish there was a guided no-code path for business users.',
      cleaned_request: 'Introduce a no-code guided workflow in ML Workbench for non-technical users',
      problem: 'Business users feel excluded from ML Workbench due to its technical complexity',
      desired_outcome: 'Ability for non-technical stakeholders to build and run simple ML experiments',
      feature_category: 'ML Tooling',
      capability_area: 'ML Workbench',
      affected_workflow: 'ML Workbench',
      urgency: 'Important',
      frequency: 'Daily',
    },
  },
  {
    id: 'bu-3',
    role: 'user',
    displayName: 'Carlos M.',
    avatar: 'CM',
    type: 'text',
    text: '+1 on that. A wizard-style approach would help our business analysts a lot.',
    ts: relativeTs(-240),
  },
]

function relativeTs(offsetSeconds) {
  return new Date(Date.now() + offsetSeconds * 1000).toISOString()
}

function formatTime(isoString) {
  return new Date(isoString).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
}

// ─── Component ─────────────────────────────────────────────────────────────────

export default function ChatWindow({ channel, onSubmitSuccess }) {
  const isBot = channel.id === 'personal-bot'

  const [messages, setMessages] = useState(
    isBot ? PERSONAL_BOT_SEED : BUSINESS_UNIT_SEED
  )
  const [inputText, setInputText] = useState('')
  const [showFormForId, setShowFormForId] = useState(null)
  const [hoveredMsgId, setHoveredMsgId] = useState(null)
  const [showMenuFor, setShowMenuFor] = useState(null)
  const [confirmedRequests, setConfirmedRequests] = useState({})

  const bottomRef = useRef(null)
  const inputRef = useRef(null)

  // Reset when channel changes
  useEffect(() => {
    setMessages(isBot ? PERSONAL_BOT_SEED : BUSINESS_UNIT_SEED)
    setInputText('')
    setShowFormForId(null)
    setShowMenuFor(null)
    setConfirmedRequests({})
  }, [channel.id])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, showFormForId])

  function sendUserMessage() {
    if (!inputText.trim()) return
    const userMsg = {
      id: `user-${Date.now()}`,
      role: 'user',
      type: 'text',
      text: inputText.trim(),
      ts: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMsg])
    setInputText('')

    // Bot processes the message after a short delay
    setTimeout(() => {
      const botMsg = {
        id: `bot-${Date.now()}`,
        role: 'bot',
        type: 'card-prompt',
        userText: userMsg.text,
        cleanedRequest: deriveCleaned(userMsg.text),
        ts: new Date().toISOString(),
      }
      setMessages((prev) => [...prev, botMsg])
    }, 800)
  }

  function deriveCleaned(text) {
    // In production this would call an NLP step in the bot handler.
    // Here we produce a plausible cleaned version for demo purposes.
    const lower = text.toLowerCase()
    if (lower.includes('podcast') || lower.includes('audio'))
      return 'Add podcast/audio mode for learning content'
    if (lower.includes('no-code') || lower.includes('nocode') || lower.includes('wizard'))
      return 'Introduce a no-code guided workflow for business users'
    if (lower.includes('bookmark') || lower.includes('favorite') || lower.includes('save'))
      return 'Add bookmarking / favorites for datasets and content'
    if (lower.includes('leaderboard') || lower.includes('ranking'))
      return 'Add a community leaderboard to Data Challenges'
    if (lower.includes('dark mode') || lower.includes('theme'))
      return 'Add dark mode / theme support to the platform'
    // Generic fallback
    const trimmed = text.replace(/[.!?,]+$/, '').trim()
    return trimmed.charAt(0).toUpperCase() + trimmed.slice(1)
  }

  function handleOpenForm(msgId) {
    setShowFormForId((prev) => (prev === msgId ? null : msgId))
    setShowMenuFor(null)
  }

  function handleFormSubmit(msgId, data) {
    setShowFormForId(null)
    setConfirmedRequests((prev) => ({ ...prev, [msgId]: data }))
    onSubmitSuccess(data)

    // Add bot confirmation message
    const confirmation = {
      id: `confirm-${Date.now()}`,
      role: 'bot',
      type: 'confirmation',
      requestId: data.request_id,
      interviewOptIn: data.payload?.interview_opt_in,
      ts: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, confirmation])
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendUserMessage()
    }
  }

  return (
    <div style={styles.window}>
      {/* Header */}
      <div style={styles.header}>
        <div style={styles.headerAvatar}>
          <div
            style={{
              ...styles.headerAvatarInner,
              background: isBot ? 'var(--teams-purple)' : 'var(--teams-purple-dark)',
            }}
          >
            {channel.avatar}
          </div>
          {isBot && <span style={styles.botBadge}>🤖</span>}
        </div>
        <div style={styles.headerInfo}>
          <div style={styles.headerName}>{channel.name}</div>
          <div style={styles.headerSub}>{channel.subtitle}</div>
        </div>
        <div style={styles.headerActions}>
          <button style={styles.headerBtn} title="Search">🔍</button>
          <button style={styles.headerBtn} title="Video call">📹</button>
          <button style={styles.headerBtn} title="More">⋯</button>
        </div>
      </div>

      {/* Demo mode banner */}
      <div style={styles.demoBanner}>
        <span style={styles.demoBadge}>DEMO</span>
        {isBot
          ? 'Flow 1 – Personal Teams Bot: type a feature idea below to trigger the bot capture flow.'
          : 'Flow 2 – Business Unit Chat: hover over Fatima\'s message and click ⋯ → "Submit to Experience Garage."'}
      </div>

      {/* Messages */}
      <div style={styles.messages}>
        {messages.map((msg) => (
          <MessageRow
            key={msg.id}
            msg={msg}
            isBot={isBot}
            hoveredMsgId={hoveredMsgId}
            showMenuFor={showMenuFor}
            showFormForId={showFormForId}
            confirmedRequests={confirmedRequests}
            onHover={setHoveredMsgId}
            onMenuToggle={setShowMenuFor}
            onOpenForm={handleOpenForm}
            onFormSubmit={(data) => handleFormSubmit(msg.id, data)}
            onFormCancel={() => setShowFormForId(null)}
            channel={channel}
          />
        ))}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      {isBot && (
        <div style={styles.inputArea}>
          <div style={styles.inputWrap}>
            <input
              ref={inputRef}
              style={styles.input}
              value={inputText}
              onChange={(e) => setInputText(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Message ${channel.name}…`}
            />
            <div style={styles.inputActions}>
              <button style={styles.inputBtn} title="Attach">📎</button>
              <button style={styles.inputBtn} title="Emoji">😊</button>
              <button
                style={{
                  ...styles.sendBtn,
                  opacity: inputText.trim() ? 1 : 0.4,
                }}
                onClick={sendUserMessage}
                disabled={!inputText.trim()}
              >
                ➤
              </button>
            </div>
          </div>
        </div>
      )}

      {!isBot && (
        <div style={styles.readonlyBar}>
          <span style={styles.readonlyText}>
            💡 This channel view is read-only in the demo. Hover over Fatima's message to submit it.
          </span>
        </div>
      )}
    </div>
  )
}

// ─── Individual message row ────────────────────────────────────────────────────

function MessageRow({
  msg,
  isBot,
  hoveredMsgId,
  showMenuFor,
  showFormForId,
  confirmedRequests,
  onHover,
  onMenuToggle,
  onOpenForm,
  onFormSubmit,
  onFormCancel,
  channel,
}) {
  const isHovered = hoveredMsgId === msg.id
  const menuOpen = showMenuFor === msg.id
  const formOpen = showFormForId === msg.id
  const confirmed = confirmedRequests[msg.id]

  // ── Bot confirmation bubble ──
  if (msg.type === 'confirmation') {
    return (
      <div style={styles.botRow}>
        <BotAvatar />
        <div style={styles.botBubbleWrap}>
          <div style={styles.msgMeta}>Experience Garage Bot · {formatTime(msg.ts)}</div>
          <div style={{ ...styles.bubble, ...styles.confirmBubble }}>
            <div style={styles.confirmTitle}>
              ✅ Request <strong>{msg.requestId}</strong> has been saved successfully.
            </div>
            <div style={styles.confirmDetail}>
              <ConfirmRow label="Source" value="Teams Bot" />
              <ConfirmRow
                label="Interview opt-in"
                value={msg.interviewOptIn ? 'Yes ✓' : 'No'}
                success={msg.interviewOptIn}
              />
              <ConfirmRow label="Status" value="Added to Community Requests dataset" />
            </div>
          </div>
        </div>
      </div>
    )
  }

  // ── Bot card-prompt bubble ──
  if (msg.type === 'card-prompt') {
    return (
      <div style={styles.botRow}>
        <BotAvatar />
        <div style={styles.botBubbleWrap}>
          <div style={styles.msgMeta}>Experience Garage Bot · {formatTime(msg.ts)}</div>
          <div style={{ ...styles.bubble, ...styles.botBubble }}>
            I captured this as a possible feature request:{' '}
            <strong>"{msg.cleanedRequest}"</strong>
            <br />
            <span style={{ fontSize: 12, color: '#555', display: 'block', marginTop: 4 }}>
              Want to add more details and submit it to the product team?
            </span>
          </div>
          {!confirmed && (
            <button
              style={styles.openFormBtn}
              onClick={() => onOpenForm(msg.id)}
            >
              {formOpen ? '✕ Close form' : '📋 Fill out request form'}
            </button>
          )}
          {formOpen && !confirmed && (
            <AdaptiveCardForm
              prefill={{ raw_request: msg.userText, cleaned_request: msg.cleanedRequest }}
              entryPoint="personal_bot"
              onSubmit={onFormSubmit}
              onCancel={onFormCancel}
            />
          )}
        </div>
      </div>
    )
  }

  // ── Bot plain text ──
  if (msg.role === 'bot') {
    return (
      <div style={styles.botRow}>
        <BotAvatar />
        <div style={styles.botBubbleWrap}>
          <div style={styles.msgMeta}>Experience Garage Bot · {formatTime(msg.ts)}</div>
          <div style={{ ...styles.bubble, ...styles.botBubble }}>{msg.text}</div>
        </div>
      </div>
    )
  }

  // ── User message (own) ──
  if (msg.role === 'user' && !msg.displayName) {
    return (
      <div style={styles.userRow}>
        <div style={styles.userBubbleWrap}>
          <div style={{ ...styles.msgMeta, textAlign: 'right' }}>
            You · {formatTime(msg.ts)}
          </div>
          <div style={{ ...styles.bubble, ...styles.userBubble }}>{msg.text}</div>
        </div>
        <div style={styles.userAvatarSmall}>SU</div>
      </div>
    )
  }

  // ── Business Unit team member message ──
  const avatarColor = {
    PR: '#0078d4',
    JL: '#107c10',
    FK: '#d83b01',
    CM: '#5c2d91',
  }[msg.avatar] || 'var(--teams-purple)'

  return (
    <div
      style={{ ...styles.teamRow, background: isHovered ? '#f0f0f8' : 'transparent' }}
      onMouseEnter={() => onHover(msg.id)}
      onMouseLeave={() => { onHover(null); if (!menuOpen) onMenuToggle(null) }}
    >
      {/* Avatar */}
      <div style={{ ...styles.teamAvatar, background: avatarColor }}>
        {msg.avatar}
      </div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={styles.msgMeta}>
          <strong>{msg.displayName}</strong> · {formatTime(msg.ts)}
        </div>
        <div style={styles.teamBubble}>{msg.text}</div>

        {/* Reactions strip */}
        {isHovered && (
          <div style={styles.reactionBar}>
            <button style={styles.reactBtn} title="React">😊 +</button>
            <button style={styles.reactBtn} title="Reply">↩ Reply</button>
            <button style={styles.reactBtn} title="Forward">↗</button>
            <div style={styles.menuWrap}>
              <button
                style={{ ...styles.reactBtn, ...(menuOpen ? styles.reactBtnActive : {}) }}
                title="More actions"
                onClick={(e) => { e.stopPropagation(); onMenuToggle(menuOpen ? null : msg.id) }}
              >
                ⋯
              </button>
              {menuOpen && (
                <div style={styles.dropdown}>
                  <button style={styles.dropdownItem} onClick={() => {}}>
                    📌 Pin message
                  </button>
                  <button style={styles.dropdownItem} onClick={() => {}}>
                    🔗 Copy link
                  </button>
                  {msg.submittable && (
                    <>
                      <div style={styles.dropdownDivider} />
                      <button
                        style={{ ...styles.dropdownItem, ...styles.dropdownHighlight }}
                        onClick={() => onOpenForm(msg.id)}
                      >
                        ⚡ Submit to Experience Garage
                      </button>
                    </>
                  )}
                </div>
              )}
            </div>
          </div>
        )}

        {/* Form (expanded inline) */}
        {formOpen && !confirmed && (
          <div style={{ marginTop: 10 }}>
            <AdaptiveCardForm
              prefill={msg.prefill || { raw_request: msg.text }}
              entryPoint="business_unit_chat"
              onSubmit={onFormSubmit}
              onCancel={onFormCancel}
            />
          </div>
        )}
      </div>
    </div>
  )
}

function BotAvatar() {
  return (
    <div style={styles.botAvatar}>
      <div style={styles.botAvatarInner}>EG</div>
      <span style={styles.botBadgeSm}>🤖</span>
    </div>
  )
}

function ConfirmRow({ label, value, success }) {
  return (
    <div style={styles.confirmRow}>
      <span style={styles.confirmLabel}>{label}:</span>
      <span style={{ ...styles.confirmValue, color: success ? 'var(--success-green)' : undefined }}>
        {value}
      </span>
    </div>
  )
}

const styles = {
  window: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    background: '#fff',
    overflow: 'hidden',
  },
  header: {
    display: 'flex',
    alignItems: 'center',
    padding: '10px 16px',
    borderBottom: '1px solid var(--teams-border)',
    background: '#fff',
    gap: 10,
    flexShrink: 0,
  },
  headerAvatar: { position: 'relative', flexShrink: 0 },
  headerAvatarInner: {
    width: 36,
    height: 36,
    borderRadius: '50%',
    color: '#fff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 12,
    fontWeight: 700,
  },
  botBadge: { position: 'absolute', bottom: -2, right: -2, fontSize: 12 },
  headerInfo: { flex: 1 },
  headerName: { fontSize: 14, fontWeight: 700, color: 'var(--teams-text-primary)' },
  headerSub: { fontSize: 11, color: 'var(--teams-text-muted)' },
  headerActions: { display: 'flex', gap: 4 },
  headerBtn: {
    background: 'transparent',
    border: 'none',
    fontSize: 16,
    padding: '4px 8px',
    borderRadius: 4,
    cursor: 'pointer',
    color: '#555',
  },
  demoBanner: {
    background: '#fffbe6',
    borderBottom: '1px solid #ffe58f',
    padding: '6px 16px',
    fontSize: 12,
    color: '#7a5800',
    display: 'flex',
    alignItems: 'center',
    gap: 8,
    flexShrink: 0,
  },
  demoBadge: {
    background: 'var(--sap-gold)',
    color: '#1f1f1f',
    fontSize: 9,
    fontWeight: 800,
    letterSpacing: 1,
    padding: '2px 6px',
    borderRadius: 3,
    flexShrink: 0,
  },
  messages: {
    flex: 1,
    overflowY: 'auto',
    padding: '16px 0 8px',
    display: 'flex',
    flexDirection: 'column',
    gap: 2,
  },

  // Bot messages
  botRow: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 10,
    padding: '6px 16px',
  },
  botBubbleWrap: { flex: 1, maxWidth: 660 },
  botAvatar: { position: 'relative', flexShrink: 0 },
  botAvatarInner: {
    width: 36,
    height: 36,
    borderRadius: '50%',
    background: 'var(--teams-purple)',
    color: '#fff',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    fontSize: 11,
    fontWeight: 700,
  },
  botBadgeSm: { position: 'absolute', bottom: -2, right: -2, fontSize: 11 },
  bubble: {
    display: 'inline-block',
    padding: '8px 12px',
    borderRadius: 8,
    fontSize: 13,
    lineHeight: 1.5,
    maxWidth: '100%',
  },
  botBubble: {
    background: '#f5f5f5',
    color: 'var(--teams-text-primary)',
    borderTopLeftRadius: 2,
  },

  // User (self) messages
  userRow: {
    display: 'flex',
    alignItems: 'flex-start',
    justifyContent: 'flex-end',
    gap: 10,
    padding: '6px 16px',
  },
  userBubbleWrap: { maxWidth: 480 },
  userBubble: {
    background: 'var(--teams-purple-light)',
    color: 'var(--teams-text-primary)',
    borderTopRightRadius: 2,
    display: 'block',
  },
  userAvatarSmall: {
    width: 28,
    height: 28,
    borderRadius: '50%',
    background: 'var(--teams-purple)',
    color: '#fff',
    fontSize: 10,
    fontWeight: 700,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    marginTop: 18,
  },

  // Business unit messages
  teamRow: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: 10,
    padding: '6px 16px',
    borderRadius: 4,
    position: 'relative',
    transition: 'background 0.1s',
  },
  teamAvatar: {
    width: 36,
    height: 36,
    borderRadius: '50%',
    color: '#fff',
    fontSize: 12,
    fontWeight: 700,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
    marginTop: 2,
  },
  teamBubble: {
    fontSize: 13,
    lineHeight: 1.5,
    color: 'var(--teams-text-primary)',
  },

  // Shared meta
  msgMeta: {
    fontSize: 11,
    color: 'var(--teams-text-muted)',
    marginBottom: 3,
  },

  // Reaction bar (hover actions)
  reactionBar: {
    display: 'flex',
    alignItems: 'center',
    gap: 2,
    marginTop: 4,
  },
  reactBtn: {
    background: '#fff',
    border: '1px solid #e0e0e0',
    borderRadius: 4,
    padding: '2px 8px',
    fontSize: 12,
    color: '#555',
    cursor: 'pointer',
    boxShadow: '0 1px 3px rgba(0,0,0,0.08)',
  },
  reactBtnActive: {
    background: 'var(--teams-purple-light)',
    borderColor: 'var(--teams-purple)',
    color: 'var(--teams-purple)',
  },
  menuWrap: { position: 'relative' },
  dropdown: {
    position: 'absolute',
    top: '110%',
    right: 0,
    background: '#fff',
    border: '1px solid var(--teams-border)',
    borderRadius: 6,
    boxShadow: '0 4px 16px rgba(0,0,0,0.14)',
    zIndex: 100,
    minWidth: 220,
    overflow: 'hidden',
  },
  dropdownItem: {
    display: 'block',
    width: '100%',
    padding: '9px 14px',
    background: 'transparent',
    border: 'none',
    textAlign: 'left',
    fontSize: 13,
    color: '#333',
    cursor: 'pointer',
  },
  dropdownHighlight: {
    color: 'var(--teams-purple)',
    fontWeight: 600,
    background: 'var(--teams-purple-light)',
  },
  dropdownDivider: {
    height: 1,
    background: '#eee',
    margin: '3px 0',
  },

  // Open form button (personal bot flow)
  openFormBtn: {
    marginTop: 8,
    padding: '6px 14px',
    background: 'var(--teams-purple)',
    border: 'none',
    borderRadius: 4,
    color: '#fff',
    fontSize: 12,
    fontWeight: 600,
    cursor: 'pointer',
    display: 'inline-block',
  },

  // Confirmation bubble
  confirmBubble: {
    background: '#f0faf0',
    border: '1px solid #c3e6c3',
    display: 'block',
    borderTopLeftRadius: 2,
  },
  confirmTitle: {
    fontSize: 13,
    marginBottom: 8,
  },
  confirmDetail: {
    borderTop: '1px solid #d0ead0',
    paddingTop: 8,
    display: 'flex',
    flexDirection: 'column',
    gap: 4,
  },
  confirmRow: {
    display: 'flex',
    gap: 8,
    fontSize: 12,
  },
  confirmLabel: {
    color: '#666',
    minWidth: 110,
  },
  confirmValue: {
    fontWeight: 600,
    color: '#222',
  },

  // Input bar
  inputArea: {
    borderTop: '1px solid var(--teams-border)',
    padding: '10px 16px',
    background: '#fff',
    flexShrink: 0,
  },
  inputWrap: {
    display: 'flex',
    alignItems: 'center',
    border: '1px solid #c8c8c8',
    borderRadius: 6,
    overflow: 'hidden',
    background: '#fafafa',
  },
  input: {
    flex: 1,
    padding: '9px 12px',
    border: 'none',
    outline: 'none',
    fontSize: 13,
    background: 'transparent',
  },
  inputActions: {
    display: 'flex',
    alignItems: 'center',
    paddingRight: 6,
    gap: 2,
  },
  inputBtn: {
    background: 'transparent',
    border: 'none',
    fontSize: 15,
    padding: 5,
    cursor: 'pointer',
    borderRadius: 4,
    color: '#666',
  },
  sendBtn: {
    background: 'var(--teams-purple)',
    border: 'none',
    borderRadius: 4,
    color: '#fff',
    padding: '5px 10px',
    fontSize: 14,
    cursor: 'pointer',
    transition: 'opacity 0.15s',
  },

  // Read-only bar
  readonlyBar: {
    borderTop: '1px solid var(--teams-border)',
    padding: '10px 16px',
    background: '#f9f9f9',
    flexShrink: 0,
  },
  readonlyText: {
    fontSize: 12,
    color: '#888',
  },
}
