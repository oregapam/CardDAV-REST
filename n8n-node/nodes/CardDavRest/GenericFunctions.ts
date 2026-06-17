import {
  IDataObject,
  IExecuteFunctions,
  IHttpRequestMethods,
  ILoadOptionsFunctions,
  INodePropertyOptions,
  JsonObject,
  NodeApiError,
} from 'n8n-workflow';

const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 300;

function isConnectionError(error: unknown): boolean {
  if (!error || typeof error !== 'object') return false;
  const e = error as Record<string, unknown>;
  // If the error carries an HTTP status code it's a real API response — don't retry
  if (e.statusCode || e.status || e.response) return false;
  return true;
}

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

export async function apiRequest(
  this: IExecuteFunctions | ILoadOptionsFunctions,
  method: IHttpRequestMethods,
  endpoint: string,
  body?: IDataObject,
  qs?: IDataObject,
): Promise<unknown> {
  const credentials = await this.getCredentials<{
    baseUrl: string;
    apiKey: string;
  }>('cardDavRestApi');

  const options = {
    method,
    url: `${credentials.baseUrl.replace(/\/$/, '')}${endpoint}`,
    headers: { 'X-API-Key': credentials.apiKey },
    body,
    qs,
    json: true,
  };

  let lastError: unknown;
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      return await this.helpers.httpRequest(options);
    } catch (error) {
      lastError = error;
      if (!isConnectionError(error) || attempt === MAX_RETRIES) {
        throw new NodeApiError(this.getNode(), error as JsonObject);
      }
      await sleep(RETRY_DELAY_MS);
    }
  }
  throw new NodeApiError(this.getNode(), lastError as JsonObject);
}

export async function loadAddressBooks(
  this: ILoadOptionsFunctions,
): Promise<INodePropertyOptions[]> {
  const books = (await apiRequest.call(this, 'GET', '/api/addressbooks')) as Array<{
    name: string;
    displayname: string;
  }>;
  return books.map((b) => ({ name: b.displayname, value: b.name }));
}
