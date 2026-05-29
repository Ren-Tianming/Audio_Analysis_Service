# Audio_Analysis_System

<p align="center">
  <img src="frontend/public/audio-analysis-logo.png" alt="Audio_Analysis_System ロゴ" width="220">
</p>

FastAPI を用いた音源解析 API と、React / TypeScript / Vite を用いたフロントエンドを含むポートフォリオ向けプロジェクトです。
JWT 認証、リフレッシュトークンのローテーション、管理者権限、MySQL、Redis、Alembic マイグレーション、Docker Compose、CI、型チェック、セキュリティスキャン、API テストを備えた構成にしています。

## プロジェクト概要

本システムは、音楽制作者、DJ、映像クリエイター、開発者向けの音源解析 SaaS を想定した Web アプリケーションです。
ユーザーはログイン後に音源をアップロードし、BPM、調性、再生時間、LUFS、RMS、波形、スペクトログラムを確認できます。
解析結果は履歴として保存され、PDF レポート、ポイント台帳、ポイント購入、API キー、管理者監査ログまで一つのプロダクトとして扱えます。

## 主な機能

- ユーザー登録
- ログイン / ログアウト
- JWT アクセストークン
- リフレッシュトークンのローテーション
- リフレッシュトークンのハッシュ保存
- 全端末ログアウト
- 自分のユーザー情報取得
- 音源アップロードと解析
- BPM / 調性 / LUFS / RMS / 波形 / スペクトログラム解析
- 解析履歴の検索、詳細取得、削除
- PDF レポート出力
- ポイント残高とポイント台帳
- 登録ボーナスと日次ログインボーナス
- ポイントパック購入のモック決済
- サブスクリプションプラン表示
- クーポン利用
- API キー発行、ハッシュ保存、失効
- API 利用ログ
- 管理者によるユーザー状態、ロール、ポイント、注文、クーポン、プラン、設定の管理
- 管理者操作の監査ログ
- MySQL 8.4
- Redis ベースのレート制限とプロセス内フォールバック
- DB 行ロックによるポイント残高と注文処理の整合性確保
- Health / Ready エンドポイント
- Request ID 付き JSON ログ
- Prometheus 形式の HTTP 指標エンドポイント
- React / TypeScript / Vite による Web UI
- Alembic による DB マイグレーション
- マイグレーションジョブと API コンテナの分離
- Docker Compose
- GitHub Actions CI
- Ruff / mypy / Bandit / pytest / coverage による品質ゲート
- MySQL バックアップ / リストア用スクリプト
- HTTPS リバースプロキシ設定例

## 技術スタック

### バックエンド

- FastAPI
- SQLAlchemy 2.x
- MySQL 8.4
- PyMySQL
- Redis
- Pydantic v2 / pydantic-settings
- PyJWT
- bcrypt
- Alembic
- librosa / pyloudnorm / NumPy / SciPy
- matplotlib

### フロントエンド

- React
- TypeScript
- Vite
- Nginx

### 開発 / インフラ

- Docker
- Docker Compose
- GitHub Actions
- 環境変数ベース設定
- pytest / httpx
- Ruff
- mypy
- Bandit
- coverage

## システムアーキテクチャ

```mermaid
flowchart LR
    user[利用者 / 管理者] --> browser[Browser]
    browser --> frontend[React Frontend<br/>localhost:8080]
    frontend -->|HTTP /api/v1| proxy[Nginx / ALB / HTTPS]
    proxy --> backend[FastAPI Backend<br/>localhost:8000]

    subgraph application[Backend Application]
        backend --> routes[API ルート / 依存関係]
        routes --> services[サービス層]
        services --> models[SQLAlchemy モデル]
        routes --> ops[Health / Ready / Metrics]
    end

    models -->|READ COMMITTED<br/>SELECT FOR UPDATE| mysql[(MySQL 8.4 / RDS MySQL)]
    services -->|レート制限 / セッション補助| redis[(Redis 7 / ElastiCache Redis)]
    services --> uploads[(一時アップロード領域)]
    ops --> mysql
    ops --> redis
    migrations[Alembic マイグレーションジョブ] --> mysql

    subgraph delivery[品質ゲート]
        actions[GitHub Actions CI] --> static[Ruff / mypy / Bandit]
        actions --> tests[pytest / coverage]
        actions --> frontend_ci[TypeScript lint / Vite build]
    end
```

- Docker Compose と本番想定のアプリケーション実行は MySQL と Redis を利用します。
- 高速な API テストでは SQLite を利用できます。
- ポイント残高更新、注文支払い、リフレッシュトークンのローテーションでは DB 行ロックを使い、同時実行時の整合性を守ります。
- `/ready` は MySQL または Redis が利用不可の場合に `503` を返します。
- `/metrics` は Prometheus 形式で HTTP リクエスト数と処理時間を返します。

## 認証フロー

```mermaid
sequenceDiagram
  participant UI as フロントエンド
  participant API as FastAPI
  participant DB as MySQL
  UI->>API: POST /api/v1/auth/login
  API->>DB: ユーザー検証と refresh token hash の保存
  API-->>UI: access token と refresh token
  UI->>API: Bearer access token 付き API リクエスト
  API-->>UI: access token 期限切れ時は 401
  UI->>API: POST /api/v1/auth/refresh
  API->>DB: refresh token を SELECT FOR UPDATE
  API->>DB: 旧 token を失効し、新 token hash を保存
  API-->>UI: 新しい access token と refresh token
  UI->>API: POST /api/v1/auth/logout-all
  API->>DB: ユーザーの有効 refresh token を全て失効
```

## 解析とポイント消費フロー

```mermaid
sequenceDiagram
  participant UI as フロントエンド / API クライアント
  participant API as FastAPI
  participant Analyzer as 音源解析処理
  participant DB as MySQL
  UI->>API: POST /api/v1/songs/analyze
  API->>DB: uploaded_file / song_analysis / analysis_job を作成
  API->>Analyzer: 一時ファイルを解析
  Analyzer-->>API: BPM / 調性 / LUFS / RMS / 波形 / スペクトログラム
  API->>DB: ユーザー行を SELECT FOR UPDATE
  API->>DB: ポイント台帳を追加し、残高を更新
  API->>DB: analysis_job を SUCCESS に更新
  API-->>UI: 解析結果を返却
```

## 主要ディレクトリ構成

```text
audio-analysis-system/
├─ README.md
├─ .gitignore
├─ .env.example
├─ pyproject.toml
├─ docker-compose.yml
├─ .github/
│  └─ workflows/
│     └─ ci.yml
├─ deploy/
│  └─ nginx/
│     └─ audio-analysis-system.conf
├─ backend/
│  ├─ README.md
│  ├─ Dockerfile
│  ├─ requirements.txt
│  ├─ requirements-dev.txt
│  ├─ alembic.ini
│  ├─ alembic/
│  │  ├─ env.py
│  │  ├─ script.py.mako
│  │  └─ versions/
│  ├─ scripts/
│  │  ├─ create_admin.py
│  │  ├─ backup_mysql.sh
│  │  └─ restore_mysql.sh
│  ├─ tests/
│  │  ├─ conftest.py
│  │  └─ test_acceptance.py
│  └─ app/
│     ├─ main.py
│     ├─ api/
│     ├─ audio/
│     ├─ core/
│     ├─ models/
│     ├─ schemas/
│     └─ services/
├─ frontend/
│  ├─ Dockerfile
│  ├─ nginx.conf
│  ├─ package.json
│  ├─ public/
│  └─ src/
└─ storage/
   └─ uploads/
```

## クイックスタート（Docker Compose）

### 1. リポジトリを取得

```bash
git clone https://github.com/Ren-Tianming/audio-analysis-system.git
cd audio-analysis-system
```

### 2. 環境変数ファイルを作成

```bash
cp .env.example .env
```

`.env` は Git に含めず、MySQL パスワード、Redis 接続先、JWT 署名鍵、CORS 設定などを本番環境に合わせて変更してください。

### 3. 起動

```bash
docker compose up --build
```

Compose では `mysql`、`redis`、`migrations`、`backend`、`frontend` を起動します。
`migrations` コンテナが `alembic upgrade head` を実行し、成功後に API コンテナが起動します。

起動後のアクセス先:

- Frontend: `http://localhost:8080`
- Backend API: `http://localhost:8000`
- Swagger UI: `http://localhost:8000/docs`
- Health: `http://localhost:8000/health`
- Ready: `http://localhost:8000/ready`
- Metrics: `http://localhost:8000/metrics`
- MySQL: `localhost:3306`
- Redis: `localhost:6379`

## ローカル実行

Docker Compose で MySQL と Redis だけを先に起動します。

```bash
docker compose up -d mysql redis
```

### バックエンド

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements-dev.txt
cp ../.env.example .env
alembic -c alembic.ini upgrade head
uvicorn app.main:app --reload
```

短時間で API を確認する場合のみ SQLite も利用できます。

```bash
export AUDIO_DATABASE_URL=sqlite:///./local-dev.db
export AUDIO_AUTO_CREATE_TABLES=true
export AUDIO_REDIS_URL=
```

### フロントエンド

```bash
cd frontend
npm install
npm run dev
```

開発サーバーは `/api`、`/health`、`/ready`、`/metrics` を `http://localhost:8000` へプロキシします。

## 初期管理者の作成

マイグレーション後に次のコマンドで初期管理者を作成または昇格します。

```bash
cd backend
export AUDIO_ADMIN_EMAIL=admin@example.com
export AUDIO_ADMIN_USERNAME=管理者
export AUDIO_ADMIN_PASSWORD=replace-with-a-strong-password
PYTHONPATH=. python scripts/create_admin.py
```

## 環境変数

| 変数 | 説明 | 例 |
|---|---|---|
| `AUDIO_APP_NAME` | アプリケーション名 | `Audio_Analysis_System` |
| `AUDIO_ENVIRONMENT` | 実行環境 | `development` |
| `AUDIO_LOG_LEVEL` | ログレベル | `INFO` |
| `AUDIO_DATABASE_URL` | SQLAlchemy 接続 URL | `mysql+pymysql://audio_user:audio_password@localhost:3306/audio_analysis?charset=utf8mb4` |
| `AUDIO_REDIS_URL` | Redis 接続 URL | `redis://localhost:6379/0` |
| `AUDIO_JWT_SECRET_KEY` | JWT 署名鍵。本番では必ず変更 | `replace-with-a-random-secret-at-least-32-characters` |
| `AUDIO_JWT_EXPIRE_MINUTES` | access token の有効期間 | `60` |
| `AUDIO_REFRESH_TOKEN_EXPIRE_DAYS` | refresh token の有効期間 | `30` |
| `AUDIO_CORS_ORIGINS` | CORS 許可 origin | `http://localhost:5173,http://localhost:8080` |
| `AUDIO_UPLOAD_DIR` | 一時アップロードディレクトリ | `storage/uploads` |
| `AUDIO_RATE_LIMIT_REQUESTS` | 通常 API のレート制限回数 | `60` |
| `AUDIO_AUTH_RATE_LIMIT_REQUESTS` | 認証 API のレート制限回数 | `10` |
| `AUDIO_RATE_LIMIT_WINDOW_SECONDS` | レート制限の時間枠 | `60` |
| `AUDIO_AUTO_CREATE_TABLES` | テスト / 一時開発用の自動テーブル作成 | `false` |

## テストと品質チェック

### バックエンド

```bash
cd backend
ruff check .
mypy app scripts
bandit -r app scripts -x tests
pytest --cov=app --cov-report=term-missing --cov-fail-under=60
```

### フロントエンド

```bash
cd frontend
npm run lint
npm run build
```

## バックアップとリストア

```bash
cd backend
MYSQL_HOST=127.0.0.1 MYSQL_USER=audio_user MYSQL_PASSWORD=audio_password ./scripts/backup_mysql.sh
MYSQL_HOST=127.0.0.1 MYSQL_USER=audio_user MYSQL_PASSWORD=audio_password ./scripts/restore_mysql.sh ./backups/audio_analysis_YYYYMMDD_HHMMSS.sql.gz
```

本番環境では RDS の自動バックアップとポイントインタイムリカバリを優先してください。
スクリプトは低コスト構成や緊急時の手動エクスポート用です。

## HTTPS / リバースプロキシ

Nginx の設定例は `deploy/nginx/audio-analysis-system.conf` にあります。
利用時は次の値を環境に合わせて変更してください。

- `server_name example.com www.example.com`
- Let’s Encrypt の証明書パス
- バックエンドとフロントエンドの upstream

ローカル Compose の `frontend/nginx.conf` は `/api`、`/health`、`/ready`、`/metrics` をバックエンドへプロキシします。

## 低コスト AWS デプロイ案

データベース、バックエンド、フロントエンドを分離しつつ、初期費用を抑える構成です。

```text
Route53 / 独自ドメイン
        ↓
ACM + ALB または EC2 Nginx + Let's Encrypt
        ↓
EC2 Docker Compose または ECS Fargate
        ↓
RDS MySQL
        ↓
ElastiCache Redis
```

### 最小コスト構成

- フロントエンド: 最小コストでは S3 + CloudFront。初期検証では EC2 上の Nginx 配信でも可。
- バックエンド: まずは単一 EC2 `t4g.small` で Docker Compose。安定後に ECS Fargate へ移行。
- データベース: RDS MySQL 単一 AZ、`db.t4g.micro` または `db.t4g.small` から開始。
- Redis: ElastiCache Redis 単一ノード `cache.t4g.micro` から開始。
- HTTPS: ALB を使う場合は ACM。ALB を省く場合は EC2 Nginx + Let’s Encrypt。
- ドメイン: Route53 でホストゾーンを管理し、ALB または EC2 Elastic IP へ向ける。

### 本番運用の最低ライン

- `AUDIO_JWT_SECRET_KEY` は十分に長いランダム値にする。
- RDS と Redis は private subnet に置き、バックエンドの security group からのみ接続を許可する。
- バックエンドは ALB または Nginx 経由で公開し、DB のパブリックアクセスは無効化する。
- RDS の自動バックアップを有効化し、少なくとも 7〜14 日保持する。
- CloudWatch Logs にコンテナログを集約する。
- `/ready`、5xx、CPU、メモリ、RDS ストレージ使用量にアラートを設定する。
