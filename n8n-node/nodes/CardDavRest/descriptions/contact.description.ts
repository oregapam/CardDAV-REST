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
  {
    displayName: 'Check for Duplicates',
    name: 'checkDuplicates',
    type: 'boolean',
    displayOptions: { show: { resource: ['contact'], operation: ['create'] } },
    default: false,
    description:
      'Whether to return a 409 error if a contact with the same email already exists',
  },
];
