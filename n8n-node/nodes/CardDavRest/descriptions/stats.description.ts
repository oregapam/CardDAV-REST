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
