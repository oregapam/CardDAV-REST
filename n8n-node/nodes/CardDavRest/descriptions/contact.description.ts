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

export const contactFields: INodeProperties[] = [
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
