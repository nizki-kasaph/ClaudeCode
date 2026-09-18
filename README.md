# JEV-UsageGuide

TypeSafe AI の判定専用モデル JEV の使い方を、AGI ラボの解説記事（2026-09-18）を軸に整理したもの。
今後、メール仕分け・分類・採点など「判定だけ欲しい」処理を他プロジェクトへ組み込むときの参照資料として使う。

## 構成

| パス | 内容 |
| --- | --- |
| `docs/jev-usage-guide.md` | 本体。元記事 §1〜§5・§6-1 途中までを転記し、公式 SDK・実測レポートで補足 |
| `docs/HANDOVER.md` | 作業の引継メモ（未取得箇所・push 方針など） |
| `source/JEV.pdf` | 元記事の PDF（12 ページ・画像のみ。§6-1 途中で終了） |
| `client/jev_client.py` | Python クライアント。`JEV_BACKEND=typesafe`（既定）/ `cloudflare` を環境変数で切替。`.env` に認証情報 |

## 未完了

- 元記事 §6-1 の後半と §6-2〜§6-4 は PDF に含まれておらず未転記（2026-09-19 時点、サイト側エラーで再取得できず）。
- Cloudflare 経由は課金ブロックで未実測。公式 API は 2026-09-19 に実測済み（`client/jev_client.py`、既定経路）。

## リポジトリ

https://github.com/nizki-kasaph/ClaudeCode（`main` に直 push、2026-09-19）

## 他プロジェクトで使うときの最短経路

1. `docs/jev-usage-guide.md` §5「基本の形」の JS 例をコピーし、`state` と `questions` を差し替える。
2. 日本から呼ぶなら「注意点」の 6 つのコツ（質問をまとめる・並列・接続再利用 など）を先に読む。
3. 閾値やフォールバックの設計は付録「実装時の落とし穴」に従う。
