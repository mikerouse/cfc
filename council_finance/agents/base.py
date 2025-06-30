class AgentBase:
    """Base class for all agents."""
    name = "AgentBase"

    def run(self, **kwargs):
        raise NotImplementedError("Agents must implement run()")
