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
