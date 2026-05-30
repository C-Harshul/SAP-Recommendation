# Experience Garage – Community Request Capture (Teams Prototype)

A local, full-stack prototype that simulates how SAP employees submit product feature requests through a Microsoft Teams-style interface. Designed for stakeholder demos and transferable to a real Microsoft Teams bot implementation.

---

## Quick Start

### Prerequisites
- Node.js ≥ 18 and npm installed
- Ports 4000 and 5173 must be free

### 1 – Start the backend

```bash
cd backend
npm install
node server.js
```

The API will be available at `http://localhost:4000`.

### 2 – Start the frontend (in a new terminal tab)

```bash
cd frontend
npm install
npm run dev
```

Open `http://localhost:5173` in your browser.

---

## Demo Flows

### Flow 1 – Personal Teams Bot

1. Click **"Experience Garage Bot"** in the left chat sidebar.
2. Type a feature idea in the message box, e.g.:
   > "It would be nice if lessons were available in podcast format."
3. The bot responds with a cleaned summary and offers to open a form.
4. Click **"Fill out request form"** to expand the Adaptive Card-style form.
5. Complete the fields and click **Submit to Experience Garage**.
6. The bot confirms with the assigned request ID (e.g. CR-1001).
7. The JSON payload appears in the right-side panel.

### Flow 2 – Business Unit Chat

1. Click **"SAP CX & Success Enablement"** in the left sidebar.
2. Hover over **Fatima K.'s** message:
   > "The ML Workbench is useful, but I wish there was a guided no-code path for business users."
3. Click the **⋯ (more actions)** button that appears on hover.
4. Select **"⚡ Submit to Experience Garage"** from the dropdown.
5. The prefilled form expands inline.
6. Review fields and click **Submit to Experience Garage**.

---

## Project Structure

```
experience-garage-teams-prototype/
├── backend/
│   ├── server.js                   # Express API – POST /community-requests
│   ├── package.json
│   ├── mock-s3/
│   │   └── community-requests/
│   │       └── raw/                # Saved CR-XXXX.json files
│   ├── schemas/
│   │   └── community-request.schema.json
│   ├── adaptive-cards/
│   │   └── community-request-card.json   # Teams Adaptive Card JSON
│   └── sample-data/
│       └── synthetic-requests.json
└── frontend/
    ├── src/
    │   ├── App.jsx                 # Shell layout (NavRail + Sidebar + Chat + Panel)
    │   ├── components/
    │   │   ├── NavRail.jsx         # Teams-style icon rail
    │   │   ├── Sidebar.jsx         # Chat list sidebar
    │   │   ├── ChatWindow.jsx      # Both demo flows + conversation logic
    │   │   ├── AdaptiveCardForm.jsx # Adaptive Card-style form
    │   │   └── JsonPanel.jsx       # Right-side payload viewer
    │   ├── index.css
    │   └── main.jsx
    ├── index.html
    ├── vite.config.js
    └── package.json
```

---

## API Reference

### `POST http://localhost:4000/community-requests`

**Request body** (all fields optional except `raw_request`):

| Field | Type | Description |
|---|---|---|
| `raw_request` | string | Verbatim user text |
| `cleaned_request` | string | Bot-normalized summary |
| `problem` | string | Pain point description |
| `desired_outcome` | string | What success looks like |
| `feature_category` | string | High-level category |
| `capability_area` | string | Platform capability |
| `affected_workflow` | string | One of the defined workflows |
| `role` | string | User's job role |
| `urgency` | string | Nice to have / Important / Critical blocker |
| `frequency` | string | One-time / Monthly / Weekly / Daily |
| `interview_opt_in` | string | Yes / Maybe / No |
| `preferred_follow_up_method` | string | Teams / Email / No preference |
| `interview_context` | string | Extra context for follow-up |
| `entry_point` | string | personal_bot \| business_unit_chat |

**Response:**

```json
{
  "success": true,
  "request_id": "CR-1001",
  "mock_s3_path": "backend/mock-s3/community-requests/raw/CR-1001.json",
  "payload": { ... full community request object ... }
}
```

---

## Real Microsoft Teams Integration Guide

This prototype is structured so each layer maps directly to a real Teams implementation:

| Prototype asset | Real Teams equivalent |
|---|---|
| `ChatWindow.jsx` flow logic | Azure Bot Framework `onMessage()` handler |
| `AdaptiveCardForm.jsx` | `backend/adaptive-cards/community-request-card.json` sent as an Adaptive Card attachment |
| Business Unit ⋯ menu | Teams Message Extension with Action command |
| `POST /community-requests` | Same endpoint, called from bot handler instead of browser |
| `mock-s3/` writes | AWS S3 `PutObject` using same JSON schema |
| `community-request.schema.json` | Shared schema for both bot and recommendation engine |

See `// REAL TEAMS INTEGRATION NOTE:` comments throughout the source for precise porting instructions.

---

## Saved Files

Each submitted request is saved to:

```
backend/mock-s3/community-requests/raw/CR-XXXX.json
```

The counter persists across server restarts via:

```
backend/mock-s3/community-requests/.counter
```
