
class DeploymentTemplate:
    def __init__(self, resources):
        self.resources = resources
        self.description = ''
        self.labels = []
        self.empty = len(resources) == 0

    def __str__(self) -> str:
        return "{}".format(self.resources)

    @staticmethod
    def empty():
        return DeploymentTemplate([])


