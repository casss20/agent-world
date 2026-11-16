export default class BaseService {
  constructor(baseUrl = '') {
    this.baseUrl = baseUrl;
    this.headers = { 'Content-Type': 'application/json' };
  }

  async request(method, endpoint, body = null) {
    const url = `${this.baseUrl}${endpoint}`;
    const options = { method, headers: this.headers };
    if (body) options.body = JSON.stringify(body);
    const res = await fetch(url, options);
    if (!res.ok) throw new Error(`${method} ${endpoint}: ${res.status}`);
    return res.json();
  }

  get(endpoint)    { return this.request('GET', endpoint); }
  post(endpoint, body) { return this.request('POST', endpoint, body); }
  put(endpoint, body)  { return this.request('PUT', endpoint, body); }
  delete(endpoint)     { return this.request('DELETE', endpoint); }
}
