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
