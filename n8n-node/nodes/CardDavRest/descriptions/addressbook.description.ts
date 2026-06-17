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
