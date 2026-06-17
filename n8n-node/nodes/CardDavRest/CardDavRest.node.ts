import {
  IDataObject,
  IExecuteFunctions,
  ILoadOptionsFunctions,
  INodeExecutionData,
  INodePropertyOptions,
  INodeType,
  INodeTypeDescription,
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

function buildContactBody(
  fn: IExecuteFunctions,
  i: number,
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
          const addressBook = this.getNodeParameter('addressBook', i) as string;

          if (operation === 'list') {
            const returnAll = this.getNodeParameter('returnAll', i) as boolean;
            const q = this.getNodeParameter('q', i) as string;
            type Page = { items: IDataObject[]; total: number; warning?: string };

            if (returnAll) {
              const PAGE_SIZE = 1000;
              let currentOffset = 0;
              const allItems: IDataObject[] = [];
              let total = 0;
              do {
                const qs: IDataObject = { limit: PAGE_SIZE, offset: currentOffset };
                if (q) qs.q = q;
                const page = (await apiRequest.call(
                  this, 'GET', `/api/addressbooks/${addressBook}/contacts`, undefined, qs,
                )) as Page;
                total = page.total;
                allItems.push(...page.items);
                currentOffset += PAGE_SIZE;
              } while (currentOffset < total);
              const mappedItems = allItems.map((item) => ({ ...item, _total: total }));
              responseData = mappedItems.length > 0 ? mappedItems : [{ _total: 0 }];
            } else {
              const limit = this.getNodeParameter('limit', i) as number;
              const offset = this.getNodeParameter('offset', i) as number;
              const qs: IDataObject = { limit, offset };
              if (q) qs.q = q;
              const page = (await apiRequest.call(
                this, 'GET', `/api/addressbooks/${addressBook}/contacts`, undefined, qs,
              )) as Page;
              if (page.items.length === 0) {
                responseData = [{ _total: page.total, _offset: offset, _warning: page.warning ?? null }];
              } else {
                responseData = page.items.map((item) => ({
                  ...item,
                  _total: page.total,
                  ...(page.warning ? { _warning: page.warning } : {}),
                }));
              }
            }
          } else if (operation === 'get') {
            const uid = this.getNodeParameter('uid', i) as string;
            responseData = await apiRequest.call(
              this,
              'GET',
              `/api/addressbooks/${addressBook}/contacts/${uid}`,
            );
          } else if (operation === 'create') {
            const body = buildContactBody(this, i);
            const createAddl = this.getNodeParameter('additionalFields', i) as IDataObject;
            body.check_duplicates = (createAddl.checkDuplicates as boolean) ?? true;
            responseData = await apiRequest.call(
              this,
              'POST',
              `/api/addressbooks/${addressBook}/contacts`,
              body,
            );
          } else if (operation === 'update') {
            const uid = this.getNodeParameter('uid', i) as string;
            const body = buildContactBody(this, i);
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
          }
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
