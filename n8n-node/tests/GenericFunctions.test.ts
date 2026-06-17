import {
  IExecuteFunctions,
  ILoadOptionsFunctions,
} from 'n8n-workflow';
import { apiRequest, loadAddressBooks } from '../nodes/CardDavRest/GenericFunctions';

function makeCtx(overrides: Record<string, unknown> = {}) {
  const mockHttpRequest = jest.fn().mockResolvedValue({});
  return {
    ctx: {
      getCredentials: jest.fn().mockResolvedValue({
        baseUrl: 'http://localhost:8000',
        apiKey: 'test-key',
      }),
      helpers: { httpRequest: mockHttpRequest },
      ...overrides,
    } as unknown as IExecuteFunctions,
    mockHttpRequest,
  };
}

describe('apiRequest', () => {
  it('calls httpRequest with correct URL and X-API-Key header', async () => {
    const { ctx, mockHttpRequest } = makeCtx();
    await apiRequest.call(ctx, 'GET', '/api/addressbooks');
    expect(mockHttpRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'GET',
        url: 'http://localhost:8000/api/addressbooks',
        headers: expect.objectContaining({ 'X-API-Key': 'test-key' }),
      }),
    );
  });

  it('strips trailing slash from baseUrl', async () => {
    const { ctx, mockHttpRequest } = makeCtx({
      getCredentials: jest.fn().mockResolvedValue({
        baseUrl: 'http://localhost:8000/',
        apiKey: 'key',
      }),
    });
    await apiRequest.call(ctx, 'GET', '/api/config');
    expect(mockHttpRequest).toHaveBeenCalledWith(
      expect.objectContaining({ url: 'http://localhost:8000/api/config' }),
    );
  });

  it('sends body as JSON when provided', async () => {
    const { ctx, mockHttpRequest } = makeCtx();
    await apiRequest.call(ctx, 'POST', '/api/contacts/search', { name: 'Alice' });
    expect(mockHttpRequest).toHaveBeenCalledWith(
      expect.objectContaining({ body: { name: 'Alice' }, json: true }),
    );
  });

  it('sends query string when qs provided', async () => {
    const { ctx, mockHttpRequest } = makeCtx();
    await apiRequest.call(ctx, 'GET', '/api/contacts', undefined, { limit: 10 });
    expect(mockHttpRequest).toHaveBeenCalledWith(
      expect.objectContaining({ qs: { limit: 10 } }),
    );
  });
});

describe('loadAddressBooks', () => {
  it('returns name/value pairs from GET /api/addressbooks', async () => {
    const { ctx } = makeCtx({
      helpers: {
        httpRequest: jest.fn().mockResolvedValue([
          { name: 'default', displayname: 'Default' },
          { name: 'leads', displayname: 'Leads' },
        ]),
      },
    });
    const result = await loadAddressBooks.call(
      ctx as unknown as ILoadOptionsFunctions,
    );
    expect(result).toEqual([
      { name: 'Default', value: 'default' },
      { name: 'Leads', value: 'leads' },
    ]);
  });
});
