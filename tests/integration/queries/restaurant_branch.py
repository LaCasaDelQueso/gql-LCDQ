query_test_get_rest_cat = """query getCuisineTypes {
  getRestaurantCategories {
    ... on RestaurantCategories {
      categories {
        value: id
        label: name
      }
    }
    ... on RestaurantBranchError {
      code
    }
  }
}"""

query_test_new_restaurant_branch = """mutation newRestoBranch(
      $resBId: UUID!,
      $name: String!,
      $street: String!,
      $extN: String!,
      $intN: String!,
      $neigh: String!,
      $city: String!,
      $estate: String!,
      $country: String!,
      $zipCode: String!,
      $categoryId: UUID!,
      $fAddress: String!) {
    newRestaurantBranch(
      restaurantBusinessId: $resBId
      branchName: $name
      street: $street
      externalNum: $extN
      internalNum: $intN
      neighborhood: $neigh
      city: $city
      state: $estate
      country: $country
      zipCode: $zipCode
      categoryId: $categoryId
      fullAddress: $fAddress
    ) {
      ... on RestaurantBranchGQL {
        id
        branchName
        branchCategory {
          restaurantCategoryId
        }
        street
        externalNum
        internalNum
        neighborhood
        city
        estate: state
        country
        zipCode
      }
      ... on RestaurantBranchError {
        code
      }
    }
  }"""

query_test_new_branch_tax_info = """mutation insertNewBranchTaxInfo(
    $cfdi: CFDIUse!,
    $taxEmail: String!,
    $taxAddress: String!,
    $lName: String!,
    $RFC: String!,
    $branchId: UUID!,
    $satReg: RegimenSat!,
    $taxZip: String!) {
  newRestaurantBranchTaxInfo(
    cfdiUse: $cfdi
    email: $taxEmail
    fullAddress: $taxAddress
    legalName: $lName
    mxSatId: $RFC
    restaurantBranchId: $branchId
    satRegime: $satReg
    zipCode: $taxZip
  ) {
    ... on RestaurantBranchMxInvoiceInfo {
      taxId: mxSatId
      fiscalRegime: satRegime
      taxName: legalName
      taxAddress: fullAddress
      cfdiUse
      taxZipCode: zipCode
      invoiceEmail: email
    }
    ... on RestaurantBranchError {
      code
      msg
    }
  }
}"""

query_test_get_branches = """query getRestoBranches($resBId: UUID!) {
  getRestaurantBranchesFromToken(restaurantBusinessId: $resBId) {
    ... on RestaurantBranchGQL {
      id
      fullAddress
      branchName
      deleted
      branchCategory {
        restaurantCategoryId
      }
    }
    ... on RestaurantBranchError {
      code
    }
  }
}"""

query_test_get_branch_by_id = """query getRestoBranchById($branchId: UUID!) {
  getRestaurantBranchesFromToken(restaurantBranchId: $branchId) {
    ... on RestaurantBranchGQL {
      id
      street
      externalNum
      internalNum
      neighborhood
      city
      estate: state
      country
      zipCode
      fullAddress
      branchName
      deleted
      branchCategory {
        restaurantCategoryId
      }
      taxInfo {
        taxId: mxSatId
        fiscalRegime: satRegime
        taxName: legalName
        taxAddress: fullAddress
        cfdiUse
        taxZipCode: zipCode
        invoiceEmail: email
      }
    }
    ... on RestaurantBranchError {
      code
    }
  }
}"""

query_test_edit_branch = """mutation editRestoBranch(
    $resBId: UUID!,
    $name: String,
    $street: String,
    $extN: String,
    $intN: String,
    $neigh: String,
    $city: String,
    $estate: String,
    $country: String,
    $zipCode: String,
    $categoryId: UUID,
    $fAddress: String) {
  updateRestaurantBranch(
    restaurantBranchId: $resBId
    branchName: $name
    street: $street
    externalNum: $extN
    internalNum: $intN
    neighborhood: $neigh
    city: $city
    state: $estate
    country: $country
    zipCode: $zipCode
    categoryId: $categoryId
    fullAddress: $fAddress
  ) {
    ... on RestaurantBranchGQL {
      id
      branchName
      branchCategory {
        restaurantCategoryId
      }
      street
      externalNum
      internalNum
      neighborhood
      city
      estate: state
      country
      zipCode
    }
    ... on RestaurantBranchError {
        code
      }
  }
}"""

query_test_edit_branch_tax_id = """mutation editBranchTaxInfo(
    $cfdi: CFDIUse,
    $taxEmail: String,
    $taxAddress: String,
    $lName: String,
    $RFC: String,
    $branchId: UUID!,
    $satReg: RegimenSat,
    $taxZip: String) {
  updateRestaurantBranchTaxInfo(
    restaurantBranchId: $branchId
    cfdiUse: $cfdi
    email: $taxEmail
    fullAddress: $taxAddress
    legalName: $lName
    mxSatId: $RFC
    satRegime: $satReg
    zipCode: $taxZip
  ) {
    ... on RestaurantBranchMxInvoiceInfo {
      taxId: mxSatId
      fiscalRegime: satRegime
      taxName: legalName
      taxAddress: fullAddress
      cfdiUse
      taxZipCode: zipCode
      invoiceEmail: email
    }
    ... on RestaurantBranchError {
      code
    }
  }
}"""

query_test_delete_branch = """mutation deleteBranch($branchId: UUID!, $delete: Boolean!) {
  updateRestaurantBranch(restaurantBranchId: $branchId, deleted: $delete) {
    ... on RestaurantBranchGQL {
      id
      deleted
    }
    ... on RestaurantBranchError {
      code
    }
  }
}"""
