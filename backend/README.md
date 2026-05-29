# Audio_Analysis_System バックエンド

FastAPI、MySQL、Redis を用いた `Audio_Analysis_System` のバックエンド API です。
API バージョンは `/api/v1`、日時の業務基準は `Asia/Tokyo` です。

## 起動手順

```bash
pip install -r requirements-dev.txt
cp ../.env.example .env
alembic -c alembic.ini upgrade head
uvicorn app.main:app --reload
```

初回起動時にポイントパック、料金プラン、システム設定の初期マスターを投入します。
DB スキーマの変更は `alembic/versions` のマイグレーションとして管理してください。

## 初期管理者

マイグレーション後に次のコマンドで初期管理者を作成または昇格します。

```bash
export AUDIO_ADMIN_EMAIL=admin@example.com
export AUDIO_ADMIN_USERNAME=管理者
export AUDIO_ADMIN_PASSWORD=replace-with-a-strong-password
PYTHONPATH=. python scripts/create_admin.py
```

## 主な API

| 分類 | エンドポイント | 内容 |
| --- | --- | --- |
| 認証 | `POST /api/v1/auth/register` | ユーザー登録、JWT、ハッシュ化 refresh token を発行 |
| 認証 | `POST /api/v1/auth/login` | ログイン、日次ボーナス、JWT、refresh token を発行 |
| 認証 | `POST /api/v1/auth/refresh` | refresh token のローテーション |
| 認証 | `POST /api/v1/auth/logout` | 指定 refresh token の失効 |
| 認証 | `POST /api/v1/auth/logout-all` | 全端末の refresh token を失効 |
| ポイント | `GET /api/v1/points/balance` | ポイント残高取得 |
| ポイント | `GET /api/v1/points/transactions` | ポイント台帳照会 |
| 解析 | `POST /api/v1/songs/analyze` | 音源解析、成功時のみポイント消費 |
| 解析 | `GET /api/v1/songs/history` | 自分の解析履歴検索 |
| 解析 | `GET /api/v1/songs/history/{id}/report` | PDF レポート出力 |
| 購入 | `POST /api/v1/orders/{id}/mock-pay` | モック決済とポイント反映 |
| API キー | `POST /api/v1/api-keys` | API キー発行、平文表示は発行時のみ |
| 管理 | `/api/v1/admin/*` | ユーザー、ロール、ポイント、注文、設定、監査の管理 |
| 運用 | `/health`、`/ready`、`/metrics` | 死活監視、依存サービス確認、Prometheus 指標 |

## 設定値

環境変数は `AUDIO_` プレフィックスを使用します。

| 変数 | 内容 |
| --- | --- |
| `AUDIO_DATABASE_URL` | MySQL SQLAlchemy 接続 URL |
| `AUDIO_REDIS_URL` | Redis 接続 URL |
| `AUDIO_JWT_SECRET_KEY` | JWT 署名秘密鍵。本番ではランダムな長い値を設定 |
| `AUDIO_CORS_ORIGINS` | 許可する Web UI Origin のカンマ区切り |
| `AUDIO_UPLOAD_DIR` | 解析中のみ使用する一時アップロード領域 |
| `AUDIO_MAX_UPLOAD_BYTES` | 最大アップロードサイズ。既定値 50 MB |
| `AUDIO_MAX_AUDIO_DURATION_SEC` | 最大音源秒数。既定値 600 秒 |
| `AUDIO_RATE_LIMIT_REQUESTS` | 通常 API のレート制限回数 |
| `AUDIO_AUTH_RATE_LIMIT_REQUESTS` | 認証 API のレート制限回数 |
| `AUDIO_AUTO_CREATE_TABLES` | テスト / 一時開発専用。運用環境では `false` |

## 品質チェック

```bash
ruff check .
mypy app scripts
bandit -r app scripts -x tests
pytest --cov=app --cov-report=term-missing --cov-fail-under=60
```

## 実装上の扱い

- 原音源は解析後に削除し、メタ情報と表示用の縮約データのみを永続化します。
- 波形とスペクトログラムは Web 表示に必要な粒度まで縮約し、レスポンス肥大化を防ぎます。
- 解析ポイントは結果が成功した時点でのみ台帳へ記録します。
- ポイント残高更新、注文支払い、refresh token ローテーションは DB 行ロックで整合性を守ります。
- 大量並列解析を必要とする本番フェーズでは、`analysis_jobs` をキューワーカーへ接続する設計です。
