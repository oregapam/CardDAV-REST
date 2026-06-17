import {
  IDataObject,
  IExecuteFunctions,
  IHttpRequestMethods,
  ILoadOptionsFunctions,
  INodePropertyOptions,
  NodeOperationError,
} from 'n8n-workflow';

const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 300;

function sleep(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms));
}

function buildErrorMessage(statusCode: number, body: unknown): string {
  const b = (body && typeof body === 'object' ? body : {}) as Record<string, unknown>;
  // FastAPI wraps HTTPException detail one level deeper: { detail: <actual payload> }
  const d = (b.detail && typeof b.detail === 'object' ? b.detail : b) as Record<string, unknown>;
  if (statusCode === 409) {
    if (d.matched_email) return `Duplicate contact: email ${d.matched_email} already exists (UID: ${d.existing_uid})`;
    if (d.matched_phone) return `Duplicate contact: phone ${d.matched_phone} already exists (UID: ${d.existing_uid})`;
    return 'Duplicate contact or concurrent modification conflict';
  }
  if (statusCode === 422) return `Validation error: ${typeof b.detail === 'string' ? b.detail : JSON.stringify(b.detail ?? body)}`;
  if (statusCode === 404) return 'Contact not found';
  if (statusCode === 401) return 'Invalid API key — check your CardDavRestApi credential';
  if (statusCode === 502) return 'Baïkal server unreachable — check that Baïkal is running';
  return `Request failed with status ${statusCode}`;
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
    returnFullResponse: true as const,
    ignoreHttpStatusErrors: true as const,
  };

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      const response = await this.helpers.httpRequest(options) as {
        statusCode: number;
        body: unknown;
      };
      if (response.statusCode >= 400) {
        throw new NodeOperationError(
          this.getNode(),
          buildErrorMessage(response.statusCode, response.body),
        );
      }
      return response.body;
    } catch (error) {
      if (error instanceof NodeOperationError) throw error;
      // Raw connection/network error — retry if attempts remain, then wrap safely
      if (attempt === MAX_RETRIES) {
        throw new NodeOperationError(
          this.getNode(),
          error instanceof Error ? error.message : 'Request failed',
        );
      }
      await sleep(RETRY_DELAY_MS);
    }
  }
  throw new NodeOperationError(this.getNode(), 'Request failed');
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
