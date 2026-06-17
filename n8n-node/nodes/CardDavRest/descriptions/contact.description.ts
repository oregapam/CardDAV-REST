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

export const contactFields: INodeProperties[] = [];
