query_new_rest_business = """mutation newRestoBiz(
    $name: String!,
    $country: String!,
    $bizType: RestaurantBusinessType!,
    $phone: String!,
    $email: String!,
    $website: String) {
  newRestaurantBusiness(
    country: $country
    name: $name
    account: {businessType: $bizType, phoneNumber: $phone, email: $email, website: $website}
  ) {
    ... on RestaurantBusinessAdminGQL {
      id
      businessName: name
      active
      account {
        businessType
        email
        phoneNumber
        website
      }
    }
    ... on RestaurantBusinessError {
      code
      msg
    }
  }
}"""

query_rest_business = """query getRestoBiz {
    getRestaurantBusinessFromToken {
     ... on RestaurantBusinessAdminGQL {
       id
       businessName: name
       active
       account {
         businessType
         email
         phoneNumber
         website
       }
     }
     ... on RestaurantBusinessError {
       code
     }
   }
 }"""

query_edit_rest_business = """mutation updateRestoBizInfo(
    $name: String,
    $country: String,
    $active: Boolean,
    $restoId: UUID!,
    $bizType: RestaurantBusinessType!,
    $phone: String!,
    $email: String!,
    $website: String) {
  updateRestaurantBusiness(
    country: $country
    name: $name
    active: $active
    restaurantBusinessId: $restoId
    account: {businessType: $bizType, phoneNumber: $phone, email: $email, website: $website}
  ) {
    ... on RestaurantBusinessGQL {
      id
      businessName: name
      active
      account {
        businessType
        email
        phoneNumber
        website
      }
    }
    ... on RestaurantBusinessError {
      code
    }
  }
}"""
