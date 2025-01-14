/****************************************/
/************ AUTHOS SCHEMA  ************/
/****************************************/

-- CREATE DATABASE authos;

/* Load uuid extension library */
CREATE EXTENSION pgcrypto;

CREATE TABLE ecommerce_seller (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    supplier_business_id uuid NOT NULL, -- referenced to Alima Seller
    secret_key varchar NOT NULL, --NEXT_PUBLIC_SELLER_ID
    seller_name varchar NOT NULL, --NEXT_PUBLIC_SELLER_NAME
    project_name varchar,
    ecommerce_url varchar, --NEXT_PUBLIC_PROJECT_URL
    created_at timestamp NOT NULL DEFAULT NOW(),
    last_updated timestamp NOT NULL DEFAULT NOW(),
    
    banner_img varchar, --NEXT_PUBLIC_BANNER_IMG (/assets/banner_{secret_key}.png)
    banner_img_href varchar, --NEXT_PUBLIC_BANNER_IMG_HREF
    categories varchar, --NEXT_PUBLIC_CATEGORIES
    rec_prods varchar, --NEXT_PUBLIC_REC_PRODS
    styles_json varchar, --NEXT_PUBLIC_STYLES_JSON

    shipping_enabled boolean, --NEXT_PUBLIC_SHIPPING_ENABLED
    shipping_rule_verified_by varchar, --NEXT_PUBLIC_SHIPPING_RULE_VERIFIED_BY
    shipping_threshold double precision, --NEXT_PUBLIC_SHIPPING_THRESHOLD
    shipping_cost double precision, --NEXT_PUBLIC_SHIPPING_COST

    search_placeholder varchar, --NEXT_PUBLIC_SEARCH_PLACEHOLDER
    footer_msg varchar, --NEXT_PUBLIC_FOOTER_MSG
    footer_cta varchar, --NEXT_PUBLIC_FOOTER_CTA
    footer_phone varchar, --NEXT_PUBLIC_FOOTER_PHONE
    footer_is_wa boolean, --NEXT_PUBLIC_FOOTER_IS_WA
    footer_email varchar, --NEXT_PUBLIC_FOOTER_EMAIL

    seo_description varchar, --NEXT_PUBLIC_SEO_DESCRIPTION
    seo_keywords varchar, --NEXT_PUBLIC_SEO_KEYWORDS

    default_supplier_unit_id uuid, --NEXT_PUBLIC_DEFAULT_SUPPLIER_UNIT_ID
    commerce_display varchar, --NEXT_PUBLIC_COMMERCE_DISPLAY
    account_active boolean, --NEXT_PUBLIC_ACCOUNT_ACTIVE
    currency varchar, --NEXT_PUBLIC_CURRENCY
);

-- Table templates

-- CREATE TABLE IF NOT EXISTS ecommerce_user_<secret_key> (
--     id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
--     first_name varchar NOT NULL,
--     last_name varchar NOT NULL,
--     email varchar(255) NOT NULL,
--     phone_number varchar(255),
--     password varchar(255) NOT NULL,
--     disabled boolean DEFAULT 'f' NOT NULL,
--     created_at timestamp NOT NULL DEFAULT NOW(),
--     last_updated timestamp NOT NULL DEFAULT NOW()
-- );

-- CREATE TABLE IF NOT EXISTS user_session_<secret_key> (
--     session_token text PRIMARY KEY NOT NULL,
--     ecommerce_user_id uuid references ecommerce_user_<secret_key> (id),
--     session_data json,
--     expiration timestamp NOT NULL,
--     created_at timestamp DEFAULT NOW() NOT NULL,
--     last_updated timestamp DEFAULT NOW() NOT NULL
-- );

-- CREATE TABLE IF NOT EXISTS pwd_restore_<secret_key> (
--     restore_token text PRIMARY KEY NOT NULL,
--     ecommerce_user_id uuid REFERENCES ecommerce_user_<secret_key> (id),
--     expiration timestamp NOT NULL
-- );