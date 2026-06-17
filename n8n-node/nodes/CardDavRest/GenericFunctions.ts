import {
  IDataObject,
  IExecuteFunctions,
  IHttpRequestMethods,
  ILoadOptionsFunctions,
  INodePropertyOptions,
} from 'n8n-workflow';

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

  return this.helpers.httpRequest({
    method,
    url: `${credentials.baseUrl.replace(/\/$/, '')}${endpoint}`,
    headers: { 'X-API-Key': credentials.apiKey },
    body,
    qs,
    json: true,
  });
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
