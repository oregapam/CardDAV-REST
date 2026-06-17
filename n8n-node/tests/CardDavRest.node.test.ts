import {
  IExecuteFunctions,
  INodeExecutionData,
  IDataObject,
} from 'n8n-workflow';
import { CardDavRest } from '../nodes/CardDavRest/CardDavRest.node';

function makeExecFn(
  resource: string,
  operation: string,
  paramOverrides: Record<string, unknown> = {},
  httpResult: unknown = {},
) {
  const mockHttpRequest = jest.fn().mockResolvedValue({ statusCode: 200, body: httpResult });
  const params: Record<string, unknown> = { resource, operation, ...paramOverrides };
  return {
    ctx: {
      getInputData: () => [{ json: {} }] as INodeExecutionData[],
      getNodeParameter: (name: string, _i: number) => params[name] ?? '',
      getCredentials: jest.fn().mockResolvedValue({
        baseUrl: 'http://localhost:8000',
        apiKey: 'test-key',
      }),
      helpers: {
        httpRequest: mockHttpRequest,
        returnJsonArray: (arr: IDataObject[]) =>
          arr.map((json) => ({ json })),
        constructExecutionMetaData: (
          items: INodeExecutionData[],
          _meta: unknown,
        ) => items,
      },
      continueOnFail: () => false,
      getNode: () => ({ name: 'CardDAV REST', type: 'cardDavRest' }),
    } as unknown as IExecuteFunctions,
    mockHttpRequest,
  };
}

describe('CardDavRest node description', () => {
  const node = new CardDavRest();

  it('has name cardDavRest', () => {
    expect(node.description.name).toBe('cardDavRest');
  });

  it('has 4 resources', () => {
    const resourceProp = node.description.properties.find(
      (p) => p.name === 'resource',
    );
    const values = (resourceProp?.options as Array<{ value: string }>)?.map(
      (o) => o.value,
    );
    expect(values).toContain('contact');
    expect(values).toContain('addressbook');
    expect(values).toContain('stats');
    expect(values).toContain('config');
  });

  it('addressbook has list operation', () => {
    const ops = node.description.properties.find(
      (p) =>
        p.name === 'operation' &&
        (p.displayOptions?.show?.resource as string[])?.includes('addressbook'),
    );
    const values = (ops?.options as Array<{ value: string }>)?.map(
      (o) => o.value,
    );
    expect(values).toContain('list');
  });

  it('stats has get operation', () => {
    const ops = node.description.properties.find(
      (p) =>
        p.name === 'operation' &&
        (p.displayOptions?.show?.resource as string[])?.includes('stats'),
    );
    expect(
      (ops?.options as Array<{ value: string }>)?.map((o) => o.value),
    ).toContain('get');
  });

  it('config has get operation', () => {
    const ops = node.description.properties.find(
      (p) =>
        p.name === 'operation' &&
        (p.displayOptions?.show?.resource as string[])?.includes('config'),
    );
    expect(
      (ops?.options as Array<{ value: string }>)?.map((o) => o.value),
    ).toContain('get');
  });
});

describe('execute — addressbook, stats, config', () => {
  const node = new CardDavRest();

  it('addressbook list calls GET /api/addressbooks', async () => {
    const { ctx, mockHttpRequest } = makeExecFn('addressbook', 'list', {}, []);
    await node.execute.call(ctx);
    expect(mockHttpRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'GET',
        url: 'http://localhost:8000/api/addressbooks',
      }),
    );
  });

  it('stats get calls GET /api/stats', async () => {
    const { ctx, mockHttpRequest } = makeExecFn('stats', 'get', {}, {
      total_contacts: 5,
      addressbooks: [],
    });
    await node.execute.call(ctx);
    expect(mockHttpRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'GET',
        url: 'http://localhost:8000/api/stats',
      }),
    );
  });

  it('config get calls GET /api/config', async () => {
    const { ctx, mockHttpRequest } = makeExecFn('config', 'get', {}, {
      name_format: 'western',
      default_region: 'HU',
      required_fields: [],
    });
    await node.execute.call(ctx);
    expect(mockHttpRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'GET',
        url: 'http://localhost:8000/api/config',
      }),
    );
  });
});

describe('execute — contact: list + get', () => {
  const node = new CardDavRest();

  it('list calls GET /api/addressbooks/{book}/contacts with qs', async () => {
    const { ctx, mockHttpRequest } = makeExecFn(
      'contact',
      'list',
      { addressBook: 'default', limit: 25, offset: 10, q: '' },
      { items: [], total: 0, limit: 25, offset: 10 },
    );
    await node.execute.call(ctx);
    expect(mockHttpRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'GET',
        url: 'http://localhost:8000/api/addressbooks/default/contacts',
        qs: expect.objectContaining({ limit: 25, offset: 10 }),
      }),
    );
  });

  it('list passes q param when provided', async () => {
    const { ctx, mockHttpRequest } = makeExecFn(
      'contact',
      'list',
      { addressBook: 'default', limit: 50, offset: 0, q: 'alice' },
      { items: [], total: 0, limit: 50, offset: 0 },
    );
    await node.execute.call(ctx);
    expect(mockHttpRequest).toHaveBeenCalledWith(
      expect.objectContaining({ qs: expect.objectContaining({ q: 'alice' }) }),
    );
  });

  it('get calls GET /api/addressbooks/{book}/contacts/{uid}', async () => {
    const { ctx, mockHttpRequest } = makeExecFn(
      'contact',
      'get',
      { addressBook: 'default', uid: 'abc-123' },
      { uid: 'abc-123', firstname: 'Alice' },
    );
    await node.execute.call(ctx);
    expect(mockHttpRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'GET',
        url: 'http://localhost:8000/api/addressbooks/default/contacts/abc-123',
      }),
    );
  });
});

describe('execute — contact: create', () => {
  const node = new CardDavRest();

  it('create calls POST /api/addressbooks/{book}/contacts', async () => {
    const { ctx, mockHttpRequest } = makeExecFn(
      'contact',
      'create',
      {
        addressBook: 'default',
        firstname: 'Alice',
        lastname: 'Smith',
        phones: {},
        emails: {},
        addresses: {},
        additionalFields: {},
      },
      { status: 'success', uid: 'new-uid' },
    );
    await node.execute.call(ctx);
    expect(mockHttpRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'POST',
        url: 'http://localhost:8000/api/addressbooks/default/contacts',
        body: expect.objectContaining({ firstname: 'Alice', lastname: 'Smith' }),
      }),
    );
  });

  it('create maps phones fixed collection to array', async () => {
    const { ctx, mockHttpRequest } = makeExecFn(
      'contact',
      'create',
      {
        addressBook: 'default',
        firstname: 'Bob',
        lastname: '',
        phones: { phone: [{ type: 'cell', value: '+36301234567' }] },
        emails: {},
        addresses: {},
        additionalFields: {},
      },
      { status: 'success', uid: 'uid2' },
    );
    await node.execute.call(ctx);
    expect(mockHttpRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        body: expect.objectContaining({
          phones: [{ type: 'cell', value: '+36301234567' }],
        }),
      }),
    );
  });

  it('create maps additionalFields.categories string to array', async () => {
    const { ctx, mockHttpRequest } = makeExecFn(
      'contact',
      'create',
      {
        addressBook: 'default',
        firstname: 'Carol',
        lastname: '',
        phones: {},
        emails: {},
        addresses: {},
        additionalFields: { categories: 'VIP, Customer' },
      },
      { status: 'success', uid: 'uid3' },
    );
    await node.execute.call(ctx);
    expect(mockHttpRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        body: expect.objectContaining({ categories: ['VIP', 'Customer'] }),
      }),
    );
  });
});

describe('execute — contact: update + patch', () => {
  const node = new CardDavRest();

  it('update calls PUT /api/addressbooks/{book}/contacts/{uid}', async () => {
    const { ctx, mockHttpRequest } = makeExecFn(
      'contact',
      'update',
      {
        addressBook: 'default',
        uid: 'uid-1',
        firstname: 'Alice',
        lastname: 'Updated',
        phones: {},
        emails: {},
        addresses: {},
        additionalFields: {},
      },
      { status: 'updated', uid: 'uid-1' },
    );
    await node.execute.call(ctx);
    expect(mockHttpRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'PUT',
        url: 'http://localhost:8000/api/addressbooks/default/contacts/uid-1',
        body: expect.objectContaining({ firstname: 'Alice' }),
      }),
    );
  });

  it('patch calls PATCH /api/addressbooks/{book}/contacts/{uid}', async () => {
    const { ctx, mockHttpRequest } = makeExecFn(
      'contact',
      'patch',
      {
        addressBook: 'default',
        uid: 'uid-1',
        fieldsToUpdate: { org: 'Acme Inc' },
        phones: {},
        emails: {},
        addresses: {},
      },
      { status: 'updated', uid: 'uid-1' },
    );
    await node.execute.call(ctx);
    expect(mockHttpRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'PATCH',
        url: 'http://localhost:8000/api/addressbooks/default/contacts/uid-1',
        body: expect.objectContaining({ org: 'Acme Inc' }),
      }),
    );
  });
});

describe('execute — contact: delete + search', () => {
  const node = new CardDavRest();

  it('delete calls DELETE /api/addressbooks/{book}/contacts/{uid}', async () => {
    const { ctx, mockHttpRequest } = makeExecFn(
      'contact',
      'delete',
      { addressBook: 'default', uid: 'uid-del' },
      { status: 'deleted', uid: 'uid-del' },
    );
    await node.execute.call(ctx);
    expect(mockHttpRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'DELETE',
        url: 'http://localhost:8000/api/addressbooks/default/contacts/uid-del',
      }),
    );
  });

  it('search calls POST .../contacts/search with body', async () => {
    const { ctx, mockHttpRequest } = makeExecFn(
      'contact',
      'search',
      {
        addressBook: 'default',
        name: 'Alice',
        email: '',
        phone: '',
        matchCondition: 'allof',
      },
      { exists: true, match_count: 1, matches: [] },
    );
    await node.execute.call(ctx);
    expect(mockHttpRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'POST',
        url: 'http://localhost:8000/api/addressbooks/default/contacts/search',
        body: expect.objectContaining({ name: 'Alice', match_condition: 'allof' }),
      }),
    );
  });

  it('search omits empty fields from body', async () => {
    const { ctx, mockHttpRequest } = makeExecFn(
      'contact',
      'search',
      { addressBook: 'default', name: '', email: 'a@b.hu', phone: '', matchCondition: 'anyof' },
      { exists: false, match_count: 0, matches: [] },
    );
    await node.execute.call(ctx);
    const body = mockHttpRequest.mock.calls[0][0].body as IDataObject;
    expect(body).not.toHaveProperty('name');
    expect(body).toHaveProperty('email', 'a@b.hu');
  });
});

describe('execute — contact: merge + move + getVcard', () => {
  const node = new CardDavRest();

  it('merge calls POST .../contacts/{uid}/merge/{otherUid}', async () => {
    const { ctx, mockHttpRequest } = makeExecFn(
      'contact',
      'merge',
      { addressBook: 'default', uid: 'uid-keep', otherUid: 'uid-gone' },
      { uid: 'uid-keep', firstname: 'Alice' },
    );
    await node.execute.call(ctx);
    expect(mockHttpRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'POST',
        url: 'http://localhost:8000/api/addressbooks/default/contacts/uid-keep/merge/uid-gone',
      }),
    );
  });

  it('move calls POST .../contacts/{uid}/move/{targetBook}', async () => {
    const { ctx, mockHttpRequest } = makeExecFn(
      'contact',
      'move',
      { addressBook: 'default', uid: 'uid-1', targetBook: 'leads' },
      { status: 'moved' },
    );
    await node.execute.call(ctx);
    expect(mockHttpRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'POST',
        url: 'http://localhost:8000/api/addressbooks/default/contacts/uid-1/move/leads',
      }),
    );
  });

  it('getVcard calls GET .../contacts/{uid}/vcard and returns binary', async () => {
    const vcardText = 'BEGIN:VCARD\nVERSION:3.0\nFN:Alice\nEND:VCARD';
    const mockHttpRequest = jest.fn().mockResolvedValue(vcardText);
    const mockPrepareBinaryData = jest
      .fn()
      .mockResolvedValue({ data: 'base64...', mimeType: 'text/vcard' });

    const params: Record<string, unknown> = {
      resource: 'contact',
      operation: 'getVcard',
      addressBook: 'default',
      uid: 'uid-1',
    };
    const ctx = {
      getInputData: () => [{ json: {} }] as INodeExecutionData[],
      getNodeParameter: (name: string, _i: number) => params[name] ?? '',
      getCredentials: jest.fn().mockResolvedValue({
        baseUrl: 'http://localhost:8000',
        apiKey: 'test-key',
      }),
      helpers: {
        httpRequest: mockHttpRequest,
        prepareBinaryData: mockPrepareBinaryData,
      },
      continueOnFail: () => false,
      getNode: () => ({ name: 'CardDAV REST', type: 'cardDavRest' }),
    } as unknown as IExecuteFunctions;

    const result = await node.execute.call(ctx);
    expect(mockHttpRequest).toHaveBeenCalledWith(
      expect.objectContaining({
        method: 'GET',
        url: 'http://localhost:8000/api/addressbooks/default/contacts/uid-1/vcard',
      }),
    );
    expect(result[0][0].binary).toBeDefined();
    expect(result[0][0].binary!.data).toBeDefined();
  });
});
