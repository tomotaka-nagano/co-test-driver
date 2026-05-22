from exmgai import Client
from src.schemas.scenario import Scenarios


CREATE_PROMPT = """

# 

# テストシナリオ導出観点

"""


class ScenarioCreator:

    def create(self):
        client = Client('gpt-5.4')

    def refine(self):
        pass
