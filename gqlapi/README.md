# Alima's GraphQL API

GraphQL API built on Python 3.10 with [strawberry](https://strawberry.roks/docs/) and [starlette](https://starlett.io). 


## Local Installation

### Prerequisites

- `Python: 3.10.*`
  - `Poetry: 1.4.*`
- `PostgreSQL: >13`
- `MongoDB: > 6`

### Environment variables

```bash
APP_NAME=gqlapi
TESTING  # (bool) Flag to initialize GraphiQL, default False
LOG_LEVEL  # Log lovel

# SQL DB
RDS_HOSTNAME  # Postgres server host
RDS_PORT  # Postgres server port
DB_NAME  # Postgres database name
RDS_PASSWORD  # Postgres password
RDS_USERNAME  # Postgres user name

# Firebase
FIREBASE_SERVICE_ACCOUNT  # Firebase Service Account 
FIREBASE_SECRET_KEY  # Firebase API Key

# Mongo
MONGO_URI  # Atlas Mongo URI

# Stripe
STRIPE_API_KEY # Stripe API Key
STRIPE_API_SECRET # Stripe API SECRET

# Aux Services
HILOS_API_KEY
SENDGRID_API_KEY
ALGOLIA_APP_ID
ALGOLIA_SEARCH_KEY
ALGOLIA_INDEX_NAME

# Godaddy
GODADDY_API_KEY
GODADDY_API_SECRET
```

### Adding Databases (skip if already have them)

1. Install Docker Engine
2. Add a PostgreSQL server
  a. Create first data volume, `docker volume create pgdata`
  a. `docker run -d --name some-postgres -e POSTGRES_PASSWORD=1 -e PGDATA=/var/lib/postgresql/data/pgdata -v pgdata:/var/lib/postgresql/data -p 5432:5432 postgres:13`
3. Add a MongoDB server
  a. Create first data volume, `docker volume create mongodata`
  b. `docker run -d --name some-mongo -v mongodata:/etc/mongo -p 8080:27017 mongo`
4. Create a `core_user` record in PostgreSQL within the `alima_marketplace<_env>` with the following fields: 
  a. First Name: Alima
  b. Last Name: Bot
  c. Email: admin
  d. firebase_id: admin
  e. Phone Number: `''`
5. Execute the catalog script to add categories:
    ```bash
    cd projects/gqlapi
    source .envvars
    poetry run python -m gqlapi.scripts.core.init_category_db --restaurant init --supplier init
    ```


### Steps to Run

1. Run `poetry install` 
2. Set your env vars in the `.env` file and source them.
3. Execute tests to validate all is in order
```
poetry run pytest -vs tests/unit/
poetry run pytest -vs tests/integration/
```
5. To execute GraphQL server run: `poetry run api-server` or `poetry run python -m gqlapi.main`