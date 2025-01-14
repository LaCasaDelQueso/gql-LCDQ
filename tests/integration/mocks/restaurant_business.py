from gqlapi.domain.models.v2.utils import RestaurantBusinessType


mock_rest_bus = {
    "country": "México",
    "name": "Carnes LaLatop",
    "bizType": RestaurantBusinessType.RESTAURANT.value.upper(),
    "phone": "5244332211",
    "email": "gqltest91@alima.la",
    "website": "alima.la",
}

mock_rest_supp_error = {
    "country": "",
    "name": "",
    "bizType": RestaurantBusinessType.RESTAURANT.value.upper(),
    "phone": "",
    "email": "",
    "website": "",
}
