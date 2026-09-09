# streamer-name-dict

配信者（VTuber・実写ストリーマー）の活動名を IME で変換できるようにする、出典付き・無料の変換辞書です。
データモデル・運用方針の詳細は [DESIGN.md](./DESIGN.md) を参照してください。

### はじめての方へ

配信者の名前は IME でうまく変換できないことが多いので、読み仮名の辞書をみんなで持ち寄って育てています。
辞書に足りない名前があれば下の「データの追加方法」から、逆に自分の名前を載せてほしくない場合は
「削除・訂正申請」から気軽にどうぞ。

## 収録件数

収録件数は固定せず増減します。現在の件数は `python build.py` を実行した際の標準出力
（「収録 N 件」）が最新の値です。

## 収録の原則

1. **活動名のみ**。本名・旧名義は載せません（本人が現在名乗っている名前だけ）。
2. **読みは本人・所属組織の公式情報、または出典の明示された公開文献（Wikipedia・Wikidata）に
   由来するものだけ**。推定した読みは載せません。
3. **全件に出典 URL を必ず入れます**（あとから確かめ直せるようにするため。`data/entries.tsv` のみ。
   `data/aliases.tsv` の愛称・表記揺れは出典を求めません。下記「愛称・表記揺れ」参照）。
4. **削除・訂正申請は本人または所属組織からなら無条件・即時**。理由は問いません。削除後は配布物に含めません（`data/` の管理用の行は `status=removed` として残ります）。
5. **データは CC0 1.0（[LICENSE-DATA](./LICENSE-DATA)）で公開します**。

## 愛称・表記揺れ（`data/aliases.tsv`）

`data/entries.tsv` は「公式の読み・出典あり」の行だけを載せています。それとは別に、
`data/aliases.tsv` に**愛称**（表記が正式名と異なるニックネーム）と**表記揺れ**
（同じ表記に対して通用している別の読み）を収録しています。

- **正式な読みとしては扱いません**。IME 辞書には含めますが、出典は求めません。
- **本人が望まない愛称は、正式名と同じ手続き（Issue）で削除申請できます**。
  `person_id` 単位で扱うため、正式名の削除申請が通ると、その人物の愛称・表記揺れも一緒に消えます。
- データモデルの詳細は [DESIGN.md](./DESIGN.md#aliases愛称・表記揺れ出典を求めない補助情報) を参照してください。

## 使い方（各 IME への取り込み）

生成済みの辞書ファイルは [Releases](../../releases) に添付します（`dist/` はリポジトリには含まれません。生成物のため）。
自分でビルドする場合は下記「開発」を参照してください。

| IME | ファイル | 取り込み手順（概要） |
|---|---|---|
| Microsoft IME | `streamer_dict_msime.txt` | 「Microsoft IME ユーザー辞書ツール」→ ツール → テキストファイルからの登録 → `streamer_dict_msime.txt` を選択 |
| Google 日本語入力 / Mozc | `streamer_dict_google_mozc.txt` | 「辞書ツール」→ 管理 → 新規辞書にインポート → `streamer_dict_google_mozc.txt` を選択（文字コード UTF-8） |
| ATOK | `streamer_dict_atok.txt` | 「ATOK Pad」または「単語登録」→ 単語一括登録 → `streamer_dict_atok.txt` を選択 |
| SKK | `streamer_dict_skk.txt` | 個人辞書 or `~/.skk-jisyo-streamer` 等に配置し、`skk-search-prog-list` や `skk-jisyo-code` の設定で読み込む |

macOS 標準の日本語入力（ことえり／日本語入力）は本辞書の対象外です。

Microsoft IME・ATOK・SKK での実機確認は募集中です（Issue でお知らせください）。

## データの追加方法

PR か Issue でお知らせください。

### PR で追加する

1. `data/entries.tsv` に行を追加してください（列の意味は [DESIGN.md](./DESIGN.md#データモデル) 参照）。
2. `reading_source` は定義済みの値（信頼度順: `org_kana` / `kana_surface` / `self_channel_title` / `self_profile` / `wikidata` / `wikipedia` / `org_romaji` / `pr_manual`）から選んでください。
3. `source_url` に読みを確認できる URL を入れてください。あとから読みを確かめ直せるようにしたいので、これだけは省略できません。
4. PR を送ってください。レビューでは出典 URL を実際に開いて読みを確認します。
   PR に慣れていない場合は [追加希望の Issue](../../issues/new?template=addition.yml) からでも構いません。

### 愛称・表記揺れの追加（`data/aliases.tsv`）

1. `data/aliases.tsv` に行を追加してください（列: `person_id` / `surface` / `reading` / `kind` / `note` / `added`）。
2. `person_id` は `data/entries.tsv` に既に存在するものを使ってください（新しい人物はこのファイルだけでは作れません）。
3. `kind` は `nickname`（表記が正式名と異なる愛称）か `reading_variant`（表記は正式名と同じで読みだけ別）のどちらかです。
   `reading_variant` の場合、`surface` は `entries.tsv` の当該人物の表記と一致させてください。
4. **出典 URL は不要です**（愛称・表記揺れは出典を求めない情報のため）。そのまま PR を送ってください。

## 削除・訂正申請

ご本人または所属組織の方は、GitHub の Issue でお知らせください。理由は問いません。
本人性の確認は「公式チャンネル・公式 X からの言及」または「所属組織からの連絡」のみで足ります（過剰な本人確認は求めません）。

- [削除申請](../../issues/new?template=removal.yml)
- [訂正申請](../../issues/new?template=correction.yml)（正式名の読み・表記の訂正。出典は何でも構いません——本人の発言・X の bio・公式ページなど、
  確認できる URL が 1 つあれば足ります。厳格な一次資料は求めません。
  ご本人からの申請で URL を示せない場合は、Issue 本文自体を出典として扱います）
- [追加希望（正式名）](../../issues/new?template=addition.yml)（entries.tsv。出典の考え方は訂正申請と同じです）
- [追加希望（愛称・略称）](../../issues/new?template=alias-addition.yml)（aliases.tsv。**出典不要**）

個人勢の追加や PR の書き方は [CONTRIBUTING.md](./CONTRIBUTING.md) を参照してください。

## 開発

```bash
python3 -m venv .venv   # または任意の venv
source .venv/bin/activate
pip install -r requirements-dev.txt   # 実行時依存のみでよければ requirements.txt
python -m pytest
ruff check .
python build.py
```

- `lib/entries.py`: `data/entries.tsv` の読み込みとスキーマ定義
- `lib/aliases.py`: `data/aliases.tsv`（愛称・表記揺れ）の読み込みとスキーマ定義
- `lib/validate.py`: 入力検証（必須列・reading のひらがな判定・`reading_source`/`status`/`kind` の定義内チェック・重複検出・aliases の person_id 存在確認）。`python -m lib.validate data/entries.tsv data/aliases.tsv` で単体実行可能
- `lib/formats.py`: 各 IME 形式の生成
- `lib/promote.py`: メンテナが手元でまとめた TSV → entries のマージロジック（メンテナ用・通常は使いません。純関数。CLI は `promote.py`）
- `build.py`: CLI（検証 → 生成。entries と aliases を合わせて出力。検証エラーがあれば非ゼロ終了・`dist/` は作らない）
- `promote.py`: メンテナ用 CLI（通常は使いません。手元でまとめた TSV を `data/entries.tsv` へ取り込む。検証エラー・衝突があれば非ゼロ終了・書き込まない）

## ライセンス

- データ（`data/entries.tsv`・`data/aliases.tsv` および生成される辞書ファイル）: [CC0 1.0](./LICENSE-DATA)
- コード（`lib/`・`build.py`・テスト等）: [MIT License](./LICENSE)
