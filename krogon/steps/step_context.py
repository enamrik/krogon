
class StepContext:
    def __init__(self, params: dict):
        self.params = params

    def __str__(self) -> str:
        return "StepContext{}".format(self.params)

    def __eq__(self, other) -> bool:
        return isinstance(other, StepContext) and self.params == other.params

    def set_param(self, key: str, value):
        new_params = dict(self.params, **{key: value})
        return StepContext(new_params)

    def get_param(self, key: str):
        return self.params[key] if key in self.params else None


