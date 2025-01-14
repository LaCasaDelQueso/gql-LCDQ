from gqlapi.domain.models.v2.utils import NotificationChannelType


mock_rest_supplier = {
    "country": "México",
    "cName": "Lalo Garcia",
    "sName": "Felix Cuevas 42",
    "email": "felixcuevas@alima.la",
    "phoneNumber": "0987654321",
    "notifPref": str(NotificationChannelType.EMAIL.name),
    "catalog": {
        "product": {
            "sku": "123",
            "description": "123",
            "taxId": "123",
            "sellUnit": "KG",
            "taxUnit": "Pesos",
            "tax": 1.5,
            "conversionFactor": 1.5,
            "buyUnit": "KG",
            "unitMultiple": 1.5,
            "minQuantity": 1.5,
            "estimatedWeight": 1.5,
            "isActive": False,
            "upc": "",
        },
        "price": {
            "price": 1.5,
            "currency": "MXN",
            "validFrom": "1999-02-02",
            "validUpto": "2000-02-02",
        },
    },
}

mock_supp_file = {
    "supplier_business_name": "FerchoTest",
    "notification_preference": "email",
    "phone_number": "5544332211",
    "email": "FerchoTest@alima.la",
}

mock_prod_file = {
    "supplier_business_name": "FerchoTest",
    "description": "Pollo",
    "sell_unit": "Kg",
}
