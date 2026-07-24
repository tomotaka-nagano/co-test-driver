import json
from pathlib import Path

from exmgai import Client
from src.schemas.scenario import Scenario


CREATE_PROMPT = """\
あなたはテストエンジニアです。
以下のテストシナリオとインターフェース資料に基づき、シミュレータに投入可能な具体的なテストケースを生成してください。

## 指示
- テストシナリオの summary と viewpoints を網羅するテストケースを作成してください。
- 各 viewpoint に対して、1つ以上のテストケースを作成してください。
- テストケースはインターフェース資料に記載された構造・フィールド・値の仕様に厳密に準拠してください。
- 具体的な値 (温度、水量、時間、状態名など) を設定してください。
- 境界値や異常系も viewpoints に含まれている場合は適切にテストケース化してください。
- 出力は JSON 配列とし、各要素がインターフェース資料で定義された1テストケースに対応するようにしてください。
- JSON 以外のテキストは出力しないでください。

# テストシナリオ
{scenario}

# インターフェース資料
{api_doc}
"""


DESCRIBE_PROMPT = """\
あなたはテストエンジニアです。
以下のテストシナリオ、テストケース (JSON)、およびインターフェース資料に基づき、人間が理解可能なテストケースの記述を Markdown 形式で作成してください。

## 指示
- テストシナリオとの対応関係が明確にわかるように、シナリオ番号・概要を見出しとして含めてください。
- 各テストケースについて以下を記述してください:
  - テストケース名
  - 目的 (どの検証観点に対応するか)
  - 前提条件 (初期状態の内容を自然言語で記述、具体的な数値を含む)
  - 操作手順 (各ステップの操作を自然言語で記述、タイミング・具体的な値を含む)
  - 期待結果 (検証内容を自然言語で記述、定量的な判断基準を含む)
- 定量的な操作・判断基準 (温度、水量、時間、on/off 等) は省略せず明記してください。
- 出力は Markdown テキストのみとし、コードブロックで囲まないでください。

# テストシナリオ
{scenario}

# テストケース (JSON)
{testcases}

# インターフェース資料
{api_doc}
"""


class TestcaseCreator:

    def __init__(self, api_doc_path: str | Path):
        self.api_doc_path = Path(api_doc_path)
        self._api_doc = self.api_doc_path.read_text(encoding='utf-8')

    def generate(self, scenario_path: str | Path) -> list[dict]:
        scenario_path = Path(scenario_path)
        scenarios_data = json.loads(scenario_path.read_text(encoding='utf-8'))

        all_testcases: list[dict] = []
        client = Client('gpt-5.4')

        for i, item in enumerate(scenarios_data['items'], start=1):
            scenario = Scenario.model_validate(item)
            prompt = CREATE_PROMPT.format(
                scenario=json.dumps(item, ensure_ascii=False, indent=2),
                api_doc=self._api_doc,
            )

            response = client.chat.create(prompt)
            result = self._parse_json_array(response.content)

            for tc in result:
                all_testcases.append(tc)

            print(f'シナリオ {i} ({scenario.summary[:30]}...) → {len(result)} テストケース生成')

        return all_testcases

    def describe(self, scenario_path: str | Path, testcases_path: str | Path) -> str:
        scenario_path = Path(scenario_path)
        testcases_path = Path(testcases_path)
        scenarios_data = json.loads(scenario_path.read_text(encoding='utf-8'))
        testcases_list: list[dict] = json.loads(testcases_path.read_text(encoding='utf-8'))

        # シナリオ番号ごとにテストケースをグループ化
        tc_by_scenario: dict[int, list[dict]] = {}
        for tc in testcases_list:
            name: str = tc.get('name', '')
            for i in range(len(scenarios_data['items']), 0, -1):
                prefix = f'S-{i}'
                if name.startswith(prefix) and (
                    len(name) == len(prefix)
                    or name[len(prefix)] in (':', ' ', '-')
                ):
                    tc_by_scenario.setdefault(i, []).append(tc)
                    break

        md_parts: list[str] = []
        client = Client('gpt-5.4')

        for i, item in enumerate(scenarios_data['items'], start=1):
            scenario = Scenario.model_validate(item)
            group = tc_by_scenario.get(i, [])
            if not group:
                continue

            prompt = DESCRIBE_PROMPT.format(
                scenario=json.dumps(item, ensure_ascii=False, indent=2),
                testcases=json.dumps(group, ensure_ascii=False, indent=2),
                api_doc=self._api_doc,
            )

            response = client.chat.create(prompt)
            md_parts.append(response.content)
            print(f'シナリオ {i} ({scenario.summary[:30]}...) → 記述生成完了')

        return '\n\n'.join(md_parts)

    @staticmethod
    def _parse_json_array(text: str) -> list[dict]:
        text = text.strip()
        # コードブロックで囲まれている場合を除去
        if text.startswith('```'):
            text = text.split('\n', 1)[1]
            text = text.rsplit('```', 1)[0].strip()
        return json.loads(text)
