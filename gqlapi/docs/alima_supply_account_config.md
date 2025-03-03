# Alima Supply Account Configuration

For Alima Supply

## Paid Account Configuration

The configuration of what is shown and is available in the [Alima Supply product](https://seller.alima.la), stored in the following table `alima_marketplace.paid_account_config` as a JSON format in the `config` column.

The shape of such configuration is as follows:

```json
{
    "sections": [
        {
            "section_id": "0",
            "section_name": "",
            "subsections": [
                {
                    "subsection_id": "0.1",
                    "subsection_name": "Home",
                    "available": true,
                    "plugins": []
                }
            ]
        },
        {
            "section_id": "1",
            "section_name": "Clientes",
            "subsections": [
                {
                    "subsection_id": "1.1",
                    "subsection_name": "Clientes",
                    "available": true,
                    "plugins": []
                }
            ]
        },
        {
            "section_id": "2",
            "section_name": "Pedidos",
            "subsections": [
                {
                    "subsection_id": "2.1",
                    "subsection_name": "Catálogo",
                    "available": true,
                    "plugins": []
                },
                {
                    "subsection_id": "2.2",
                    "subsection_name": "Pedidos",
                    "available": true,
                    "plugins": []
                },
                {
                    "subsection_id": "2.3",
                    "subsection_name": "Facturas",
                    "available": false,
                    "plugins": []
                }
            ]
        },
        {
            "section_id": "3",
            "section_name": "Pagos",
            "subsections": [
                {
                    "subsection_id": "3.1",
                    "subsection_name": "Pagos",
                    "available": false,
                    "plugins": []
                }
            ]
        },
        {
            "section_id": "4",
            "section_name": "Reportes",
            "subsections": [
                {
                    "subsection_id": "4.1",
                    "subsection_name": "Reportes",
                    "available": true,
                    "plugins": [
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
                    ]
                }
            ]
        }
    ]
}
```

On the Front-End side, all sections are shown, and the availability is restricted at subsection level with the variable `available`.  Additionally each subsection can have [**plugins**](./alima_supply_plugins.md) to increase functionalities in each section.

### How to create Paid Account Configuration

This configurations is currently supported only for `alima_comercial` and `alima_pro` accounts.

The script to create the Paid account ([`create_supplier_alima_account.py`](../gqlapi/scripts/alima_account/create_supplier_alima_account.py)) already takes care of the process. But this script ([create_supplier_alima_config_account.py](../gqlapi/scripts/alima_account/create_supplier_alima_config_account.py)) can be used to create the respective configuration depending the supplier paid account.

This process does the following:

- For `alima_comercial`, it generates the full supply configuration available with the exception of the **Pagos** and **Facturas** subsection. No plugins are added.
- For `alima_pro`, it generates the full supply configuration available. No plugins are added.


