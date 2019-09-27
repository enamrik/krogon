# Krogon

Krogon is a DSL that encodes repeatable patterns we observed while using K8s. Krogon
also has plugins that encode repeatable patterns in services that run on K8s.

## Requirements

* python3

## Plugins

* [Krogon-GCD](https://github.com/enamrik/krogon-gocd)
* [Krogon-Istio](https://github.com/enamrik/krogon-istio)

## Installation

Install python3:

To use [pyenv](https://github.com/pyenv/pyenv) to install python, run:

```bash
brew install pyenv
pyenv install 3.7.4
eval "$(pyenv init -)" # put in your rc file (e.g. ~/.zshrc)
```

Setup your virtual environment:

```bash
pip install virtualenv
virtualenv .venv  --no-site-packages
. ./.venv/bin/activate
```

Install Krogon:

```bash
pip install -e "git+ssh://git@github.com/enamrik/krogon.git#egg=krogon"
```

## Usage

### DSL

Krogon is a simple step runner. There are two steps as of now: a template generator and a template runner.

### Template Generator Step

### gen_template:

a template generator. Templates are put in a folder called `output` in the current directory.

e.g.

```python
from krogon import krogon
from krogon.steps.k8s import gen_template, micro_service

krogon(
    run_steps=[
        gen_template(
            templates = [
            ...
        ])
    ]
)
```

Args:

* `templates`: An array of templates for which to generate yaml files.

### Template Runner Step

### run_in_cluster:

a template runner that executes templates in one or more clusters.

e.g.
```python
import os
from krogon import krogon
from krogon import config
from krogon.steps.k8s import run_in_cluster, micro_service

krogon(
    run_steps=[
        run_in_cluster(
            named='prod-us',
            templates = [
                ...
        ])
    ],
    for_config=config(
        project_id=os.environ['PROJECT_ID'],
        service_account_b64=os.environ['SERVICE_ACCOUNT_B64']
    )
)
```
Args:

* `named`: A tag used to filter which cluster(s) to deploy to. In the example, any cluster
which name contains the text 'prod-us', e.g. 'prod-us-east' or 'prod-us-west', will be deployed to.

* `templates`: An array of templates for which to generate yaml files.

* `for_config:project_id`: The project_id of the project where your clusters live.
Can also be set via environment variable: `KG_PROJECT_ID=prod-project`.

* `for_config:service_account_b64`: A base 64 string of the service account key file. Can be produced by `$(base64 ~/Documents/prod-access.json)`.
Can also be set via environment variable: `KG_SERVICE_ACCOUNT_B64=$(base64 <path-to-file>)`.

* `for_config:output_template`: If True, wil generate each cluster's yaml file in the output folder. Default is false. 
Can also be set via environment variable: `KG_TEMPLATE=true`.

* `for_config:delete`: If True, will delete the resources created.
Can also be set via environment variable: `KG_DELETE=true`.

If you specify all `for_config` arguments via environment variables, you can leave out the `for_config` argument entirely.


### Template types

### micro_service:

a template for generating resources that make up a service.

e.g.
```python
from krogon import krogon
from krogon.steps.k8s import gen_template, micro_service

krogon(
    run_steps=[
        gen_template([
            micro_service(
                name='test-app',
                image='gcr.io/prod-project/test-app:1.0.0',
                app_port=3000)
        ])
    ]
)
```

Args:

* `name`: The name of the service. It will be used to name other resources.

* `image`: The full image url of the container image.

* `app_port`: The port the container will be listening on. This is different from the service port.

Optionals:

* `with_service_port(port: int)`: The port the service will be made available on. Default is 80.

* `with_replicas(min: int, max: int)`: The min/max replicas allowed to scale to. Default is 1 to 3.

* `with_command(command_args: List[str])`: The [container args](https://kubernetes.io/docs/tasks/inject-data-application/define-command-argument-container/). Default is none.

* `with_environment_variable(name: str, value: str)`: The environment variables set for the container process. 

* `with_environment_secret(secret_name: str, data: dict)`: Adds a reference to a secret. `secret_name` is the name of a secret and data is a map where `key` 
is the environment variable name and `value` is the key of the secret part.

### secret: 

a template to generate a secret.

Args:

* `name`: The name of the secret.

* `data`: A map of the key and value of key parts. 

* `already_b64`: True if the value of key parts don't need to be base64 encoded. Default is false.

### cron_job:

a template for creating cron jobs.

* `name`: The name of the job.

* `image`: The full image url of the container image.

Optionals:

* `with_command(command_args: List[str])`: The [container args](https://kubernetes.io/docs/tasks/inject-data-application/define-command-argument-container/). Default is none.

* `with_environment_variable(name: str, value: str)`: The environment variables set for the container process. 

* `with_environment_secret(secret_name: str, data: dict)`: Adds a reference to a secret. `secret_name` is the name of a secret and data is a map where `key` 

* `with_schedule`: The cron pattern that determines how often the job runs. The default is * * * * * (disabled).


