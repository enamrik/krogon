
class DeploymentTemplate:
    def __init__(self, resources):
        self.resources = resources
        self.description = ''
        self.labels = []

    def __str__(self) -> str:
        return "{}".format(self.resources)


