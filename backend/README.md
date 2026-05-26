# RyThM_Music_Analys Backend

FastAPI と MySQL を用いた音源解析 SaaS の API 実装です。API バージョンは `/api/v1`、日時の業務基準は `Asia/Tokyo` です。

## 起動手順

```bash
pip install -r requirements.txt
cp ../.env.example .env
alembic -c alembic.ini upgrade head
uvicorn app.main:app --reload
```

初回起動時にポイントパック、料金プラン、システム設定の初期マスターを投入します。DB スキーマの変更は `alembic/versions` のマイグレーションとして管理してください。

初回の管理者アカウントは、マイグレーション後に次のように作成します。

```bash
export AUDIO_ADMIN_EMAIL=admin@example.jp
export AUDIO_ADMIN_USERNAME=Administrator
export AUDIO_ADMIN_PASSWORD=replace-with-a-strong-password
PYTHONPATH=. python scripts/create_admin.py
```

## 主な API

| 分類 | エンドポイント | 内容 |
| --- | --- | --- |
| 認証 | `POST /api/v1/auth/register` | 登録と 20 PT 付与 |
| 認証 | `POST /api/v1/auth/login` | JWT 発行と日次 10 PT 付与 |
| ポイント | `GET /api/v1/points/transactions` | 台帳照会 |
| 解析 | `POST /api/v1/songs/analyze` | 音源解析、成功時 5 PT 消費 |
| 解析 | `GET /api/v1/songs/history` | 自己履歴の検索 |
| 解析 | `GET /api/v1/songs/history/{id}/report` | PDF レポート |
| 購入 | `POST /api/v1/orders/{id}/mock-pay` | 疑似決済とポイント反映 |
| API | `POST /api/v1/api-keys` | API キー発行 |
| 管理 | `/api/v1/admin/*` | ユーザー、ロール、ポイント、注文、クーポン、プラン、設定、監査 API |

## 設定値

環境変数は `AUDIO_` プレフィックスを使用します。

| 変数 | 内容 |
| --- | --- |
| `AUDIO_DATABASE_URL` | MySQL SQLAlchemy 接続 URL |
| `AUDIO_JWT_SECRET_KEY` | JWT 署名秘密鍵。本番ではランダムな長い値を設定 |
| `AUDIO_CORS_ORIGINS` | 許可する Web UI Origin のカンマ区切り |
| `AUDIO_UPLOAD_DIR` | 解析中のみ使用する一時アップロード領域 |
| `AUDIO_MAX_UPLOAD_BYTES` | 最大アップロードサイズ。既定値 50 MB |
| `AUDIO_MAX_AUDIO_DURATION_SEC` | 最大音源秒数。既定値 600 秒 |
| `AUDIO_AUTO_CREATE_TABLES` | テスト/一時開発専用。運用環境では `false` |

## 実装上の扱い

- 原音源は解析後に削除し、メタ情報と表示用の縮約データのみを永続化します。
- 波形とスペクトログラムは Web 表示に必要な粒度まで縮約し、レスポンス肥大化を防止します。
- 解析ポイントは結果が成功した時点でのみ台帳へ記録します。
- 大量並列解析を必要とする本番フェーズでは `analysis_jobs` をキュー Worker に接続することを前提にしています。
