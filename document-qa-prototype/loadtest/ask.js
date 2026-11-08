import http from 'k6/http';
import { check } from 'k6';

const BASE_URL = 'http://127.0.0.1:8000';
const DOCUMENT_TEXT = 'The yellow weather balloon is launched from Cedar Field at 08:30 each morning.';
const QUESTION = 'When is the yellow weather balloon launched?';

export const options = {
  // One workload keeps the maximum concurrency at 10 VUs.
  scenarios: {
    ask_load: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '5s', target: 5 },
        { duration: '5s', target: 10 },
        { duration: '30s', target: 10 },
        { duration: '10s', target: 0 },
      ],
      gracefulRampDown: '5s',
    },
  },
  thresholds: {
    'http_req_failed{endpoint:ask}': ['rate<0.01'],
    'http_req_duration{endpoint:ask}': ['p(95)<1000'],
    'checks{endpoint:ask}': ['rate>0.99'],
  },
};

export function setup() {
  const response = http.post(
    `${BASE_URL}/documents`,
    JSON.stringify({ text: DOCUMENT_TEXT }),
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { endpoint: 'document_setup' },
      timeout: '5s',
    },
  );

  if (response.status !== 201) {
    throw new Error(`Document setup failed: expected HTTP 201, received ${response.status}.`);
  }

  let documentId;
  try {
    documentId = response.json('document_id');
  } catch (_) {
    throw new Error('Document setup failed: response did not contain valid JSON.');
  }

  if (typeof documentId !== 'string' || !documentId) {
    throw new Error('Document setup failed: response is missing document_id.');
  }

  return { documentId };
}

export default function ({ documentId }) {
  const response = http.post(
    `${BASE_URL}/ask`,
    JSON.stringify({
      document_id: documentId,
      question: QUESTION,
      use_context: true,
    }),
    {
      headers: { 'Content-Type': 'application/json' },
      tags: { endpoint: 'ask' },
      timeout: '5s',
    },
  );

  check(
    response,
    {
      'POST /ask returns HTTP 200': (res) => res.status === 200,
      'POST /ask returns a non-empty answer': (res) => {
        if (res.status !== 200) return false;
        try {
          const answer = res.json('answer');
          return typeof answer === 'string' && answer.trim().length > 0;
        } catch (_) {
          return false;
        }
      },
    },
    { endpoint: 'ask' },
  );
}
