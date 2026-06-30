import axios from 'axios';

const client = axios.create({
  baseURL: '/api',
  timeout: 120000,
});

export async function healthCheck() {
  const { data } = await client.get('/health');
  return data;
}

export async function generateDataset(nSamples) {
  const { data } = await client.post('/dataset/generate', { n_samples: nSamples });
  return data;
}

export async function uploadDataset(file) {
  const form = new FormData();
  form.append('file', file);
  const { data } = await client.post('/dataset/upload', form, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return data;
}

export async function runDetection({
  defaultPqcMode,
  live,
  delay,
  onEvent,
  onComplete,
  onError,
}) {
  if (live) {
    return streamDetection({
      defaultPqcMode,
      delay,
      onEvent,
      onComplete,
      onError,
    });
  }
  const { data } = await client.post('/detect', {
    default_pqc_mode: defaultPqcMode,
    live: false,
    delay,
  });
  return data;
}

export function streamDetection({ defaultPqcMode, delay, onEvent, onComplete, onError }) {
  return new Promise((resolve, reject) => {
    fetch('/api/detect/stream', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        default_pqc_mode: defaultPqcMode,
        live: true,
        delay,
      }),
    })
      .then((response) => {
        if (!response.ok) throw new Error('检测流连接失败');
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';

        const pump = () => {
          reader.read().then(({ done, value }) => {
            if (done) {
              resolve();
              return;
            }
            buffer += decoder.decode(value, { stream: true });
            const parts = buffer.split('\n\n');
            buffer = parts.pop() || '';
            parts.forEach((part) => {
              if (part.startsWith('data: ')) {
                try {
                  const payload = JSON.parse(part.slice(6));
                  onEvent?.(payload);
                  if (payload.type === 'complete') {
                    onComplete?.(payload);
                  }
                } catch (e) {
                  onError?.(e);
                }
              }
            });
            pump();
          });
        };
        pump();
      })
      .catch((err) => {
        onError?.(err);
        reject(err);
      });
  });
}

export default client;
