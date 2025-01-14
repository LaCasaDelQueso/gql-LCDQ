query_test_new_rest_supplier = """mutation newRestoSupplier(
        $catId: UUID!,
        $country: String!,
        $sName: String!,
        $email: String!,
        $phoneNumber: String!,
        $notifPref: NotificationChannelType!,
        $branchId: UUID!,
        $cName: String!,
        $catalog: [SupplierProductCreationInput!]
        ) {
    newRestaurantSupplerCreation(
      categoryId: $catId
      country: $country
      email: $email
      name: $sName
      contactName: $cName
      notificationPreference: $notifPref
      phoneNumber: $phoneNumber
      restaurantBranchId: $branchId
      catalog: $catalog
    ) {
      ... on RestaurantSupplierCreationGQL {
        supplierBusiness {
          name
          id
          active
          notificationPreference
          country
        }
        supplierBusinessAccount {
          phoneNumber
          email
          displayName: legalRepName
        }
        unit {
          supplierUnit {
            id
          }
          category {
            supplierCategoryId
          }
        }
        products {
          product {
            id
          }
          price {
            id
          }
        }
      }
      ... on RestaurantSupplierError {
        code
      }
    }
  }"""

query_test_get_supp_cat = """query getSupCategories {
    getCategories(categoryType:SUPPLIER) {
      ...on Category {
        label: name
        value: id
      }
      ... on CategoryError {
        code
      }
    }
  }"""

query_test_get_active_supp = """query getActiveSuppliers {
  getRestaurantSuppliers {
    ... on RestaurantSupplierCreationGQL {
      supplierBusiness {
        id
        active
        name
        notificationPreference
        country
      }
      supplierBusinessAccount {
        email
        phoneNumber
        displayName: legalRepName
      }
      unit {
        category {
          supplierCategoryId
        }
      }
    }
    ... on RestaurantSupplierError {
      code
    }
  }
}"""

query_test_get_supp_profile = """query getSupplierProfile($supplierId: UUID!) {
  getRestaurantSuppliers(restaurantSupplierId: $supplierId) {
    ... on RestaurantSupplierCreationGQL {
      supplierBusiness {
        id
        active
        name
        notificationPreference
        country
      }
      supplierBusinessAccount {
        email
        phoneNumber
        displayName: legalRepName
      }
      unit {
        category {
          supplierCategoryId
        }
        supplierUnit {
          fullAddress
          id
          unitName
        }
      }
      products {
        product {
          id
          sku
          unitMultiple
          productUuid: productId
          minQuantity
          estimatedWeight
          productDescription: description
          conversionFactor
          sellUnit
        }
        price {
          amount: price
          id
          supplierProductId
          validUntil: validUpto
          unit: currency
        }
      }
      relation {
        restaurantBranchId
        rating
      }
    }
    ... on RestaurantSupplierError {
      code
    }
  }
}"""

query_test_edit_rest_supp = """mutation updateRestoSupplier(
    $supId: UUID!,
    $catId: UUID,
    $country: String,
    $sName: String,
    $email: String,
    $phoneNumber: String,
    $notifPref: NotificationChannelType,
    $branchId: UUID,
    $cName: String,
    $catalog: [SupplierProductCreationInput!]) {
  updateRestaurantSupplerCreation(
    supplierBusinessId: $supId
    categoryId: $catId
    country: $country
    email: $email
    name: $sName
    contactName: $cName
    notificationPreference: $notifPref
    phoneNumber: $phoneNumber
    restaurantBranchId: $branchId
    catalog: $catalog
  ) {
    ... on RestaurantSupplierCreationGQL {
      supplierBusiness {
        name
        id
        active
        notificationPreference
        country
      }
      supplierBusinessAccount {
        phoneNumber
        email
        displayName: legalRepName
      }
      unit {
        category {
          supplierCategoryId
        }
      }
      products {
        price {
          id
        }
      }
    }
    ... on RestaurantSupplierError {
      code
      msg
    }
  }
}"""

query_test_upload_supplier_file = """mutation uploadBatchRestoSuppliers(
    $productsfile: Upload!,
    $restaurantBranchId: UUID!,
    $supplierFile: Upload!) {
  newSupplierFile(
    productFile: $productsfile
    restaurantBranchId: $restaurantBranchId
    supplierFile: $supplierFile
  ) {
    ... on RestaurantSupplierBatchGQL {
      resMsg: msg
      products {
        description
        msg
        status
        sku
        supplierName
      }
      suppliers {
        uuid
        status
        name
        msg
      }
    }
    ... on RestaurantSupplierError {
      code
    }
  }
}"""
