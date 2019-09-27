
def add_environment_secret(environment_vars, secret_name: str, data: map):
    def _key_to_secret_ref(env_name, secret_content_key):
        return {
            'name': env_name,
            'valueFrom': {'secretKeyRef': {'name': secret_name, 'key': secret_content_key}}}
    secret_vars = list(map(lambda item: _key_to_secret_ref(item[0], item[1]), data.items()))
    return environment_vars + secret_vars


def set_environment_variable(environment_vars, name, value):
    if len(list(filter(lambda x: x['name'] == name, environment_vars))) > 0:
        return list(map(
            lambda x:
            {'name': name, 'value': value}
            if x['name'] == name
            else x,
            environment_vars))
    else:
        return environment_vars + [{'name': name, 'value': value}]
