-- CREATE DATABASE alima_marketplace;
CREATE EXTENSION pgcrypto;
CREATE EXTENSION unaccent;

/*
* 
*	Core Module
* 
*/ 
CREATE TABLE core_user (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    first_name VARCHAR NOT NULL,
    last_name VARCHAR NOT NULL,
    email VARCHAR NOT NULL,
    phone_number VARCHAR NOT NULL,
    firebase_id VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE orden (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    orden_type VARCHAR NOT NULL,
    orden_number VARCHAR DEFAULT '0' NOT NULL,
    source_type VARCHAR DEFAULT 'automation', -- automation, marketplace
    created_by UUID REFERENCES core_user(id) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE orden_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    orden_id UUID REFERENCES orden(id),
    status VARCHAR,
    created_by UUID REFERENCES core_user(id) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE category (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR NOT NULL,
  category_type VARCHAR NOT NULL, 
  keywords TEXT[],
  parent_category_id UUID REFERENCES category(id),
  created_by UUID REFERENCES core_user(id) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW() NOT NULL,
  last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE product_family (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    buy_unit VARCHAR NOT NULL, -- Buy UOM Type
    created_by UUID REFERENCES core_user(id) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE product_family_category (
  product_family_id UUID REFERENCES product_family(id) NOT NULL,
  category_id UUID REFERENCES category(id) NOT NULL,
  created_by UUID REFERENCES core_user(id) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW() NOT NULL,
  last_updated TIMESTAMP DEFAULT NOW() NOT NULL,
  PRIMARY KEY (product_family_id, category_id)
);

CREATE TABLE product (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    product_family_id UUID REFERENCES product_family(id) NOT NULL,
    sku VARCHAR NOT NULL,
    upc VARCHAR NOT NULL,
    name VARCHAR NOT NULL,
    description VARCHAR,
    keywords TEXT[],
    sell_unit VARCHAR NOT NULL, -- Sell UOM type 
    conversion_factor DOUBLE PRECISION DEFAULT 1.0 NOT NULL,
    buy_unit VARCHAR NOT NULL, -- Buy UOM type
    estimated_weight DOUBLE PRECISION,
    created_by UUID REFERENCES core_user(id) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE restaurant_business (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR NOT NULL,
    country VARCHAR NOT NULL,
    active BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE restaurant_branch (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_business_id UUID REFERENCES restaurant_business (id) NOT NULL,
    branch_name VARCHAR NOT NULL,
    full_address VARCHAR NOT NULL,
    street VARCHAR NOT NULL,
    external_num VARCHAR NOT NULL,
    internal_num VARCHAR NOT NULL,
    neighborhood VARCHAR NOT NULL,
    city VARCHAR NOT NULL,
    state VARCHAR NOT NULL,
    country VARCHAR NOT NULL,
    zip_code VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    deleted BOOLEAN DEFAULT 'f' NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE restaurant_branch_tag (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  restaurant_branch_id UUID REFERENCES restaurant_branch(id) NOT NULL,
  tag_key VARCHAR NOT NULL,
  tag_value VARCHAR NOT NULL,
  created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE supplier_business (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  name VARCHAR NOT NULL,
  country VARCHAR NOT NULL,
  active BOOLEAN NOT NULL,
  notification_preference VARCHAR NOT NULL, -- notification channel preference
  created_at TIMESTAMP DEFAULT NOW() NOT NULL,
  last_updated TIMESTAMP DEFAULT NOW() NOT NULL,
  logo_url VARCHAR
);

CREATE TABLE supplier_unit (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_business_id UUID REFERENCES supplier_business(id) NOT NULL,
  unit_name VARCHAR NOT NULL,
  full_address VARCHAR NOT NULL,
  street VARCHAR NOT NULL,
  external_num VARCHAR NOT NULL,
  internal_num VARCHAR NOT NULL,
  neighborhood VARCHAR NOT NULL,
  city VARCHAR NOT NULL,
  state VARCHAR NOT NULL,
  country VARCHAR NOT NULL,
  zip_code VARCHAR NOT NULL,
  deleted BOOLEAN DEFAULT 'f' NOT NULL,
  account_number VARCHAR DEFAULT '000000000000000000' NOT NULL,
  allowed_payment_methods TEXT[] DEFAULT '{}'::TEXT[],
  created_at TIMESTAMP DEFAULT NOW() NOT NULL,
  last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE OR REPLACE VIEW customer_business AS (
    SELECT id FROM restaurant_business
    UNION ALL
    SELECT id FROM supplier_business
);

/*
* 
*	Alima Business Module
* 
*/ 

CREATE TABLE alima_user (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    core_user_id UUID REFERENCES  core_user(id) NOT NULL,
    role VARCHAR NOT NULL,
    enabled BOOLEAN NOT NULL,
    deleted BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE alima_user_permission (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alima_user_id UUID REFERENCES alima_user(id) NOT NULL,
    create_user BOOLEAN NOT NULL,
    delegate_mode BOOLEAN NOT NULL,
    created_by UUID REFERENCES core_user(id) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE paid_account (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    customer_type VARCHAR CHECK (customer_type IN ('demand', 'supply', 'logistics', 'internal')) NOT NULL,
    customer_business_id UUID NOT NULL, -- implicit reference to customer business
    account_name VARCHAR NOT NULL,  -- account name
    invoicing_provider_id VARCHAR,
    created_by UUID REFERENCES core_user(id) NOT NULL,
    active_cedis INTEGER NOT NULL DEFAULT 1,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE paid_account_config (
    paid_account_id UUID PRIMARY KEY REFERENCES paid_account (id) NOT NULL,
    config JSON NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE charge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paid_account_id UUID REFERENCES paid_account (id) NOT NULL,
    charge_type VARCHAR NOT NULL,
    charge_amount DOUBLE PRECISION NOT NULL,
    currency VARCHAR(3) NOT NULL, -- currency code yype
    charge_amount_type VARCHAR NOT NULL, -- charge amount type % or $
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    charge_description VARCHAR DEFAULT '' NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL,
    active BOOLEAN DEFAULT 't' NOT NULL
);

-- Not yet implemented
CREATE TABLE discount_charge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    charge_id UUID REFERENCES charge (id) NOT NULL,
    charge_discount_type VARCHAR NOT NULL,
    charge_discount_amount DOUBLE PRECISION NOT NULL,
    charge_discount_amount_type VARCHAR NOT NULL, -- charge amount type % or $
    charge_discount_description VARCHAR NOT NULL,
    valid_upto TIMESTAMP NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);


CREATE TABLE billing_payment_method (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paid_account_id UUID REFERENCES paid_account (id) NOT NULL,
    payment_type VARCHAR NOT NULL, -- payment type
    payment_provider VARCHAR NOT NULL, -- payment provider type
    payment_provider_id VARCHAR NOT NULL, -- customer id in payment provider 
    account_number VARCHAR, -- account number (optional) for transfers
    account_name VARCHAR, -- account name (optional) for transfers
    bank_name VARCHAR, -- bank name (optional) for transfers
    created_by UUID REFERENCES core_user(id) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL,
    active BOOLEAN DEFAULT 't' NOT NULL
);

CREATE TABLE billing_invoice (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    paid_account_id UUID REFERENCES paid_account (id) NOT NULL,
    country VARCHAR NOT NULL,
    invoice_month VARCHAR NOT NULL, -- MM-YYYY 
    invoice_name VARCHAR NOT NULL,
    tax_invoice_id VARCHAR NOT NULL,
    invoice_number VARCHAR NOT NULL,
    invoice_files BYTEA[],
    sat_invoice_uuid UUID,
    total DOUBLE PRECISION NOT NULL,
    currency VARCHAR(3) NOT NULL, -- currency code type
    status VARCHAR CHECK (status IN ('active', 'canceled')) NOT NULL,
    result VARCHAR,
    payment_method VARCHAR CHECK (payment_method IN ('PUE', 'PPD')) DEFAULT 'PUE' NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE billing_invoice_complement (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    billing_invoice_id UUID REFERENCES billing_invoice (id) NOT NULL,
    tax_invoice_id VARCHAR NOT NULL,
    invoice_number VARCHAR NOT NULL,
    invoice_files BYTEA[],
    sat_invoice_uuid UUID NOT NULL,
    total DOUBLE PRECISION NOT NULL,
    currency VARCHAR(3) NOT NULL, -- currency code type
    status VARCHAR CHECK (status IN ('active', 'canceled')) NOT NULL,
    result VARCHAR,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE billing_invoice_charge (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    billing_invoice_id UUID REFERENCES billing_invoice (id) NOT NULL,
    charge_id UUID REFERENCES charge (id) NOT NULL,
    charge_type VARCHAR NOT NULL, -- charge type
    charge_base_quantity DOUBLE PRECISION NOT NULL,
    charge_amount DOUBLE PRECISION NOT NULL,
    charge_amount_type VARCHAR NOT NULL, -- $ or %
    total_charge DOUBLE PRECISION NOT NULL,
    currency VARCHAR(3)  NOT NULL, -- currency code type
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE billing_invoice_paystatus (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    billing_invoice_id UUID REFERENCES billing_invoice (id) NOT NULL,
    billing_payment_method_id UUID REFERENCES billing_payment_method (id),
    status VARCHAR NOT NULL, -- pay status type
    transaction_id VARCHAR, -- transaction id (optional) in payment provider
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);



CREATE TABLE alima_user_customer_relation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    alima_user_id UUID REFERENCES alima_user (id) NOT NULL,
    customer_type VARCHAR CHECK (customer_type IN ('demand', 'supply', 'logistics', 'internal')),
    customer_business_id UUID NOT NULL, -- implicit customer business reference
    created_by UUID REFERENCES  core_user(id) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE alima_user_customer_relation_status (
    alima_user_customer_relation_id UUID REFERENCES alima_user_customer_relation (id),
    status VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    PRIMARY KEY (alima_user_customer_relation_id, status)
);

/*
* 
*	Restaurant Module
* 
*/ 

CREATE TABLE restaurant_branch_category (
    restaurant_branch_id UUID REFERENCES restaurant_branch (id) NOT NULL,
    restaurant_category_id UUID REFERENCES category (id) NOT NULL,
    created_by UUID REFERENCES  core_user(id) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL,
    PRIMARY KEY (restaurant_branch_id, restaurant_category_id)
);

CREATE TABLE restaurant_branch_mx_invoice_info (
    branch_id UUID REFERENCES restaurant_branch (id) NOT NULL,
    mx_sat_id VARCHAR(15) NOT NULL, -- RFC
    email VARCHAR NOT NULL,
    legal_name VARCHAR NOT NULL,
    full_address VARCHAR NOT NULL,
    zip_code VARCHAR NOT NULL,
    cfdi_use VARCHAR NOT NULL, -- SAT CFDI USE code
    sat_regime VARCHAR NOT NULL, -- SAT regime code
    invoicing_provider_id VARCHAR, -- customer invoicing id (ie for facturama)
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL,
    PRIMARY KEY (branch_id, mx_sat_id)
);

CREATE TABLE restaurant_user (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    core_user_id UUID REFERENCES  core_user(id) NOT NULL,
    role VARCHAR NOT NULL,
    enabled BOOLEAN NOT NULL,
    deleted BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE restaurant_user_permission (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_user_id UUID REFERENCES restaurant_user (id) NOT NULL,
    restaurant_business_id UUID REFERENCES restaurant_business (id),
    display_orders_section BOOLEAN NOT NULL,
    display_suppliers_section BOOLEAN NOT NULL,
    display_products_section BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE restaurant_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_user_id UUID REFERENCES restaurant_user (id) NOT NULL,
    notify_new_supplier_delivery BOOLEAN NOT NULL,
    notify_reminder_to_buy BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE restaurant_supplier_relation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    restaurant_branch_id UUID REFERENCES restaurant_branch (id) NOT NULL,
    supplier_business_id UUID REFERENCES supplier_business (id) NOT NULL,
    rating INTEGER CHECK (rating BETWEEN 0 AND 5),
    review VARCHAR,
    created_by UUID REFERENCES core_user(id) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);


/*
* 
*	Supplier Module
* 
*/ 

CREATE TABLE supplier_unit_category (
  supplier_unit_id UUID REFERENCES supplier_unit(id) NOT NULL,
  supplier_category_id UUID REFERENCES category(id) NOT NULL,
  created_by UUID REFERENCES core_user(id) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW() NOT NULL,
  last_updated TIMESTAMP DEFAULT NOW() NOT NULL,
  PRIMARY KEY (supplier_unit_id, supplier_category_id)
);

CREATE TABLE supplier_user (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  core_user_id UUID REFERENCES core_user(id) NOT NULL,
  role VARCHAR NOT NULL,
  enabled BOOLEAN NOT NULL,
  deleted BOOLEAN NOT NULL,
  created_at TIMESTAMP DEFAULT NOW() NOT NULL,
  last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE supplier_user_permission (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_user_id UUID REFERENCES supplier_user(id) NOT NULL,
  supplier_business_id UUID REFERENCES supplier_business (id),
  display_sales_section BOOLEAN NOT NULL,
  display_routes_section BOOLEAN NOT NULL,
  created_at TIMESTAMP DEFAULT NOW() NOT NULL,
  last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE supplier_product (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  product_id UUID REFERENCES product(id),
  supplier_business_id UUID REFERENCES supplier_business(id) NOT NULL,
  sku VARCHAR NOT NULL,
  upc VARCHAR,
  description VARCHAR NOT NULL,
  tax_id VARCHAR NOT NULL,
  sell_unit VARCHAR NOT NULL,
  tax_unit VARCHAR NOT NULL,
  tax DOUBLE PRECISION NOT NULL, -- tax amount
  mx_ieps DOUBLE PRECISION, -- tax amount ieps
  conversion_factor DOUBLE PRECISION DEFAULT 1.0 NOT NULL,
  buy_unit VARCHAR NOT NULL, -- BUY UOM TYPE
  unit_multiple DOUBLE PRECISION NOT NULL,
  min_quantity DOUBLE PRECISION NOT NULL,
  estimated_weight DOUBLE PRECISION,
  is_active BOOLEAN NOT NULL,
  long_description TEXT,
  created_by UUID REFERENCES core_user(id) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW() NOT NULL,
  last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE supplier_product_tag (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_product_id UUID REFERENCES supplier_product(id) NOT NULL,
  tag_key VARCHAR NOT NULL,
  tag_value VARCHAR NOT NULL,
  created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE supplier_product_stock (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_product_id UUID REFERENCES supplier_product(id) NOT NULL,
  supplier_unit_id UUID REFERENCES supplier_unit(id),
  stock DOUBLE PRECISION NOT NULL,
  stock_unit VARCHAR NOT NULL, -- stock UOM type
  created_by UUID REFERENCES core_user(id) NOT NULL,
  active BOOLEAN NOT NULL,
  keep_selling_without_stock BOOLEAN NOT NULL,
  created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE supplier_product_price (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_product_id UUID REFERENCES supplier_product(id) NOT NULL,
  price DOUBLE PRECISION NOT NULL,
  currency VARCHAR(3) NOT NULL, -- currency code type
  valid_from TIMESTAMP NOT NULL,
  valid_upto TIMESTAMP NOT NULL,
  created_by UUID REFERENCES core_user(id) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE supplier_price_list (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_unit_id UUID REFERENCES supplier_unit(id) NOT NULL,
  supplier_restaurant_relation_ids JSON NOT NULL,
  supplier_product_price_ids JSON NOT NULL,
  name VARCHAR NOT NULL,
  is_default BOOLEAN NOT NULL,
  valid_from TIMESTAMP NOT NULL,
  valid_upto TIMESTAMP NOT NULL,
  created_by UUID REFERENCES core_user(id) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW() NOT NULL,
  last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE supplier_product_image (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_product_id UUID REFERENCES supplier_product(id) NOT NULL,
  image_url VARCHAR NOT NULL,
  deleted BOOLEAN NOT NULL,
  created_at TIMESTAMP DEFAULT NOW() NOT NULL,
  last_updated TIMESTAMP DEFAULT NOW() NOT NULL,
  priority INT DEFAULT 1 NOT NULL
);

CREATE TABLE supplier_restaurant_relation (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_unit_id UUID REFERENCES supplier_unit(id) NOT NULL,
  restaurant_branch_id UUID REFERENCES restaurant_branch(id) NOT NULL,
  approved BOOLEAN NOT NULL,
  priority INTEGER,
  rating INTEGER,
  review VARCHAR,
  created_by UUID REFERENCES core_user(id) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW() NOT NULL,
  last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE supplier_restaurant_relation_status (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  supplier_restaurant_relation_id UUID REFERENCES supplier_restaurant_relation(id) NOT NULL,
  status VARCHAR NOT NULL,
  created_by UUID REFERENCES core_user(id) NOT NULL,
  created_at TIMESTAMP DEFAULT NOW() NOT NULL,
  last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE supplier_restaurant_relation_mx_invoice_options (
    supplier_restaurant_relation_id UUID REFERENCES supplier_restaurant_relation (id) NOT NULL,
    automated_invoicing BOOLEAN NOT NULL,
    triggered_at VARCHAR NOT NULL,
    consolidation VARCHAR,
    invoice_type VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE supplier_vehicle (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_business_id UUID REFERENCES supplier_business(id) NOT NULL,
    vehicle_type VARCHAR NOT NULL, -- Vehicle Type
    max_weight DOUBLE PRECISION NOT NULL,
    name VARCHAR NOT NULL,
    plates VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);


CREATE TABLE supplier_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_user_id UUID REFERENCES supplier_user(id) NOT NULL,
    notify_new_resturant_orden BOOLEAN NOT NULL,
    notify_closing_day BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE supplier_cashback_transaction (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_unit_id UUID REFERENCES supplier_unit(id) NOT NULL,
    restaurant_branch_id UUID REFERENCES restaurant_branch(id) NOT NULL,
    concept VARCHAR NOT NULL,
    amount DOUBLE PRECISION NOT NULL,
    created_by UUID REFERENCES core_user(id) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

/*
* 
*	Core Module
*   Ordering Submodule
* 
*/ 
CREATE TABLE cart (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    active BOOLEAN NOT NULL,
    created_by UUID REFERENCES core_user(id) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    closed_at TIMESTAMP
);

CREATE TABLE cart_product (
    cart_id UUID REFERENCES cart(id) NOT NULL,
    supplier_product_id UUID REFERENCES supplier_product(id) NOT NULL,
    supplier_product_price_id UUID REFERENCES supplier_product_price(id),
    quantity DOUBLE PRECISION NOT NULL,
    unit_price DOUBLE PRECISION,
    subtotal DOUBLE PRECISION,
    comments VARCHAR,
    sell_unit VARCHAR NOT NULL, -- Sell UOM type
    created_by UUID REFERENCES core_user(id) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL,
    PRIMARY KEY (cart_id, supplier_product_id)
);

-- orden_details is insert-only, no updates allowed. 
CREATE TABLE orden_details (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    orden_id UUID REFERENCES orden(id) NOT NULL,
    version INTEGER,
    restaurant_branch_id UUID REFERENCES restaurant_branch(id) NOT NULL,
    supplier_unit_id UUID REFERENCES supplier_unit(id) NOT NULL,
    cart_id UUID REFERENCES cart(id) NOT NULL,
    delivery_date DATE NOT NULL,
    delivery_time VARCHAR NOT NULL, -- delivery time window type
    delivery_type VARCHAR DEFAULT 'scheduled_delivery', -- delivery type / selling option
    subtotal_without_tax DOUBLE PRECISION,
    tax DOUBLE PRECISION, -- tax amount
    subtotal DOUBLE PRECISION,
    discount DOUBLE PRECISION,
    discount_code VARCHAR,
    cashback DOUBLE PRECISION,
    cashback_transation_id UUID REFERENCES supplier_cashback_transaction(id),
    shipping_cost DOUBLE PRECISION,
    packaging_cost DOUBLE PRECISION,
    service_fee DOUBLE PRECISION,
    total DOUBLE PRECISION,
    comments VARCHAR,
    payment_method VARCHAR, -- payment method type
    created_by UUID REFERENCES core_user(id) NOT NULL, 
    approved_by UUID REFERENCES core_user(id),
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE orden_paystatus (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    orden_id UUID REFERENCES orden(id),
    status VARCHAR NOT NULL,
    created_by UUID REFERENCES core_user(id) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE payment_receipt (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_value DOUBLE PRECISION NOT NULL,
    evidence_file VARCHAR, -- json encoded file
    comments VARCHAR,
    created_by UUID REFERENCES core_user(id) NOT NULL,
    payment_day TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE mx_invoice (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_business_id UUID REFERENCES supplier_business(id) NOT NULL,
    restaurant_branch_id UUID REFERENCES restaurant_branch(id) NOT NULL,
    sat_invoice_uuid UUID NOT NULL,
    invoice_number VARCHAR NOT NULL,
    invoice_provider VARCHAR,
    invoice_provider_id VARCHAR,
    pdf_file BYTEA, -- byte array for binary data
    xml_file BYTEA, -- byte array for binary data
    total DOUBLE PRECISION NOT NULL,
    status VARCHAR NOT NULL,  -- invoice status type
    result VARCHAR,
    cancel_result VARCHAR,
    payment_method VARCHAR CHECK (payment_method IN ('PUE', 'PPD')) DEFAULT 'PUE' NOT NULL,
    created_by UUID REFERENCES core_user(id) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE mx_invoice_complement (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mx_invoice_id UUID REFERENCES mx_invoice(id) NOT NULL,
    sat_invoice_uuid UUID NOT NULL,
    invoice_number VARCHAR NOT NULL,
    invoice_provider VARCHAR,
    invoice_provider_id VARCHAR,
    pdf_file BYTEA, -- byte array for binary data
    xml_file BYTEA, -- byte array for binary data
    total DOUBLE PRECISION NOT NULL,
    status VARCHAR NOT NULL,  -- invoice status type
    result VARCHAR,
    created_by UUID REFERENCES core_user(id) NOT NULL, 
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE payment_receipt_orden (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    payment_receipt_id UUID REFERENCES payment_receipt(id) NOT NULL,
    orden_id UUID REFERENCES orden(id) NOT NULL,
    mx_invoice_complement_id UUID REFERENCES mx_invoice_complement(id),
    deleted boolean DEFAULT 'f' NOT NULL,
    created_by UUID REFERENCES core_user(id) NOT NULL, 
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE mx_invoice_paystatus (
    mx_invoice_id UUID REFERENCES mx_invoice(id) NOT NULL,
    status VARCHAR NOT NULL, -- pay status type
    created_by UUID REFERENCES core_user(id) NOT NULL, 
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    PRIMARY KEY (mx_invoice_id, status)
);

CREATE TABLE mx_invoice_orden (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    mx_invoice_id UUID REFERENCES mx_invoice(id) NOT NULL,
    orden_details_id UUID REFERENCES orden_details(id) NOT NULL,
    created_by UUID REFERENCES core_user(id) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE mx_sat_product_code (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    sat_code VARCHAR NOT NULL,
    sat_description VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE mx_invoicing_execution (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    orden_details_id UUID REFERENCES orden_details(id) NOT NULL,
    execution_start TIMESTAMP DEFAULT NOW() NOT NULL,
    execution_end TIMESTAMP,
    status VARCHAR NOT NULL, -- execution status type (running, success, failed)
    result JSON NOT NULL
);

/*
* 
*	Driver Module
* 
*/ 

CREATE TABLE driver_user (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    core_user_id UUID REFERENCES  core_user(id) NOT NULL,
    enabled BOOLEAN NOT NULL,
    deleted BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);


CREATE TABLE driver_status (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_user_id UUID REFERENCES driver_user (id) NOT NULL,
    status VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE driver_notifications (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    driver_user_id UUID REFERENCES driver_user (id) NOT NULL,
    notify_new_delivery_route BOOLEAN NOT NULL,
    created_by TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE driver_orden_status (
    orden_id UUID REFERENCES orden,
    driver_user_id UUID REFERENCES driver_user (id) NOT NULL,
    status VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    PRIMARY KEY (orden_id, driver_user_id, status)
);


/*
* 
*	Supplier Module
*   Delivery Submodule
* 
*/ 
CREATE TABLE supplier_route (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    vehicle_id UUID REFERENCES supplier_vehicle(id) NOT NULL,
    driver_user_id UUID REFERENCES driver_user(id) NOT NULL,
    start_time TIMESTAMP NOT NULL,
    actual_start_time TIMESTAMP,
    route_distance DOUBLE PRECISION NOT NULL,
    route_total_time INTEGER NOT NULL, -- IN SECONDS
    route_total_weight DOUBLE PRECISION NOT NULL, -- KGS
    actual_end_time TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE delivery_location(
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    lat DOUBLE PRECISION,
    long DOUBLE PRECISION,
    name VARCHAR,
    full_address VARCHAR
);

CREATE TABLE supplier_route_orden (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_route_id UUID REFERENCES supplier_route(id) NOT NULL,
    orden_id UUID REFERENCES orden(id) NOT NULL,
    stop_number INTEGER NOT NULL,
    delivery_time VARCHAR NOT NULL, -- serialized time window
    actual_delivery_time TIMESTAMP,
    estimated_weight DOUBLE PRECISION NOT NULL,
    source_location UUID REFERENCES delivery_location(id) NOT NULL,
    destination_location UUID REFERENCES delivery_location(id) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE supplier_delivery_evidence (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_route_orden_id UUID REFERENCES supplier_route_orden(id) NOT NULL,
    receiver_name VARCHAR,
    receiver_signature BYTEA,
    evidence_picture BYTEA[],
    created_by UUID REFERENCES core_user(id) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE supplier_driver_relation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_unit_id UUID REFERENCES supplier_unit(id) NOT NULL,
    driver_user_id UUID REFERENCES driver_user(id) NOT NULL,
    license_img BYTEA,
    license_number VARCHAR ,
    license_valid_until DATE NOT NULL,
    created_by UUID REFERENCES core_user(id) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

/*
* 
*	Scripts
* 
*/ 

CREATE TABLE script_execution (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    script_name VARCHAR NOT NULL,
    script_start TIMESTAMP DEFAULT NOW() NOT NULL,
    script_end TIMESTAMP,
    status VARCHAR NOT NULL,  -- script status type
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    data json
);

/**
*
*   B2B Ecommerce
*
**/

CREATE TABLE ecommerce_user_restaurant_relation (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    ecommerce_user_id UUID NOT NULL,
    restaurant_business_id UUID REFERENCES restaurant_business (id) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

/**
*
*   Integrations
*
*
**/

CREATE TABLE integrations_partner (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    integrator_name VARCHAR NOT NULL,
    description VARCHAR,
    business_id UUID NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE integrations_orden (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    integrations_partner_id UUID REFERENCES integrations_partner (id) NOT NULL,
    orden_id UUID REFERENCES orden (id) NOT NULL,
    integrations_orden_id VARCHAR,
    status VARCHAR, -- execution status type (running, success, failed)
    reason VARCHAR,
    result VARCHAR,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL,
    last_updated TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE integrations_webhook (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    url VARCHAR NOT NULL,
    source_type VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE third_parties_data_zones (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    zip_code VARCHAR NOT NULL,
    city VARCHAR NOT NULL,
    state VARCHAR NOT NULL,
    neighborhood VARCHAR NOT NULL,
    country VARCHAR NOT NULL,
    source VARCHAR NOT NULL
);


CREATE TABLE workflow_vars (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_business_id UUID REFERENCES supplier_business(id) NOT NULL,
    vars JSON NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);

CREATE TABLE workflow_integrations (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_business_id UUID REFERENCES supplier_business(id) NOT NULL,
    script_task VARCHAR NOT NULL,
    task_type VARCHAR NOT NULL,
    customer_type VARCHAR NOT NULL,
    created_at TIMESTAMP DEFAULT NOW() NOT NULL
);