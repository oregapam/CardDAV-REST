import {
  IDataObject,
  IExecuteFunctions,
  IHttpRequestMethods,
  ILoadOptionsFunctions,
  INodePropertyOptions,
  NodeApiError,
  NodeOperationError,
} from 'n8n-workflow';

const MAX_RETRIES = 2;
const RETRY_DELAY_MS = 300;

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

  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {
    try {
      return await this.helpers.httpRequest(options);
    } catch (error) {
      // n8n already formatted this error (HTTP 4xx/5xx) — re-throw as-is
      if (error instanceof NodeApiError || error instanceof NodeOperationError) {
        throw error;
      }
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
