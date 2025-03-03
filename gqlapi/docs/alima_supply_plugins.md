# Alima Supply Plugins

In Alima Supply, in order to manage additional features and even external software integrations, we are introducing the use of **plugins** to all subsections of the product.

## How is a Plugin implemented?

Apart from what needs to be implemented from the Front-end side, from the backend each [Paid Account config](./alima_supply_account_config.md#paid-account-configuration) has to have a plugin configuration for it to be displayed in the UI. 

The plugin is stored within the JSON of the config and can be added to each of the subsections. (** Note: review the [Current Plugins](alima_supply_plugins.md#current-plugins)) docs to review what is supported.

### How to add a plugin?

Use the following script to add a plugin to a given paid account, and then follow the steps to add parameters to it.

```bash
cd projects/gqlapi

poetry run python -m gqlapi.scripts.alima_account.add_supplier_alima_config_plugin --supplier_business_id "SUPLIER_BUSINESS_ID" --subsection_id 4.1 --plugin_id 4.1.2 --plugin_name "NOMBRE DEL REPORTE" --plugin_provider "PLUGIN_PROVIDER" --plugin_provider_ref 29 
```


## Current Plugins

- Supported Subsections in UI: 
  - **Reportes**
- Supported Plugin Providers:
  - `alima_metabase`

### Plugin Providers

- Alima Metabase
  - Key:  `alima_metabase` 
  - Implementation: Integration of Generic Metabase iframe from configuration
    - The `plugin_provider_ref` is the number of Dashboard created in Metabase and exposed to be embedded in the application. This value is a string but is casted as an integer in the front-end. 
    - By default the `alima_metabase` component in the UI will pass a parameter called `supplier_business` : `string` passig over the UUID.
    - Parameter Types:
      - `date`
        - Default value is the number of days from current day, stored as an integer value stored as string, i.e. "-30", "0", "1"
      - `string`
      - `number`
      - `string[]`
        - if provided, `options` have to be provided in the form of `{key: string, label: string}[]`. And default value must be a `key` from the options.
      - `number[]`
        - if provided, `options` have to be provided in the form of `{key: number, label: string}[]`. And default value must be a `key` from the options.

--- 

### Plugins Library

#### 4.1.1 Reporte Diario 

```json
{
    "plugin_id": "4.1.1",
    "plugin_name": "Reporte de Pedidos Diarios",
    "plugin_provider": "alima_metabase",
    "plugin_provider_ref": "28",
    "plugin_params": [
        {
            "param_name": "Fecha",
            "param_key": "fecha",
            "param_type": "date",
            "default_value": "0"
        }
    ]
}
```

#### 4.1.2 Reporte de Estado de Cuenta

```json
{
    "plugin_id": "4.1.2",
    "plugin_name": "Reporte de Estado de Cuenta",
    "plugin_provider": "alima_metabase",
    "plugin_provider_ref": "29",
    "plugin_params": [
        {
            "param_name": "Desde",
            "param_key": "desde",
            "param_type": "date",
            "default_value": "-90"
        },
        {
            "param_name": "Hasta",
            "param_key": "hasta",
            "param_type": "date",
            "default_value": "1"
        },
        {
            "param_name": "Periodo",
            "param_key": "periodo",
            "param_type": "string[]",
            "default_value": "week",
            "options" : [
              {"key": "week", "label": "Semana"},
              {"key": "month", "label": "Mes"}
            ]
        }
    ]
}
```