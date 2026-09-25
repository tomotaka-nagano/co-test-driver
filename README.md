# co-test-driver

組込み製品向けのテストケース生成・実行を、非同期の検証ジョブとして提供する FastAPI アプリケーションです。

## 起動

```powershell
uv sync
uv run uvicorn src.api.app:app --host 0.0.0.0 --port 8000
```

API 仕様は起動後に `http://localhost:8000/docs` で確認できます。

## 検証の開始

```http
POST /verifications
Content-Type: application/json

{
	"workflow_step_id": "system-test-01",
	"requirements": {"path": "res/artifact/requirements.md"},
	"design": {"path": "res/artifact/api.md"},
	"product": {
		"path": "build/product-simulator.exe",
		"sha256": "<64桁のSHA-256>"
	},
	"test_environment_id": "local",
	"idempotency_key": "workflow-123-system-test-01-v1",
	"callback_url": "https://workflow.example.com/hooks/verification",
	"require_approval": false
}
```

成果物参照には `path`、または `CO_TEST_DRIVER_ARTIFACT_ROOT` を基準とする `version` を指定します。`sha256` を指定すると、利用前にファイルを検証します。

状態値は `accepted`、`generating_testcases`、`awaiting_approval`、`executing_tests`、`completed`、`error`、`canceled` です。同一の冪等キーと同一入力は既存ジョブを返し、異なる入力には `409 Conflict` を返します。

## テスト環境

[test-environments.toml](test-environments.toml) の `command` がテストケースごとに実行されます。以下のプレースホルダーを利用できます。

- `{product_path}`: 製品ソフトウェアのパス
- `{testcase_path}`: 1 件分のテストケース JSON
- `{result_path}`: runner が結果を書き込むパス
- `{work_dir}`: ジョブの作業ディレクトリ

runner は `{result_path}` に次の形式の JSON を書き込み、終了コード `0` で終了してください。

```json
{
	"name": "testcase-name",
	"status": "pass",
	"detail": "optional execution detail"
}
```

`status` は `pass`、`fail`、`unable` のいずれかです。終了コードが非 `0`、または結果ファイルがない場合は `unable` として集計されます。

## 設定

| 環境変数 | 既定値 | 説明 |
|---|---|---|
| `CO_TEST_DRIVER_DATA_DIR` | `data` | SQLite DB とジョブ成果物の保存先 |
| `CO_TEST_DRIVER_ARTIFACT_ROOT` | プロジェクトルート | `version` 参照の基準ディレクトリ |
| `CO_TEST_DRIVER_ENVIRONMENTS` | `test-environments.toml` | テスト環境設定ファイル |

完了またはエラー時の Webhook は最大 3 回送信されます。結果や成果物はそれぞれ
`GET /verifications/{id}/result`、`GET /verifications/{id}/artifacts` から再取得できます。

## テスト

```powershell
uv run python -m unittest discover -s tests -v
```