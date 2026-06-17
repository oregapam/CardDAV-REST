# n8n Community Node Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build and publish an n8n community node (`n8n-nodes-carddav-rest`) that wraps every endpoint of the CardDAV-REST adapter so n8n workflows can manage contacts without hand-crafted HTTP Request nodes.

**Architecture:** A self-contained TypeScript package lives in `n8n-node/` inside the existing monorepo. It has no Python dependency — it only calls the adapter's HTTP API. The node uses `@n8n/node-cli` for build/dev, Jest for unit tests. Resource/Operation dropdowns follow standard n8n community node conventions.

**Tech Stack:** TypeScript 5, `n8n-workflow` (peer dep), `@n8n/node-cli` (build), Jest + ts-jest (tests).

---

## File Map

```
n8n-node/
├── package.json
├── tsconfig.json
├── .npmignore
├── credentials/
│   └── CardDavRestApi.credentials.ts      # baseUrl + apiKey fields
├── nodes/
│   └── CardDavRest/
│       ├── CardDavRest.node.ts            # INodeType: description + execute()
│       ├── GenericFunctions.ts            # apiRequest() + loadAddressBooks()
│       ├── carddav-rest.svg               # node icon
│       └── descriptions/
│           ├── contact.description.ts     # Contact operations + fields
│           ├── addressbook.description.ts # Addressbook operations
│           ├── stats.description.ts       # Stats operation
│           └── config.description.ts     # Config operation
└── tests/
    ├── credential.test.ts
    ├── GenericFunctions.test.ts
    └── CardDavRest.node.test.ts
```

**Note on spec vs layout:** The approved spec shows `src/credentials/` and `src/nodes/`. The official `@n8n/node-cli` starter template (and its build pipeline) expects `credentials/` and `nodes/` at the package root. This plan uses the correct layout so that `dist/credentials/…` and `dist/nodes/…` paths match the `n8n` key in `package.json`.

---

## Task 1: Package scaffolding

**Files:**
- Create: `n8n-node/package.json`
- Create: `n8n-node/tsconfig.json`
- Create: `n8n-node/.npmignore`
- Modify: `.gitignore` (repo root)

- [ ] **Step 1: Create `n8n-node/package.json`**

```json
{
  "name": "n8n-nodes-carddav-rest",
  "version": "0.1.0",
  "description": "n8n community node for CardDAV REST — manage Baïkal contacts from n8n workflows",
  "license": "MIT",
  "keywords": [
    "n8n-community-node-package",
    "carddav",
    "contacts",
    "baikal",
    "vcard"
  ],
  "scripts": {
    "build": "n8n-node build",
    "dev": "n8n-node dev",
    "lint": "n8n-node lint",
    "lint:fix": "n8n-node lint --fix",
    "release": "n8n-node release",
    "test": "jest"
  },
  "files": ["dist"],
  "n8n": {
    "n8nNodesApiVersion": 1,
    "credentials": ["dist/credentials/CardDavRestApi.credentials.js"],
    "nodes": ["dist/nodes/CardDavRest/CardDavRest.node.js"]
  },
  "devDependencies": {
    "@n8n/node-cli": "*",
    "@types/jest": "^29.5.0",
    "jest": "^29.5.0",
    "ts-jest": "^29.1.0",
    "typescript": "^5.3.0"
  },
  "peerDependencies": {
    "n8n-workflow": "*"
  },
  "jest": {
    "preset": "ts-jest",
    "testEnvironment": "node",
    "roots": ["<rootDir>/tests"],
    "testMatch": ["**/*.test.ts"],
    "moduleNameMapper": {
      "^n8n-workflow$": "<rootDir>/node_modules/n8n-workflow"
    }
  }
}
```

- [ ] **Step 2: Create `n8n-node/tsconfig.json`**

```json
{
  "compilerOptions": {
    "strict": true,
    "module": "commonjs",
    "moduleResolution": "node",
    "target": "es2019",
    "lib": ["es2019", "es2020", "es2022.error"],
    "declaration": true,
    "sourceMap": true,
    "noImplicitAny": true,
    "noImplicitReturns": true,
    "noUnusedLocals": true,
    "strictNullChecks": true,
    "outDir": "./dist/"
  },
  "include": ["credentials/**/*", "nodes/**/*", "tests/**/*"]
}
```

- [ ] **Step 3: Create `n8n-node/.npmignore`**

```
tests/
*.test.ts
tsconfig.json
.eslintrc.js
```

- [ ] **Step 4: Update repo root `.gitignore`**

Add these lines to the existing `.gitignore` at the repo root:

```
n8n-node/dist/
n8n-node/node_modules/
```

- [ ] **Step 5: Install dependencies**

```bash
cd n8n-node
npm install
```

Expected: `node_modules/` created, no errors. Verify `n8n-workflow` is in `node_modules/` as a transitive dep from `@n8n/node-cli`.

- [ ] **Step 6: Commit**

```bash
git add n8n-node/package.json n8n-node/tsconfig.json n8n-node/.npmignore .gitignore
git commit -m "feat(n8n-node): scaffold TypeScript package"
```

---

## Task 2: Credential type

**Files:**
- Create: `n8n-node/credentials/CardDavRestApi.credentials.ts`
- Create: `n8n-node/tests/credential.test.ts`

- [ ] **Step 1: Write the failing test**

Create `n8n-node/tests/credential.test.ts`:

```typescript
import { CardDavRestApi } from '../credentials/CardDavRestApi.credentials';

describe('CardDavRestApi credential', () => {
  const cred = new CardDavRestApi();

  it('has name cardDavRestApi', () => {
    expect(cred.name).toBe('cardDavRestApi');
  });

  it('has displayName CardDAV REST API', () => {
    expect(cred.displayName).toBe('CardDAV REST API');
  });

  it('has baseUrl and apiKey fields', () => {
    const fieldNames = cred.properties.map((p) => p.name);
    expect(fieldNames).toContain('baseUrl');
    expect(fieldNames).toContain('apiKey');
  });

  it('apiKey field is a password field', () => {
    const apiKeyField = cred.properties.find((p) => p.name === 'apiKey');
    expect(apiKeyField?.typeOptions?.password).toBe(true);
  });
});
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
cd n8n-node
npm test -- --testPathPattern=credential
```

Expected: FAIL — "Cannot find module '../credentials/CardDavRestApi.credentials'"

- [ ] **Step 3: Create `n8n-node/credentials/CardDavRestApi.credentials.ts`**

```typescript
import { ICredentialType, INodeProperties } from 'n8n-workflow';

export class CardDavRestApi implements ICredentialType {
  name = 'cardDavRestApi';
  displayName = 'CardDAV REST API';
  documentationUrl =
    'https://github.com/mark/CardDAV-REST#authentication';
  properties: INodeProperties[] = [
    {
      displayName: 'Base URL',
      name: 'baseUrl',
      type: 'string',
      default: 'http://localhost:8000',
      placeholder: 'http://localhost:8000',
      description: 'Base URL of the CardDAV REST adapter. No trailing slash.',
    },
    {
      displayName: 'API Key',
      name: 'apiKey',
      type: 'string',
      typeOptions: { password: true },
      default: '',
      description: 'Value sent as the X-API-Key header on every request.',
    },
  ];
}
```

- [ ] **Step 4: Run test — expect PASS**

```bash
npm test -- --testPathPattern=credential
```

Expected: PASS (4 tests)

- [ ] **Step 5: Commit**

```bash
git add n8n-node/credentials/CardDavRestApi.credentials.ts n8n-node/tests/credential.test.ts
git commit -m "feat(n8n-node): add CardDavRestApi credential type"
```

---

## Task 3: GenericFunctions — HTTP helper

**Files:**
- Create: `n8n-node/nodes/CardDavRest/GenericFunctions.ts`
- Create: `n8n-node/tests/GenericFunctions.test.ts`

- [ ] **Step 1: Write the failing tests**

Create `n8n-node/tests/GenericFunctions.test.ts`:

```typescript
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
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
npm test -- --testPathPattern=GenericFunctions
```

Expected: FAIL — "Cannot find module '../nodes/CardDavRest/GenericFunctions'"

- [ ] **Step 3: Create `n8n-node/nodes/CardDavRest/GenericFunctions.ts`**

```typescript
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
```

- [ ] **Step 4: Run test — expect PASS**

```bash
npm test -- --testPathPattern=GenericFunctions
```

Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add n8n-node/nodes/CardDavRest/GenericFunctions.ts n8n-node/tests/GenericFunctions.test.ts
git commit -m "feat(n8n-node): add GenericFunctions apiRequest helper"
```

---

## Task 4: Addressbook, Stats, Config descriptions + node skeleton

**Files:**
- Create: `n8n-node/nodes/CardDavRest/descriptions/addressbook.description.ts`
- Create: `n8n-node/nodes/CardDavRest/descriptions/stats.description.ts`
- Create: `n8n-node/nodes/CardDavRest/descriptions/config.description.ts`
- Create: `n8n-node/nodes/CardDavRest/descriptions/contact.description.ts` (stub — only operations menu, no fields yet)
- Create: `n8n-node/nodes/CardDavRest/CardDavRest.node.ts`
- Create: `n8n-node/tests/CardDavRest.node.test.ts`

- [ ] **Step 1: Write failing tests**

Create `n8n-node/tests/CardDavRest.node.test.ts`:

```typescript
import {
  IExecuteFunctions,
  INodeExecutionData,
} from 'n8n-workflow';
import { CardDavRest } from '../nodes/CardDavRest/CardDavRest.node';

function makeExecFn(
  resource: string,
  operation: string,
  paramOverrides: Record<string, unknown> = {},
  httpResult: unknown = {},
) {
  const mockHttpRequest = jest.fn().mockResolvedValue(httpResult);
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
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
npm test -- --testPathPattern=CardDavRest.node
```

Expected: FAIL — "Cannot find module '../nodes/CardDavRest/CardDavRest.node'"

- [ ] **Step 3: Create `n8n-node/nodes/CardDavRest/descriptions/addressbook.description.ts`**

```typescript
import { INodeProperties } from 'n8n-workflow';

export const addressbookOperations: INodeProperties[] = [
  {
    displayName: 'Operation',
    name: 'operation',
    type: 'options',
    noDataExpression: true,
    displayOptions: { show: { resource: ['addressbook'] } },
    options: [
      {
        name: 'List',
        value: 'list',
        action: 'List all address books',
        description: 'Return all address books for the configured Baïkal user',
      },
    ],
    default: 'list',
  },
];

export const addressbookFields: INodeProperties[] = [];
```

- [ ] **Step 4: Create `n8n-node/nodes/CardDavRest/descriptions/stats.description.ts`**

```typescript
import { INodeProperties } from 'n8n-workflow';

export const statsOperations: INodeProperties[] = [
  {
    displayName: 'Operation',
    name: 'operation',
    type: 'options',
    noDataExpression: true,
    displayOptions: { show: { resource: ['stats'] } },
    options: [
      {
        name: 'Get',
        value: 'get',
        action: 'Get address book statistics',
        description:
          'Return contact count, last/oldest modification date, and total size for all address books',
      },
    ],
    default: 'get',
  },
];

export const statsFields: INodeProperties[] = [];
```

- [ ] **Step 5: Create `n8n-node/nodes/CardDavRest/descriptions/config.description.ts`**

```typescript
import { INodeProperties } from 'n8n-workflow';

export const configOperations: INodeProperties[] = [
  {
    displayName: 'Operation',
    name: 'operation',
    type: 'options',
    noDataExpression: true,
    displayOptions: { show: { resource: ['config'] } },
    options: [
      {
        name: 'Get',
        value: 'get',
        action: 'Get server configuration',
        description:
          'Return active name_format, default_region, and required_fields settings',
      },
    ],
    default: 'get',
  },
];

export const configFields: INodeProperties[] = [];
```

- [ ] **Step 6: Create stub `n8n-node/nodes/CardDavRest/descriptions/contact.description.ts`**

This file will grow across Tasks 5–11. For now it only defines the operations menu:

```typescript
import { INodeProperties } from 'n8n-workflow';

export const contactOperations: INodeProperties[] = [
  {
    displayName: 'Operation',
    name: 'operation',
    type: 'options',
    noDataExpression: true,
    displayOptions: { show: { resource: ['contact'] } },
    options: [
      { name: 'Create', value: 'create', action: 'Create a contact' },
      { name: 'Delete', value: 'delete', action: 'Delete a contact' },
      {
        name: 'Download vCard',
        value: 'getVcard',
        action: 'Download a contact as a vCard file',
      },
      { name: 'Get', value: 'get', action: 'Get a contact by UID' },
      {
        name: 'List',
        value: 'list',
        action: 'List contacts in an address book',
      },
      {
        name: 'Merge Duplicates',
        value: 'merge',
        action: 'Merge two duplicate contacts into one',
      },
      {
        name: 'Move to Addressbook',
        value: 'move',
        action: 'Move a contact to another address book',
      },
      {
        name: 'Search',
        value: 'search',
        action: 'Search contacts by name, email, or phone',
      },
      {
        name: 'Update (Full Replace)',
        value: 'update',
        action: 'Replace all fields of a contact',
      },
      {
        name: 'Update Fields',
        value: 'patch',
        action: 'Update specific fields of a contact',
      },
    ],
    default: 'list',
  },
];

// Fields will be appended per task.
export const contactFields: INodeProperties[] = [];
```

- [ ] **Step 7: Create `n8n-node/nodes/CardDavRest/CardDavRest.node.ts`**

```typescript
import {
  IDataObject,
  IExecuteFunctions,
  ILoadOptionsFunctions,
  INodeExecutionData,
  INodePropertyOptions,
  INodeType,
  INodeTypeDescription,
  NodeOperationError,
} from 'n8n-workflow';

import { apiRequest, loadAddressBooks } from './GenericFunctions';
import {
  contactFields,
  contactOperations,
} from './descriptions/contact.description';
import {
  addressbookFields,
  addressbookOperations,
} from './descriptions/addressbook.description';
import { statsFields, statsOperations } from './descriptions/stats.description';
import {
  configFields,
  configOperations,
} from './descriptions/config.description';

export class CardDavRest implements INodeType {
  description: INodeTypeDescription = {
    displayName: 'CardDAV REST',
    name: 'cardDavRest',
    icon: 'file:carddav-rest.svg',
    group: ['transform'],
    version: 1,
    subtitle: '={{$parameter["operation"] + ": " + $parameter["resource"]}}',
    description:
      'Manage contacts in Baïkal via the CardDAV REST adapter',
    defaults: { name: 'CardDAV REST' },
    inputs: ['main'],
    outputs: ['main'],
    credentials: [{ name: 'cardDavRestApi', required: true }],
    properties: [
      {
        displayName: 'Resource',
        name: 'resource',
        type: 'options',
        noDataExpression: true,
        options: [
          { name: 'Contact', value: 'contact' },
          { name: 'Addressbook', value: 'addressbook' },
          { name: 'Stats', value: 'stats' },
          { name: 'Config', value: 'config' },
        ],
        default: 'contact',
      },
      ...contactOperations,
      ...addressbookOperations,
      ...statsOperations,
      ...configOperations,
      ...contactFields,
      ...addressbookFields,
      ...statsFields,
      ...configFields,
    ],
  };

  methods = {
    loadOptions: {
      async getAddressBooks(
        this: ILoadOptionsFunctions,
      ): Promise<INodePropertyOptions[]> {
        return loadAddressBooks.call(this);
      },
    },
  };

  async execute(this: IExecuteFunctions): Promise<INodeExecutionData[][]> {
    const items = this.getInputData();
    const returnData: INodeExecutionData[] = [];

    for (let i = 0; i < items.length; i++) {
      const resource = this.getNodeParameter('resource', i) as string;
      const operation = this.getNodeParameter('operation', i) as string;
      let responseData: unknown;

      try {
        if (resource === 'addressbook') {
          if (operation === 'list') {
            responseData = await apiRequest.call(this, 'GET', '/api/addressbooks');
          }
        } else if (resource === 'stats') {
          if (operation === 'get') {
            responseData = await apiRequest.call(this, 'GET', '/api/stats');
          }
        } else if (resource === 'config') {
          if (operation === 'get') {
            responseData = await apiRequest.call(this, 'GET', '/api/config');
          }
        } else if (resource === 'contact') {
          // Implemented in Tasks 5–11
          throw new NodeOperationError(
            this.getNode(),
            `Operation "${operation}" not yet implemented`,
          );
        }
      } catch (error) {
        if (this.continueOnFail()) {
          returnData.push({
            json: { error: (error as Error).message },
            pairedItem: { item: i },
          });
          continue;
        }
        throw error;
      }

      const dataArray = Array.isArray(responseData)
        ? (responseData as IDataObject[])
        : [responseData as IDataObject];

      returnData.push(
        ...dataArray.map((d) => ({ json: d, pairedItem: { item: i } })),
      );
    }

    return [returnData];
  }
}
```

- [ ] **Step 8: Run tests — expect PASS**

```bash
npm test -- --testPathPattern=CardDavRest.node
```

Expected: PASS (8 tests — 5 description tests + 3 execute routing tests)

- [ ] **Step 9: Commit**

```bash
git add n8n-node/nodes/ n8n-node/tests/CardDavRest.node.test.ts
git commit -m "feat(n8n-node): add node skeleton with addressbook/stats/config resources"
```

---

## Task 5: Contact — List + Get operations

**Files:**
- Modify: `n8n-node/nodes/CardDavRest/descriptions/contact.description.ts`
- Modify: `n8n-node/nodes/CardDavRest/CardDavRest.node.ts` (execute block)
- Modify: `n8n-node/tests/CardDavRest.node.test.ts`

- [ ] **Step 1: Add tests for List and Get**

Append to the bottom of `n8n-node/tests/CardDavRest.node.test.ts`:

```typescript
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
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
npm test -- --testPathPattern=CardDavRest.node
```

Expected: 3 new FAIL — "Operation "list" not yet implemented"

- [ ] **Step 3: Add List + Get fields to `contact.description.ts`**

Replace the `export const contactFields: INodeProperties[] = [];` line with:

```typescript
export const contactFields: INodeProperties[] = [
  // --- addressBook (shared by all contact operations) ---
  {
    displayName: 'Address Book Name or ID',
    name: 'addressBook',
    type: 'options',
    typeOptions: { loadOptionsMethod: 'getAddressBooks' },
    required: true,
    displayOptions: { show: { resource: ['contact'] } },
    default: '',
    description:
      'Choose from the list, or specify a name using an expression',
  },

  // --- uid (shared by get/update/patch/delete/merge/move/getVcard) ---
  {
    displayName: 'Contact UID',
    name: 'uid',
    type: 'string',
    required: true,
    displayOptions: {
      show: {
        resource: ['contact'],
        operation: ['get', 'update', 'patch', 'delete', 'merge', 'move', 'getVcard'],
      },
    },
    default: '',
    description: 'Unique identifier of the contact (UUID)',
  },

  // --- List parameters ---
  {
    displayName: 'Limit',
    name: 'limit',
    type: 'number',
    typeOptions: { minValue: 1, maxValue: 1000 },
    displayOptions: { show: { resource: ['contact'], operation: ['list'] } },
    default: 50,
    description: 'Maximum number of contacts to return',
  },
  {
    displayName: 'Offset',
    name: 'offset',
    type: 'number',
    typeOptions: { minValue: 0 },
    displayOptions: { show: { resource: ['contact'], operation: ['list'] } },
    default: 0,
    description: 'Number of contacts to skip (for pagination)',
  },
  {
    displayName: 'Quick Search',
    name: 'q',
    type: 'string',
    displayOptions: { show: { resource: ['contact'], operation: ['list'] } },
    default: '',
    description:
      'Filter contacts by name, email, or phone (case-insensitive, partial match). Leave empty to return all.',
  },
];
```

- [ ] **Step 4: Add List + Get to execute() in `CardDavRest.node.ts`**

Replace the `} else if (resource === 'contact') {` block with:

```typescript
        } else if (resource === 'contact') {
          const addressBook = this.getNodeParameter('addressBook', i) as string;

          if (operation === 'list') {
            const limit = this.getNodeParameter('limit', i) as number;
            const offset = this.getNodeParameter('offset', i) as number;
            const q = this.getNodeParameter('q', i) as string;
            const qs: IDataObject = { limit, offset };
            if (q) qs.q = q;
            const page = (await apiRequest.call(
              this,
              'GET',
              `/api/addressbooks/${addressBook}/contacts`,
              undefined,
              qs,
            )) as { items: IDataObject[] };
            responseData = page.items;
          } else if (operation === 'get') {
            const uid = this.getNodeParameter('uid', i) as string;
            responseData = await apiRequest.call(
              this,
              'GET',
              `/api/addressbooks/${addressBook}/contacts/${uid}`,
            );
          } else {
            throw new NodeOperationError(
              this.getNode(),
              `Operation "${operation}" not yet implemented`,
            );
          }
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
npm test -- --testPathPattern=CardDavRest.node
```

Expected: all tests PASS (11 total)

- [ ] **Step 6: Commit**

```bash
git add n8n-node/nodes/CardDavRest/descriptions/contact.description.ts \
        n8n-node/nodes/CardDavRest/CardDavRest.node.ts \
        n8n-node/tests/CardDavRest.node.test.ts
git commit -m "feat(n8n-node): add contact List and Get operations"
```

---

## Task 6: Contact — Create operation

**Files:**
- Modify: `n8n-node/nodes/CardDavRest/descriptions/contact.description.ts`
- Modify: `n8n-node/nodes/CardDavRest/CardDavRest.node.ts`
- Modify: `n8n-node/tests/CardDavRest.node.test.ts`

- [ ] **Step 1: Add failing test**

Append to `n8n-node/tests/CardDavRest.node.test.ts`:

```typescript
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
        checkDuplicates: false,
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
        checkDuplicates: false,
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
        checkDuplicates: false,
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
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
npm test -- --testPathPattern=CardDavRest.node
```

Expected: 3 FAIL — "Operation "create" not yet implemented"

- [ ] **Step 3: Append Create fields to `contact.description.ts`**

Append inside the `contactFields` array (after the Quick Search field), before the closing `];`:

```typescript
  // --- Shared: firstname / lastname (create + update) ---
  {
    displayName: 'First Name',
    name: 'firstname',
    type: 'string',
    required: true,
    displayOptions: { show: { resource: ['contact'], operation: ['create', 'update'] } },
    default: '',
    description:
      'At least one of First Name or Last Name is required. Server also enforces this.',
  },
  {
    displayName: 'Last Name',
    name: 'lastname',
    type: 'string',
    displayOptions: { show: { resource: ['contact'], operation: ['create', 'update'] } },
    default: '',
  },

  // --- Phone Numbers (create / update / patch) ---
  {
    displayName: 'Phone Numbers',
    name: 'phones',
    type: 'fixedCollection',
    typeOptions: { multipleValues: true },
    displayOptions: { show: { resource: ['contact'], operation: ['create', 'update', 'patch'] } },
    default: {},
    options: [
      {
        displayName: 'Phone',
        name: 'phone',
        values: [
          {
            displayName: 'Type',
            name: 'type',
            type: 'options',
            options: [
              { name: 'Cell', value: 'cell' },
              { name: 'Home', value: 'home' },
              { name: 'Work', value: 'work' },
              { name: 'Other', value: 'other' },
            ],
            default: 'cell',
          },
          {
            displayName: 'Number',
            name: 'value',
            type: 'string',
            default: '',
            description:
              'Phone number. Server normalizes to E.164 format automatically (e.g. 06301234567 → +36301234567). May be required based on server REQUIRED_FIELDS config.',
          },
        ],
      },
    ],
  },

  // --- Email Addresses (create / update / patch) ---
  {
    displayName: 'Email Addresses',
    name: 'emails',
    type: 'fixedCollection',
    typeOptions: { multipleValues: true },
    displayOptions: { show: { resource: ['contact'], operation: ['create', 'update', 'patch'] } },
    default: {},
    options: [
      {
        displayName: 'Email',
        name: 'email',
        values: [
          {
            displayName: 'Type',
            name: 'type',
            type: 'options',
            options: [
              { name: 'Home', value: 'home' },
              { name: 'Work', value: 'work' },
              { name: 'Other', value: 'other' },
            ],
            default: 'home',
          },
          {
            displayName: 'Address',
            name: 'value',
            type: 'string',
            default: '',
            description:
              'May be required based on server REQUIRED_FIELDS config.',
          },
        ],
      },
    ],
  },

  // --- Addresses (create / update / patch) ---
  {
    displayName: 'Addresses',
    name: 'addresses',
    type: 'fixedCollection',
    typeOptions: { multipleValues: true },
    displayOptions: { show: { resource: ['contact'], operation: ['create', 'update', 'patch'] } },
    default: {},
    options: [
      {
        displayName: 'Address',
        name: 'address',
        values: [
          {
            displayName: 'Type',
            name: 'type',
            type: 'options',
            options: [
              { name: 'Home', value: 'home' },
              { name: 'Work', value: 'work' },
              { name: 'Other', value: 'other' },
            ],
            default: 'home',
          },
          { displayName: 'Street', name: 'street', type: 'string', default: '' },
          { displayName: 'City', name: 'city', type: 'string', default: '' },
          { displayName: 'ZIP', name: 'zip', type: 'string', default: '' },
          { displayName: 'State', name: 'state', type: 'string', default: '' },
          { displayName: 'Country', name: 'country', type: 'string', default: '' },
        ],
      },
    ],
  },

  // --- Additional Fields (create / update) ---
  {
    displayName: 'Additional Fields',
    name: 'additionalFields',
    type: 'collection',
    placeholder: 'Add Field',
    displayOptions: { show: { resource: ['contact'], operation: ['create', 'update'] } },
    default: {},
    options: [
      { displayName: 'Birthday', name: 'birthday', type: 'string', default: '', placeholder: 'YYYY-MM-DD' },
      {
        displayName: 'Categories',
        name: 'categories',
        type: 'string',
        default: '',
        description: 'Comma-separated list of categories, e.g. "VIP, Customer"',
      },
      { displayName: 'Middle Name', name: 'middlename', type: 'string', default: '' },
      {
        displayName: 'Note',
        name: 'note',
        type: 'string',
        typeOptions: { rows: 4 },
        default: '',
      },
      { displayName: 'Organization', name: 'org', type: 'string', default: '' },
      { displayName: 'Photo URL', name: 'photo', type: 'string', default: '' },
      { displayName: 'Prefix', name: 'prefix', type: 'string', default: '' },
      { displayName: 'Suffix', name: 'suffix', type: 'string', default: '' },
      { displayName: 'Title', name: 'title', type: 'string', default: '' },
      {
        displayName: 'URLs',
        name: 'urls',
        type: 'string',
        default: '',
        description: 'Comma-separated list of URLs, e.g. "https://example.com, https://blog.example.com"',
      },
    ],
  },

  // --- Create: checkDuplicates ---
  {
    displayName: 'Check for Duplicates',
    name: 'checkDuplicates',
    type: 'boolean',
    displayOptions: { show: { resource: ['contact'], operation: ['create'] } },
    default: false,
    description:
      'Whether to return a 409 error if a contact with the same email already exists',
  },
```

- [ ] **Step 4: Add a helper function and Create case to execute() in `CardDavRest.node.ts`**

Add this helper function BEFORE the `CardDavRest` class declaration:

```typescript
function buildContactBody(
  fn: IExecuteFunctions,
  i: number,
  operation: 'create' | 'update',
): IDataObject {
  const firstname = fn.getNodeParameter('firstname', i) as string;
  const lastname = fn.getNodeParameter('lastname', i) as string;
  const phonesRaw = fn.getNodeParameter('phones', i) as {
    phone?: Array<{ type: string; value: string }>;
  };
  const emailsRaw = fn.getNodeParameter('emails', i) as {
    email?: Array<{ type: string; value: string }>;
  };
  const addressesRaw = fn.getNodeParameter('addresses', i) as {
    address?: Array<{
      type: string;
      street: string;
      city: string;
      zip: string;
      state: string;
      country: string;
    }>;
  };
  const additionalFields = fn.getNodeParameter(
    'additionalFields',
    i,
  ) as IDataObject;

  const body: IDataObject = {
    firstname,
    lastname,
    phones: phonesRaw.phone ?? [],
    emails: emailsRaw.email ?? [],
    addresses: addressesRaw.address ?? [],
  };

  const stringFields = [
    'middlename', 'prefix', 'suffix', 'org', 'title', 'birthday', 'note', 'photo',
  ];
  for (const key of stringFields) {
    if (additionalFields[key] !== undefined && additionalFields[key] !== '') {
      body[key] = additionalFields[key];
    }
  }
  if (additionalFields.categories) {
    body.categories = (additionalFields.categories as string)
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
  }
  if (additionalFields.urls) {
    body.urls = (additionalFields.urls as string)
      .split(',')
      .map((s) => s.trim())
      .filter(Boolean);
  }

  return body;
}
```

Add `create` case inside the contact block in `execute()`, before the `else` throw:

```typescript
          } else if (operation === 'create') {
            const body = buildContactBody(this, i, 'create');
            body.check_duplicates = this.getNodeParameter('checkDuplicates', i) as boolean;
            responseData = await apiRequest.call(
              this,
              'POST',
              `/api/addressbooks/${addressBook}/contacts`,
              body,
            );
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
npm test -- --testPathPattern=CardDavRest.node
```

Expected: all tests PASS (14 total)

- [ ] **Step 6: Commit**

```bash
git add n8n-node/nodes/CardDavRest/descriptions/contact.description.ts \
        n8n-node/nodes/CardDavRest/CardDavRest.node.ts \
        n8n-node/tests/CardDavRest.node.test.ts
git commit -m "feat(n8n-node): add contact Create operation"
```

---

## Task 7: Contact — Update (Full Replace) + Update Fields (PATCH)

**Files:**
- Modify: `n8n-node/nodes/CardDavRest/descriptions/contact.description.ts`
- Modify: `n8n-node/nodes/CardDavRest/CardDavRest.node.ts`
- Modify: `n8n-node/tests/CardDavRest.node.test.ts`

- [ ] **Step 1: Add failing tests**

Append to test file:

```typescript
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
```

- [ ] **Step 2: Run test — expect FAIL**

```bash
npm test -- --testPathPattern=CardDavRest.node
```

Expected: 2 FAIL

- [ ] **Step 3: Add PATCH fields to `contact.description.ts`**

Append inside `contactFields` array, after the `checkDuplicates` field:

```typescript
  // --- Patch: Fields to Update collection ---
  {
    displayName: 'Fields to Update',
    name: 'fieldsToUpdate',
    type: 'collection',
    placeholder: 'Add Field',
    displayOptions: { show: { resource: ['contact'], operation: ['patch'] } },
    default: {},
    description:
      'Only the fields you add here will be changed. Fields not listed here remain untouched.',
    options: [
      { displayName: 'Birthday', name: 'birthday', type: 'string', default: '' },
      {
        displayName: 'Categories',
        name: 'categories',
        type: 'string',
        default: '',
        description: 'Comma-separated. Replaces all existing categories.',
      },
      { displayName: 'First Name', name: 'firstname', type: 'string', default: '' },
      { displayName: 'Last Name', name: 'lastname', type: 'string', default: '' },
      { displayName: 'Middle Name', name: 'middlename', type: 'string', default: '' },
      {
        displayName: 'Note',
        name: 'note',
        type: 'string',
        typeOptions: { rows: 4 },
        default: '',
      },
      { displayName: 'Organization', name: 'org', type: 'string', default: '' },
      { displayName: 'Photo URL', name: 'photo', type: 'string', default: '' },
      { displayName: 'Prefix', name: 'prefix', type: 'string', default: '' },
      { displayName: 'Suffix', name: 'suffix', type: 'string', default: '' },
      { displayName: 'Title', name: 'title', type: 'string', default: '' },
      {
        displayName: 'URLs',
        name: 'urls',
        type: 'string',
        default: '',
        description: 'Comma-separated. Replaces all existing URLs.',
      },
    ],
  },
```

- [ ] **Step 4: Add update + patch to execute() in `CardDavRest.node.ts`**

After the `create` case, add:

```typescript
          } else if (operation === 'update') {
            const uid = this.getNodeParameter('uid', i) as string;
            const body = buildContactBody(this, i, 'update');
            responseData = await apiRequest.call(
              this,
              'PUT',
              `/api/addressbooks/${addressBook}/contacts/${uid}`,
              body,
            );
          } else if (operation === 'patch') {
            const uid = this.getNodeParameter('uid', i) as string;
            const fieldsToUpdate = this.getNodeParameter(
              'fieldsToUpdate',
              i,
            ) as IDataObject;
            const patchBody: IDataObject = {};

            const scalarFields = [
              'firstname', 'lastname', 'middlename', 'prefix', 'suffix',
              'org', 'title', 'birthday', 'note', 'photo',
            ];
            for (const key of scalarFields) {
              if (fieldsToUpdate[key] !== undefined) {
                patchBody[key] = fieldsToUpdate[key];
              }
            }
            if (fieldsToUpdate.categories !== undefined) {
              patchBody.categories = (fieldsToUpdate.categories as string)
                .split(',')
                .map((s) => s.trim())
                .filter(Boolean);
            }
            if (fieldsToUpdate.urls !== undefined) {
              patchBody.urls = (fieldsToUpdate.urls as string)
                .split(',')
                .map((s) => s.trim())
                .filter(Boolean);
            }

            // Phones/emails/addresses — only include if user added entries
            const phonesRaw = this.getNodeParameter('phones', i) as {
              phone?: Array<{ type: string; value: string }>;
            };
            if (phonesRaw.phone?.length) {
              patchBody.phones = phonesRaw.phone;
            }
            const emailsRaw = this.getNodeParameter('emails', i) as {
              email?: Array<{ type: string; value: string }>;
            };
            if (emailsRaw.email?.length) {
              patchBody.emails = emailsRaw.email;
            }
            const addressesRaw = this.getNodeParameter('addresses', i) as {
              address?: unknown[];
            };
            if (addressesRaw.address?.length) {
              patchBody.addresses = addressesRaw.address;
            }

            responseData = await apiRequest.call(
              this,
              'PATCH',
              `/api/addressbooks/${addressBook}/contacts/${uid}`,
              patchBody,
            );
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
npm test -- --testPathPattern=CardDavRest.node
```

Expected: all tests PASS (16 total)

- [ ] **Step 6: Commit**

```bash
git add n8n-node/nodes/CardDavRest/descriptions/contact.description.ts \
        n8n-node/nodes/CardDavRest/CardDavRest.node.ts \
        n8n-node/tests/CardDavRest.node.test.ts
git commit -m "feat(n8n-node): add contact Update and Update Fields operations"
```

---

## Task 8: Contact — Delete + Search

**Files:**
- Modify: `n8n-node/nodes/CardDavRest/descriptions/contact.description.ts`
- Modify: `n8n-node/nodes/CardDavRest/CardDavRest.node.ts`
- Modify: `n8n-node/tests/CardDavRest.node.test.ts`

- [ ] **Step 1: Add failing tests**

```typescript
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
```

- [ ] **Step 2: Run — expect FAIL**

```bash
npm test -- --testPathPattern=CardDavRest.node
```

- [ ] **Step 3: Add Search fields to `contact.description.ts`**

Append inside `contactFields`:

```typescript
  // --- Search parameters ---
  {
    displayName: 'Name',
    name: 'name',
    type: 'string',
    displayOptions: { show: { resource: ['contact'], operation: ['search'] } },
    default: '',
    description: 'Partial name match (word-order independent for multi-word queries)',
  },
  {
    displayName: 'Email',
    name: 'email',
    type: 'string',
    displayOptions: { show: { resource: ['contact'], operation: ['search'] } },
    default: '',
    description: 'Exact email match',
  },
  {
    displayName: 'Phone',
    name: 'phone',
    type: 'string',
    displayOptions: { show: { resource: ['contact'], operation: ['search'] } },
    default: '',
    description: 'Partial phone match',
  },
  {
    displayName: 'Match Condition',
    name: 'matchCondition',
    type: 'options',
    displayOptions: { show: { resource: ['contact'], operation: ['search'] } },
    options: [
      {
        name: 'All Of (AND)',
        value: 'allof',
        description: 'Contact must match every provided filter',
      },
      {
        name: 'Any Of (OR)',
        value: 'anyof',
        description: 'Contact must match at least one filter',
      },
    ],
    default: 'allof',
  },
```

- [ ] **Step 4: Add delete + search to execute()**

After the `patch` case:

```typescript
          } else if (operation === 'delete') {
            const uid = this.getNodeParameter('uid', i) as string;
            responseData = await apiRequest.call(
              this,
              'DELETE',
              `/api/addressbooks/${addressBook}/contacts/${uid}`,
            );
          } else if (operation === 'search') {
            const name = this.getNodeParameter('name', i) as string;
            const email = this.getNodeParameter('email', i) as string;
            const phone = this.getNodeParameter('phone', i) as string;
            const matchCondition = this.getNodeParameter('matchCondition', i) as string;
            const body: IDataObject = { match_condition: matchCondition };
            if (name) body.name = name;
            if (email) body.email = email;
            if (phone) body.phone = phone;
            responseData = await apiRequest.call(
              this,
              'POST',
              `/api/addressbooks/${addressBook}/contacts/search`,
              body,
            );
```

- [ ] **Step 5: Run tests — expect PASS**

```bash
npm test -- --testPathPattern=CardDavRest.node
```

Expected: all PASS (19 total)

- [ ] **Step 6: Commit**

```bash
git add n8n-node/nodes/CardDavRest/descriptions/contact.description.ts \
        n8n-node/nodes/CardDavRest/CardDavRest.node.ts \
        n8n-node/tests/CardDavRest.node.test.ts
git commit -m "feat(n8n-node): add contact Delete and Search operations"
```

---

## Task 9: Contact — Merge, Move, Download vCard

**Files:**
- Modify: `n8n-node/nodes/CardDavRest/descriptions/contact.description.ts`
- Modify: `n8n-node/nodes/CardDavRest/CardDavRest.node.ts`
- Modify: `n8n-node/tests/CardDavRest.node.test.ts`

- [ ] **Step 1: Add failing tests**

```typescript
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
```

- [ ] **Step 2: Run — expect FAIL**

```bash
npm test -- --testPathPattern=CardDavRest.node
```

- [ ] **Step 3: Add Merge + Move fields to `contact.description.ts`**

Append inside `contactFields`:

```typescript
  // --- Merge: otherUid ---
  {
    displayName: 'Contact to Merge In (UID)',
    name: 'otherUid',
    type: 'string',
    required: true,
    displayOptions: { show: { resource: ['contact'], operation: ['merge'] } },
    default: '',
    description:
      'UID of the duplicate contact to merge into the primary. The duplicate is deleted after merge.',
  },

  // --- Move: targetBook ---
  {
    displayName: 'Target Address Book Name or ID',
    name: 'targetBook',
    type: 'options',
    typeOptions: { loadOptionsMethod: 'getAddressBooks' },
    required: true,
    displayOptions: { show: { resource: ['contact'], operation: ['move'] } },
    default: '',
    description:
      'Address book to move the contact into. Choose from the list, or specify a name using an expression.',
  },
```

- [ ] **Step 4: Add merge + move + getVcard to execute()**

After the `search` case:

```typescript
          } else if (operation === 'merge') {
            const uid = this.getNodeParameter('uid', i) as string;
            const otherUid = this.getNodeParameter('otherUid', i) as string;
            responseData = await apiRequest.call(
              this,
              'POST',
              `/api/addressbooks/${addressBook}/contacts/${uid}/merge/${otherUid}`,
            );
          } else if (operation === 'move') {
            const uid = this.getNodeParameter('uid', i) as string;
            const targetBook = this.getNodeParameter('targetBook', i) as string;
            responseData = await apiRequest.call(
              this,
              'POST',
              `/api/addressbooks/${addressBook}/contacts/${uid}/move/${targetBook}`,
            );
          } else if (operation === 'getVcard') {
            const uid = this.getNodeParameter('uid', i) as string;
            const credentials = await this.getCredentials<{
              baseUrl: string;
              apiKey: string;
            }>('cardDavRestApi');
            const vcardContent = (await this.helpers.httpRequest({
              method: 'GET',
              url: `${credentials.baseUrl.replace(/\/$/, '')}/api/addressbooks/${addressBook}/contacts/${uid}/vcard`,
              headers: { 'X-API-Key': credentials.apiKey },
            })) as string;

            const binaryData = await this.helpers.prepareBinaryData(
              Buffer.from(vcardContent, 'utf-8'),
              `${uid}.vcf`,
              'text/vcard; charset=utf-8',
            );

            returnData.push({
              json: { uid, filename: `${uid}.vcf` },
              binary: { data: binaryData },
              pairedItem: { item: i },
            });
            continue;
```

Also remove the fallback `else throw` since all operations are now handled. Replace:
```typescript
          } else {
            throw new NodeOperationError(
              this.getNode(),
              `Operation "${operation}" not yet implemented`,
            );
          }
```

With nothing (delete those lines — the `NodeOperationError` was only needed during development).

- [ ] **Step 5: Run tests — expect PASS**

```bash
npm test
```

Expected: all PASS (22 total)

- [ ] **Step 6: Commit**

```bash
git add n8n-node/nodes/CardDavRest/descriptions/contact.description.ts \
        n8n-node/nodes/CardDavRest/CardDavRest.node.ts \
        n8n-node/tests/CardDavRest.node.test.ts
git commit -m "feat(n8n-node): add contact Merge, Move, and Download vCard operations"
```

---

## Task 10: Icon + build verification

**Files:**
- Create: `n8n-node/nodes/CardDavRest/carddav-rest.svg`
- Verify: `npm run build` succeeds

- [ ] **Step 1: Create `n8n-node/nodes/CardDavRest/carddav-rest.svg`**

```svg
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 60 60">
  <rect width="60" height="60" rx="8" fill="#4299e1"/>
  <rect x="8" y="14" width="44" height="32" rx="4" fill="white" opacity="0.95"/>
  <circle cx="22" cy="27" r="7" fill="#4299e1"/>
  <line x1="33" y1="23" x2="48" y2="23" stroke="#4299e1" stroke-width="2.5" stroke-linecap="round"/>
  <line x1="33" y1="31" x2="48" y2="31" stroke="#4299e1" stroke-width="2" stroke-linecap="round" opacity="0.6"/>
  <line x1="8" y1="38" x2="52" y2="38" stroke="#4299e1" stroke-width="1.5" opacity="0.3"/>
  <line x1="12" y1="41" x2="36" y2="41" stroke="#4299e1" stroke-width="1.5" stroke-linecap="round" opacity="0.2"/>
</svg>
```

- [ ] **Step 2: Run the full test suite one final time**

```bash
cd n8n-node
npm test
```

Expected: all 22 tests PASS, no errors.

- [ ] **Step 3: Build the package**

```bash
npm run build
```

Expected: `dist/` directory created containing:
- `dist/credentials/CardDavRestApi.credentials.js`
- `dist/nodes/CardDavRest/CardDavRest.node.js`
- `dist/nodes/CardDavRest/carddav-rest.svg`

If `npm run build` fails because `@n8n/node-cli` is not available in this environment, fall back to:
```bash
npx tsc --project tsconfig.json
cp nodes/CardDavRest/carddav-rest.svg dist/nodes/CardDavRest/
```

- [ ] **Step 4: Verify dist layout matches package.json n8n key**

```bash
ls dist/credentials/
# Expected: CardDavRestApi.credentials.js

ls dist/nodes/CardDavRest/
# Expected: CardDavRest.node.js  carddav-rest.svg
```

If the paths match the `n8n.credentials` and `n8n.nodes` arrays in `package.json`, the node is installable.

- [ ] **Step 5: Commit**

```bash
git add n8n-node/nodes/CardDavRest/carddav-rest.svg
git commit -m "feat(n8n-node): add node icon and verify build"
```

---

## Task 11: Local dev testing with n8n

This task is manual — no automated test. It verifies the node works in a real n8n instance.

- [ ] **Step 1: Start local n8n with the node loaded**

```bash
cd n8n-node
npm run dev
```

Expected: n8n starts at `http://localhost:5678`. The `CardDAV REST` node appears in the node picker.

If `npm run dev` is unavailable (requires n8n internals from `@n8n/node-cli`), use the Docker alternative:

```bash
# From repo root
docker run -it --rm \
  -p 5678:5678 \
  -v "$(pwd)/n8n-node:/home/node/.n8n/custom/n8n-nodes-carddav-rest" \
  -e N8N_CUSTOM_EXTENSIONS=/home/node/.n8n/custom \
  n8nio/n8n
```

- [ ] **Step 2: Verify credential creation**

In n8n UI: Settings → Credentials → New → type "CardDAV REST API". Fields should show: Base URL + API Key.

- [ ] **Step 3: Create a test workflow**

1. Add a `CardDAV REST` node
2. Set credential (point to your running adapter: `http://localhost:8000`, your API key)
3. Resource: **Addressbook**, Operation: **List** → Execute → should return your address books
4. Resource: **Config**, Operation: **Get** → Execute → should return `{ name_format, default_region, required_fields }`
5. Resource: **Contact**, Operation: **List**, Address Book: (select from dropdown) → Execute → returns contacts

- [ ] **Step 4: Test Create + Get roundtrip**

1. Resource: **Contact**, Operation: **Create**
   - First Name: `Test Node`
   - Execute → note the returned `uid`
2. Resource: **Contact**, Operation: **Get**
   - Contact UID: (paste uid from step 1)
   - Execute → should return the created contact
3. Resource: **Contact**, Operation: **Delete**
   - Contact UID: (same uid)
   - Execute → `{ status: "deleted" }`

- [ ] **Step 5: Commit a note about local test results (optional)**

If everything works, the node is ready for npm publish:

```bash
cd n8n-node
npm publish --dry-run
# Verify the files listed match what you expect (dist/ only)
```

---

## Publishing checklist (when ready)

Before `npm publish`:

- [ ] Update `version` in `n8n-node/package.json` (semver)
- [ ] Set `homepage`, `repository`, and `author` fields in `package.json`
- [ ] Ensure you are logged in: `npm whoami`
- [ ] `npm publish` (first publish is public by default)
- [ ] Tag the release: `git tag n8n-node-v0.1.0 && git push --tags`
