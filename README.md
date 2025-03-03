# Monorepo

Alima's python monorepository. It contains all Alima's python projects.

## Releases

## Prerequirements

- Python: `^3.10.*`

### Directory structure
* `./domain`: Service interfaces and models
* `./lib`: Shared library code
* `./projects`
  * `monolith`: Monolith legacy API and code

## Setting up the repo locally

Execute this command so VS code or your IDE doesn't complain about 
missing dependencies.
```
poetry install 
```

Note: For ubuntu you might need to install `libpq-dev` to be able to install psycopg2:
```
apt install libpq-dev
```

Run the same command for each library and project

#### Running a project/service

```
cd projects/<service> 
poetry run python -m <service>.main serve
```

#### Adding a local dependency (lib) 

From the project's directory, run:

```shell
poetry add --group dev --editable ../../lib/logging
```

Poetry editable dependencies:
Set develop argument as true in the poetry.toml file:
```
application = {path = "../../lib/application", develop = true}
```

Then run:
```
poetry install
poetry update <package>
```

#### VS Code setup

1. Install the Python extension for VS Code.
2. Go to the file search bar (or press `Cmd + P`) and type `debug `.
3. Select Python: Current File and click in Add Configuration. 
4. Edit the configuration with the following to debug a service:

```json
{
    // Set up Python virtualenv to the one generated from Poetry
    "name": "[DEV] Run Main app",
    "type": "python",
    "python": "<PATH_TO_YOUR_POETRY_ENV>/bin/python",
    "request": "launch",
    "cwd": "${workspaceFolder}/projects/<SPECIFIC_PROJECT_TO_DEBUG>/",
    "module": "<SPECIFIC_PROJECT_TO_DEBUG>.main",
    "subProcess": true,
    "justMyCode": true,
    "args": [
        "serve", "other", "args"
    ],
    "env": {
        "MYENV": "dev"
    }
}
```

5. To setup testing in VS Code, add the following configuration to the the `.vscode/launch.json` file:

```json
{
    "name": "Python: Run pytest current file",
    "type": "python",
    "python": "<PATH_TO_YOUR_POETRY_ENV>/bin/python",
    "request": "launch",
    "program": "${file}",
    "purpose": ["debug-test"],
    "justMyCode": false,
    "console": "integratedTerminal",
    "args": [
        "-vs",
    ],
    "env": {
        "MYENV": "dev"
    }
}
```
  a. And make sure to add the following to the `.vscode/settings.json` file:

  ```json
  {
    "python.formatting.provider": "black",
    "python.testing.pytestArgs": [
        "-vs",
        "<PATH_TO_YOUR_TESTING_FOLDER>"
    ],
    "python.testing.unittestEnabled": false,
    "python.testing.pytestEnabled": true
  }
  ```


### Service Definitions

Domain had only the models and interfaces of the services, instead of the actual buisiness logic.
The actual implementation of the business logic (service) lives in the project/application itself:
```
/domain
    /models
    /interfaces

/project
    /controllers
    /services
    /storage
```

## Definitions

* *Model*: Object that represent a business entity
* *ServiceInterface*: Interface of the business logic to be implemented (easily tranferable to a thrift-interface)
* *Service*: Implementation of the service interface
* *Controller*: Deals only with http requests and validations. Transfer the data in the request to the service
* *Storage*: Interface of the methods to fetch and modify the data
* *StorageImpl*: Implementation of the storage interface

## Resources
https://github.com/dermidgen/python-monorepo
https://medium.com/opendoor-labs/our-python-monorepo-d34028f2b6fa
https://github.com/ya-mori/python-monorepo

## Testing 

Linting

1. Run `make lint` from the root directory to validate correct syntax.

Testing

1. Run `make test` from the root directory to execute all unit and integrations tests
    1. In case you have a local `.env` file to run your project, execute `make local-test` to use that env file.
2. If you want to add more, go to file `tools/tests/pytest` and add the necesary project testing commands to the file. 


## Development and Deployment Workflow

Development

1. Create a new branch for new feature
2. Add new commits 
3. Pull and rebase from master 
4. Run make on the service that is changing to run tests, linting an packaging
5. Manually run `poetry run` in the service to test
6. Send Pull Request (squash commits whenever possible)

Deployment

2. When PR is rebased/merge to master, workflow is triggered
3. Package the service by running make on the service we changed
4. Build docker image 
5. Deploy to staging (task definition)
6. Manual approval to deploy to prod
7. Deploy to prod



