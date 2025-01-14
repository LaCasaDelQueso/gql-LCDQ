query_test_new_user = """
mutation newRestaurantMut(
        $email: String!,
        $firebaseId: String!,
        $firstName: String!,
        $lastName: String!,
        $phoneNumber: String!,
        $role: String!) {

        newRestaurantUser(
        email: $email
        firebaseId: $firebaseId
        firstName: $firstName
        lastName: $lastName
        phoneNumber: $phoneNumber
        role: $role
        ) {
        ... on RestaurantUserGQL {
            id
            user {
                phoneNumber
                email
                firstName
                lastName
                firebaseId
            }
            enabled
            role
            deleted
            coreUserId
        }
        ... on RestaurantUserError {
            __typename
            code
            msg
        }
    }
}
"""

query_test_get_rest_user_by_token = """query getRestoUserByToken {
    getRestaurantUserFromToken {
      ... on RestaurantUserGQL {
        id
        coreUserId
        enabled
        deleted
        user {
          firstName
          lastName
          phoneNumber
          email
        }
      }
      ... on RestaurantUserError {
        code
        msg
      }
    }
  }"""
