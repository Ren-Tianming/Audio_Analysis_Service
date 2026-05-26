# RyThM_Music_Analys

<p align="center">
  <img src="frontend/public/rythm-logo.png" alt="RyThM_Music_Analys logo" width="240">
</p>

音楽制作者・DJ・映像クリエイター向けの音源解析 SaaS `RyThM_Music_Analys` です。音源をアップロードすると BPM、Key、Duration、LUFS、RMS、波形、スペクトログラムを解析し、ポイント台帳、解析履歴、PDF レポート、API キー、疑似決済、管理者監査まで一つのプロダクトとして扱えます。

本実装は `audio_analysis_saas_v1_3_requirements_jp.docx` の v1.3 要件を基準にしています。

## 主要機能

- JWT 認証: 登録、ログイン、現在ユーザー取得、パスワード変更、ログアウト導線
- ポイント: 登録時 `+20 PT`、Asia/Tokyo 基準の日次初回ログイン `+10 PT`、解析成功時のみ `-5 PT`
- 音源解析: MP3 / WAV / FLAC / M4A、最大 50 MB・10 分、BPM / Major-Minor Key / LUFS / RMS / 可視化
- 履歴とレポート: 自分の解析履歴検索、詳細、削除、ネオン調 PDF エクスポート
- 商用化導線: ポイントパック、Mock Pay、プラン表示、クーポン基盤、API キー発行・無効化
- 管理者機能: ユーザー状態、ポイント調整、注文状態、全解析履歴、設定、監査ログ API
- UI: React + TypeScript + Vite によるダークパープル / ネオンピンク / ネオンブルーの SaaS 画面

## アーキテクチャ

```text
React / Vite UI
      |
      | REST / Bearer JWT または X-API-Key
      v
FastAPI (/api/v1)
  |- Auth / Point / Commercial / Admin Services
  |- Audio Analyzer (librosa + pyloudnorm)
  |- PDF Report Generator
      |
      v
MySQL 8.x + Alembic
```

アップロードした原音源はランダムな一時ファイル名で保持し、解析の成否にかかわらず処理後に削除します。MySQL にはファイル Hash とメタ情報、縮約した表示用可視化、台帳・監査情報のみを保存します。

## ディレクトリ

```text
backend/
  alembic/                 MySQL スキーママイグレーション
  app/api/routes/          機能別 REST API
  app/core/                設定、DB、セキュリティ、共通エラー
  app/models/              SQLAlchemy モデル
  app/schemas/             Pydantic 入出力
  app/services/            認証、台帳、解析、保存、レポート
  tests/                   受入条件に対応する API テスト
frontend/
  src/                     React UI と API クライアント
docker-compose.yml         MySQL / Backend / Frontend 起動
```

## Docker Compose で起動

Docker 環境がある場合は、MySQL、API、Web UI をまとめて起動できます。

```bash
docker compose up --build
```

起動後:

- Web UI: `http://localhost:8080`
- API ドキュメント: `http://localhost:8000/docs`
- ヘルスチェック: `http://localhost:8000/health`

Compose 起動時にバックエンドコンテナが `alembic upgrade head` を実行します。本番では `.env.example` の JWT シークレットとデータベース認証情報を必ず置換してください。

管理者は DB 作成後に `backend/scripts/create_admin.py` を環境変数付きで実行して初期発行します。詳細は `backend/README.md` を参照してください。

## ローカル開発

### Backend

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example .env
alembic -c alembic.ini upgrade head
uvicorn app.main:app --reload
```

MySQL を使用せず短時間で API を確認する場合のみ、ローカル用設定として次を利用できます。本番用データベースは MySQL を前提とします。

```bash
export AUDIO_DATABASE_URL=sqlite:///./local-dev.db
export AUDIO_AUTO_CREATE_TABLES=true
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

開発サーバーは `/api` を `http://localhost:8000` へプロキシします。別ホストの API を利用する場合は `frontend/.env.example` を参考に `VITE_API_BASE_URL` を設定してください。

## テスト

```bash
cd backend
pytest

cd ../frontend
npm run build
```

バックエンドテストは SQLite の隔離 DB を利用して、登録ボーナス、日次ログイン付与の重複防止、成功解析のみの消費、残高不足拒否、履歴の所有権、Mock Pay 冪等性、API キーの平文非再表示を確認します。

## セキュリティと整合性

- パスワードは `bcrypt` でハッシュ化し、JWT には有効期限を設定します。
- API キーは発行時のみ平文で返却し、データベースには SHA-256 Hash のみ保存します。
- ポイント増減は `point_transactions` に必ず記録し、残高更新と同じトランザクションで処理します。
- 解析結果の確定とポイント消費も同一トランザクションで扱い、同時処理時に残高が負にならないようユーザー行をロックします。
- Mock Pay は既に `PAID` の注文を再処理せず、二重付与を拒否します。
- 一般ユーザーは自分の解析履歴とキーのみ参照できます。管理者の重要操作は `admin_audit_logs` に記録します。

## 次段階の本番拡張

v1.3 の商用化雛形では解析ジョブ状態を保存しつつ、解析処理は API プロセス内で完了させます。高トラフィック運用へ進む段階では、Redis/Celery 等の耐障害キュー、S3 互換オブジェクトストレージ、外部決済、アクセストークン失効リスト、レート制限、監視・アラートを導入する設計です。
