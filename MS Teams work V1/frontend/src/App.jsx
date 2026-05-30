import React, { useState } from 'react'
import NavRail from './components/NavRail.jsx'
import Sidebar from './components/Sidebar.jsx'
import ChatWindow from './components/ChatWindow.jsx'
import JsonPanel from './components/JsonPanel.jsx'

/**
 * REAL TEAMS INTEGRATION NOTE:
 * This App component simulates the Teams shell. In production this shell is provided by
 * the Teams client itself. Only the ChatWindow logic (bot conversation flow) and the
 * AdaptiveCardForm component need to be ported to a real Teams bot manifest + Azure Bot
 * Framework handler.
 */

const CHANNELS = [
  {
    id: 'personal-bot',
    name: 'Experience Garage Bot',
    type: 'bot',
    avatar: 'EG',
    subtitle: 'Personal app · Feature request bot',
    unread: 1,
  },
  {
    id: 'business-unit',
    name: 'SAP CX & Success Enablement',
    type: 'channel',
    avatar: 'SC',
    subtitle: 'Business Unit · 142 members',
    unread: 3,
  },
]

export default function App() {
  const [activeChannel, setActiveChannel] = useState(CHANNELS[0])
  const [submittedPayload, setSubmittedPayload] = useState(null)

  return (
    <div style={styles.shell}>
      {/* Far-left icon rail (Teams activity/chat/teams icons) */}
      <NavRail />

      {/* Chat list sidebar */}
      <Sidebar
        channels={CHANNELS}
        activeChannel={activeChannel}
        onSelect={setActiveChannel}
      />

      {/* Main chat area */}
      <ChatWindow
        channel={activeChannel}
        onSubmitSuccess={setSubmittedPayload}
      />

      {/* Right panel – JSON payload viewer */}
      <JsonPanel payload={submittedPayload} />
    </div>
  )
}

const styles = {
  shell: {
    display: 'flex',
    height: '100vh',
    overflow: 'hidden',
    background: '#fff',
  },
}
