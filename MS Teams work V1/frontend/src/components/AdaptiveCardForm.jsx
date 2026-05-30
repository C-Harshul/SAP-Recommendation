import React, { useState } from 'react'

/**
 * REAL TEAMS INTEGRATION NOTE:
 * This component simulates a Teams Adaptive Card rendered as a custom React form.
 * In production, replace this component with the JSON payload from
 * backend/adaptive-cards/community-request-card.json submitted via the Bot Framework SDK.
 * The field IDs and shape of `formData` match the Adaptive Card input IDs exactly.
 */

const WORKFLOW_OPTIONS = [
  'Experience Garage mission learning',
  'ML Workbench',
  'Data Challenges',
  'AI Prototyping Lab',
  'Platform Navigation',
  'Content Delivery',
  'Collaboration',
  'Other',
]

const ROLE_OPTIONS = [
  { label: 'Data Analyst', value: 'data analyst' },
  { label: 'Product Manager', value: 'product manager' },
  { label: 'Developer', value: 'developer' },
  { label: 'Business User', value: 'business user' },
  { label: 'Learner', value: 'learner' },
  { label: 'Other', value: 'other' },
]

const URGENCY_OPTIONS = ['Nice to have', 'Important', 'Critical blocker']
const FREQUENCY_OPTIONS = ['One-time', 'Monthly', 'Weekly', 'Daily']
const FOLLOW_UP_OPTIONS = ['Teams', 'Email', 'No preference']
const INTERVIEW_OPTIONS = ['Yes', 'Maybe', 'No']

export default function AdaptiveCardForm({ prefill = {}, entryPoint, onSubmit, onCancel }) {
  const [form, setForm] = useState({
    raw_request: prefill.raw_request || '',
    cleaned_request: prefill.cleaned_request || '',
    problem: prefill.problem || '',
    desired_outcome: prefill.desired_outcome || '',
    feature_category: prefill.feature_category || '',
    capability_area: prefill.capability_area || '',
    affected_workflow: prefill.affected_workflow || 'Other',
    role: prefill.role || 'business user',
    urgency: prefill.urgency || 'Nice to have',
    frequency: prefill.frequency || 'One-time',
    interview_opt_in: prefill.interview_opt_in || 'Maybe',
    preferred_follow_up_method: prefill.preferred_follow_up_method || 'No preference',
    interview_context: prefill.interview_context || '',
  })
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  function set(field) {
    return (e) => setForm((prev) => ({ ...prev, [field]: e.target.value }))
  }

  async function handleSubmit(e) {
    e.preventDefault()
    if (!form.raw_request.trim()) {
      setError('Raw request is required.')
      return
    }
    setError(null)
    setSubmitting(true)
    try {
      const res = await fetch('http://localhost:4000/community-requests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...form, entry_point: entryPoint }),
      })
      const data = await res.json()
      if (!data.success) throw new Error('Server error')
      onSubmit(data)
    } catch (err) {
      setError('Could not reach the backend. Make sure the server is running on port 4000.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div style={styles.card}>
      <div style={styles.cardHeader}>
        <div style={styles.headerIcon}>⚡</div>
        <div>
          <div style={styles.cardTitle}>Experience Garage Feature Request</div>
          <div style={styles.cardSubtitle}>Help us improve the platform by sharing your idea</div>
        </div>
      </div>

      <form onSubmit={handleSubmit}>
        {/* ─── Section 1: Request ─── */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>Your Request</div>

          <Field label="Raw Request *">
            <textarea
              style={styles.textarea}
              value={form.raw_request}
              onChange={set('raw_request')}
              placeholder="Describe your feature idea in your own words…"
              rows={3}
            />
          </Field>

          <Field label="Cleaned Request">
            <input
              style={styles.input}
              value={form.cleaned_request}
              onChange={set('cleaned_request')}
              placeholder="Short, normalized version (bot-generated)"
            />
          </Field>

          <Field label="Problem / Pain Point">
            <textarea
              style={styles.textarea}
              value={form.problem}
              onChange={set('problem')}
              placeholder="What challenge are you facing?"
              rows={2}
            />
          </Field>

          <Field label="Desired Outcome">
            <textarea
              style={styles.textarea}
              value={form.desired_outcome}
              onChange={set('desired_outcome')}
              placeholder="What would success look like?"
              rows={2}
            />
          </Field>
        </div>

        {/* ─── Section 2: Classification ─── */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>Classification</div>

          <div style={styles.twoCol}>
            <Field label="Feature Category">
              <input
                style={styles.input}
                value={form.feature_category}
                onChange={set('feature_category')}
                placeholder="e.g. Learning Experience"
              />
            </Field>
            <Field label="Capability Area">
              <input
                style={styles.input}
                value={form.capability_area}
                onChange={set('capability_area')}
                placeholder="e.g. Content Delivery"
              />
            </Field>
          </div>

          <Field label="Affected Workflow">
            <select style={styles.select} value={form.affected_workflow} onChange={set('affected_workflow')}>
              {WORKFLOW_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
            </select>
          </Field>

          <div style={styles.twoCol}>
            <Field label="Role">
              <select style={styles.select} value={form.role} onChange={set('role')}>
                {ROLE_OPTIONS.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
              </select>
            </Field>
            <Field label="Urgency">
              <select style={styles.select} value={form.urgency} onChange={set('urgency')}>
                {URGENCY_OPTIONS.map((o) => <option key={o} value={o}>{o}</option>)}
              </select>
            </Field>
          </div>

          <Field label="Frequency – how often do you encounter this?">
            <div style={styles.chipGroup}>
              {FREQUENCY_OPTIONS.map((o) => (
                <button
                  key={o}
                  type="button"
                  style={{ ...styles.chip, ...(form.frequency === o ? styles.chipActive : {}) }}
                  onClick={() => setForm((p) => ({ ...p, frequency: o }))}
                >
                  {o}
                </button>
              ))}
            </div>
          </Field>
        </div>

        {/* ─── Section 3: Follow-up ─── */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>Follow-Up</div>

          <Field label="Would you be open to a 10–15 min follow-up chat with the Experience Garage product team?">
            <div style={styles.chipGroup}>
              {INTERVIEW_OPTIONS.map((o) => (
                <button
                  key={o}
                  type="button"
                  style={{
                    ...styles.chip,
                    ...(form.interview_opt_in === o ? styles.chipActive : {}),
                    ...(o === 'Yes' && form.interview_opt_in === 'Yes' ? styles.chipYes : {}),
                  }}
                  onClick={() => setForm((p) => ({ ...p, interview_opt_in: o }))}
                >
                  {o}
                </button>
              ))}
            </div>
          </Field>

          <Field label="Preferred Follow-up Method">
            <div style={styles.chipGroup}>
              {FOLLOW_UP_OPTIONS.map((o) => (
                <button
                  key={o}
                  type="button"
                  style={{
                    ...styles.chip,
                    ...(form.preferred_follow_up_method === o ? styles.chipActive : {}),
                  }}
                  onClick={() => setForm((p) => ({ ...p, preferred_follow_up_method: o }))}
                >
                  {o}
                </button>
              ))}
            </div>
          </Field>

          <Field label="Additional Interview Context">
            <textarea
              style={styles.textarea}
              value={form.interview_context}
              onChange={set('interview_context')}
              placeholder="Anything else you'd like us to know before we reach out?"
              rows={2}
            />
          </Field>
        </div>

        {error && <div style={styles.error}>{error}</div>}

        <div style={styles.actions}>
          <button type="button" style={styles.cancelBtn} onClick={onCancel}>
            Cancel
          </button>
          <button type="submit" style={styles.submitBtn} disabled={submitting}>
            {submitting ? 'Submitting…' : '✔ Submit to Experience Garage'}
          </button>
        </div>
      </form>
    </div>
  )
}

function Field({ label, children }) {
  return (
    <div style={{ marginBottom: 12 }}>
      <label style={styles.label}>{label}</label>
      {children}
    </div>
  )
}

const styles = {
  card: {
    background: '#fff',
    border: '1px solid var(--teams-border)',
    borderRadius: 8,
    overflow: 'hidden',
    maxWidth: 640,
    boxShadow: '0 2px 8px rgba(0,0,0,0.08)',
    margin: '8px 0',
  },
  cardHeader: {
    background: 'var(--teams-purple)',
    padding: '12px 16px',
    display: 'flex',
    alignItems: 'center',
    gap: 10,
    color: '#fff',
  },
  headerIcon: {
    fontSize: 22,
    background: 'rgba(255,255,255,0.2)',
    borderRadius: 8,
    width: 36,
    height: 36,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  cardTitle: {
    fontSize: 14,
    fontWeight: 700,
  },
  cardSubtitle: {
    fontSize: 11,
    opacity: 0.85,
    marginTop: 1,
  },
  section: {
    padding: '12px 16px 4px',
    borderBottom: '1px solid #f0f0f0',
  },
  sectionTitle: {
    fontSize: 11,
    fontWeight: 700,
    color: 'var(--teams-purple)',
    textTransform: 'uppercase',
    letterSpacing: 0.6,
    marginBottom: 10,
  },
  twoCol: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 10,
  },
  label: {
    display: 'block',
    fontSize: 12,
    fontWeight: 600,
    color: '#444',
    marginBottom: 4,
  },
  input: {
    width: '100%',
    padding: '7px 10px',
    border: '1px solid #d0d0d0',
    borderRadius: 4,
    fontSize: 13,
    outline: 'none',
    background: '#fafafa',
    transition: 'border 0.15s',
  },
  textarea: {
    width: '100%',
    padding: '7px 10px',
    border: '1px solid #d0d0d0',
    borderRadius: 4,
    fontSize: 13,
    outline: 'none',
    resize: 'vertical',
    background: '#fafafa',
    lineHeight: 1.5,
  },
  select: {
    width: '100%',
    padding: '7px 10px',
    border: '1px solid #d0d0d0',
    borderRadius: 4,
    fontSize: 13,
    outline: 'none',
    background: '#fafafa',
    appearance: 'auto',
  },
  chipGroup: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 6,
  },
  chip: {
    padding: '5px 12px',
    border: '1px solid #c8c8c8',
    borderRadius: 16,
    fontSize: 12,
    background: '#f5f5f5',
    color: '#444',
    transition: 'all 0.12s',
    cursor: 'pointer',
  },
  chipActive: {
    background: 'var(--teams-purple)',
    borderColor: 'var(--teams-purple)',
    color: '#fff',
  },
  chipYes: {
    background: 'var(--success-green)',
    borderColor: 'var(--success-green)',
  },
  actions: {
    display: 'flex',
    justifyContent: 'flex-end',
    gap: 8,
    padding: '12px 16px',
  },
  cancelBtn: {
    padding: '8px 20px',
    border: '1px solid #c8c8c8',
    borderRadius: 4,
    background: '#fff',
    fontSize: 13,
    fontWeight: 500,
    color: '#444',
  },
  submitBtn: {
    padding: '8px 20px',
    border: 'none',
    borderRadius: 4,
    background: 'var(--teams-purple)',
    color: '#fff',
    fontSize: 13,
    fontWeight: 600,
    opacity: 1,
    transition: 'opacity 0.15s',
  },
  error: {
    margin: '0 16px 8px',
    padding: '8px 12px',
    background: '#fef0f0',
    border: '1px solid #f5c5c5',
    borderRadius: 4,
    fontSize: 12,
    color: '#c00',
  },
}
