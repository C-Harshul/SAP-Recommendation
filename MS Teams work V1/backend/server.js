/**
 * SAP Experience Garage – Community Request Capture API
 *
 * REAL TEAMS INTEGRATION NOTE:
 * In a production Teams bot, this Express server would be replaced by an Azure Bot Framework
 * service. The POST /community-requests endpoint contract (request body shape + response shape)
 * should remain identical so the downstream recommendation engine requires no changes.
 * The mock-s3 writes would be replaced by actual AWS S3 PutObject calls using the same
 * community-request.schema.json structure.
 */

const express = require('express');
const cors = require('cors');
const fs = require('fs');
const path = require('path');

const app = express();
const PORT = 4000;

app.use(cors({ origin: 'http://localhost:5173' }));
app.use(express.json());

// ---------------------------------------------------------------------------
// Counter persistence – stores the last used CR number across restarts
// ---------------------------------------------------------------------------
const COUNTER_FILE = path.join(__dirname, 'mock-s3', 'community-requests', '.counter');
const RAW_DIR = path.join(__dirname, 'mock-s3', 'community-requests', 'raw');

function getNextRequestId() {
  let counter = 1000;
  if (fs.existsSync(COUNTER_FILE)) {
    counter = parseInt(fs.readFileSync(COUNTER_FILE, 'utf8'), 10);
  }
  counter += 1;
  fs.writeFileSync(COUNTER_FILE, String(counter));
  return `CR-${counter}`;
}

// ---------------------------------------------------------------------------
// POST /community-requests
// ---------------------------------------------------------------------------
app.post('/community-requests', (req, res) => {
  try {
    const body = req.body;

    const requestId = getNextRequestId();
    const submittedAt = new Date().toISOString();

    // Determine entry_point from the source field sent by the frontend
    const entryPoint = body.entry_point || 'personal_bot';

    const payload = {
      request_id: requestId,
      submitted_at: submittedAt,
      submitted_by: 'synthetic_user_001',
      department: 'SAP Customer Experience & Success Enablement',
      role: body.role || 'business user',
      source: 'Teams Bot',
      entry_point: entryPoint,

      // Core request content
      raw_request: body.raw_request || '',
      cleaned_request: body.cleaned_request || '',
      problem: body.problem || '',
      desired_outcome: body.desired_outcome || '',

      // Classification
      feature_category: body.feature_category || '',
      capability_area: body.capability_area || '',
      urgency: body.urgency || 'Nice to have',
      frequency: body.frequency || 'One-time',
      affected_workflow: body.affected_workflow || 'Other',

      // Follow-up / interview
      interview_opt_in: body.interview_opt_in === 'Yes' || body.interview_opt_in === true,
      preferred_follow_up_method: body.preferred_follow_up_method || 'No preference',
      interview_context: body.interview_context || '',

      // Enrichment placeholder (recommendation engine fills this later)
      similar_request_count: body.similar_request_count ?? 0,

      status: 'new',
    };

    // Write to mock S3
    const filePath = path.join(RAW_DIR, `${requestId}.json`);
    fs.writeFileSync(filePath, JSON.stringify(payload, null, 2));

    const mockS3Path = `backend/mock-s3/community-requests/raw/${requestId}.json`;

    res.status(201).json({
      success: true,
      request_id: requestId,
      mock_s3_path: mockS3Path,
      payload,
    });
  } catch (err) {
    console.error('Error saving community request:', err);
    res.status(500).json({ success: false, error: 'Internal server error' });
  }
});

// ---------------------------------------------------------------------------
// GET /community-requests – list all saved requests (useful for debugging)
// ---------------------------------------------------------------------------
app.get('/community-requests', (req, res) => {
  try {
    const files = fs.readdirSync(RAW_DIR).filter(f => f.endsWith('.json'));
    const requests = files.map(f => {
      return JSON.parse(fs.readFileSync(path.join(RAW_DIR, f), 'utf8'));
    });
    res.json({ count: requests.length, requests });
  } catch (err) {
    res.status(500).json({ error: 'Could not read requests' });
  }
});

app.listen(PORT, () => {
  console.log(`Experience Garage API running at http://localhost:${PORT}`);
  console.log(`Mock S3 path: ${RAW_DIR}`);
});
