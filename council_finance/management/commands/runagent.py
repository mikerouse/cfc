from django.core.management.base import BaseCommand, CommandError
from importlib import import_module
import re
from council_finance.agents.base import AgentBase

class Command(BaseCommand):
    help = "Run a registered agent"

    def add_arguments(self, parser):
        parser.add_argument('agent')
        parser.add_argument('--source')
        parser.add_argument('--council_slug')
        parser.add_argument('--field_name')
        parser.add_argument('--year_label')

    def handle(self, *args, **options):
        agent_name = options.pop('agent')
        snake = re.sub(r'(?<!^)(?=[A-Z])', '_', agent_name).lower()
        module_name = f'council_finance.agents.{snake}'
        module = import_module(module_name)
        agent_class = getattr(module, agent_name)
        if not issubclass(agent_class, AgentBase):
            raise CommandError('Invalid agent class')
        agent = agent_class()
        agent.run(**{k: v for k, v in options.items() if v is not None})
