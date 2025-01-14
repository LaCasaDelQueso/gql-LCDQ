from gqlapi.domain.models.v2.utils import CFDIUse, RegimenSat

mock_rest_branch = {
    "name": "LesTest",
    "street": "Oreoles",
    "extN": "2",
    "intN": "4",
    "neigh": "San Lazarito",
    "city": "CDMX",
    "estate": "Iztapalapa",
    "country": "México",
    "zipCode": "09230",
    "fAddress": "Mexico, CDMX, Iztapalapa, San LAzarito, Oreles Mz2 Lt4",
}

mock_rest_branch_error = {
    "name": "",
    "street": "",
    "extN": "",
    "intN": "",
    "neigh": "",
    "city": "",
    "estate": "",
    "country": "",
    "zipCode": "",
    "fAddress": "",
}

mock_branch_tax_info = {
    "cfdi": str(CFDIUse(1).name),
    "taxEmail": "tax@alima.la",
    "taxAddress": "Colonia Plumas 234",
    "lName": "Juan Acatlan",
    "RFC": "XXXX991212HDFSS",
    "satReg": str(RegimenSat(601).name),
    "taxZip": "12345",
}

mock_branch_tax_info_error = {
    "cfdi": str(CFDIUse(1).name),
    "taxEmail": "tax@alima.la",
    "taxAddress": "Colonia Plumas 234",
    "lName": "Juan Acatlan",
    "RFC": "XXXX991212HDFSS12345",
    "satReg": str(RegimenSat(601).name),
    "taxZip": "12345",
}
