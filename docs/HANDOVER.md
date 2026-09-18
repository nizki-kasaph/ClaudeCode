# 引継メモ（2026-09-19 更新 / ローカル Claude Code セッション）

## 課題
https://chatgpt-lab.com/n/n746a127b4074（AGIラボ「爆速で爆安、判定専用AI『JEV』を徹底解説」）の使い方を整理し、
`nizki-kasaph/ClaudeCode` の `claude/organize-usage-guide-8tdmh6` に置く。

## 現状（2026-09-19）
- 成果物: `~/Downloads/jev-usage-guide.md`（449 行）。**元記事の本文で全面改訂済み。**
  - 元記事 PDF（`~/Downloads/JEV.pdf`、12 ページ・全ページ画像）をローカルで読み、§1〜§5 と §6-1 の途中までを転記した。
  - 前版で「未確認」だった箇所は解消: §2 円換算 3 例（メール 1 通 約 0.016 円 / ペルソナ 150 人×6 問 約 1.2 円 / X 投稿 3,282 件 約 19 円、1 ドル 150 円）、
    §3 事例 5 件（Rinte / Mau Baron / Rinte / Jarrod Watts / Ian Nuttall）、冒頭注記、遅延の実測値、§5 の JS・Cloudflare コード、使いこなしのコツ 4 点、§6-1 の設計。
  - 二次情報（mizchi 実測・SDK README 等）は補足・付録として残し、出典 [^article] と区別してある。
- **PDF は §6-1「質問は2つを1回で」のコード冒頭で切れている。** §6-1 の残りと §6-2〜§6-4（ペルソナ調査・AIウミガメのスープ・ことばクエスト）は未取得。
  記事が有料部分に続くか、PDF 化が途中で止まったかは未確認。
- **GitHub 反映済み（2026-09-19）。** `~/Documents/Claude/JEV-UsageGuide/` を独立リポジトリとして `nizki-kasaph/ClaudeCode` の `main` に直 push した。前セッションのブランチ `claude/organize-usage-guide-8tdmh6` は使わない。

## ブロッカー
1. **§6 の残りが未取得。** 元記事を最後まで PDF 化し直す（ブラウザの「ページ全体を保存」で 12 ページ以降も含める）か、本文を貼り付ける。
2. **JEV を実際に呼べる環境が未整備。** 公式 API は招待待ち（公式サイトに待機リストのフォームは見当たらず、問い合わせ先 hello@typesafe.ai）。今すぐ使えるのは Cloudflare Workers AI（`typesafe/jev`）。OpenRouter 経路はモデルページ 404 で不可（2026-09-19 確認）。

## 次にやること（順番）
1. 元記事の §6 残りを入手し、`jev-usage-guide.md` の「6-1 質問は2つを1回で」以降と「6-2〜6-4（未取得）」を埋める。
2. Cloudflare Workers AI 経由の「判定サービス」Worker と、Python / Node の共通クライアント（環境変数で Cloudflare / 公式 API を切替）を作る。`wrangler dev` でローカル検証してからデプロイ。ユーザーの Cloudflare アカウント有無・プランを確認中。

## 参照ファイル
- `docs/jev-usage-guide.md` … 成果物（改訂版）
- `source/JEV.pdf` … 元記事 PDF（12 ページ、画像のみ。テキスト抽出不可、PyMuPDF でページ画像化して読んだ）
- `docs/HANDOVER.md` … 本メモ
- リポジトリ: https://github.com/nizki-kasaph/ClaudeCode （ローカル `~/Documents/Claude/JEV-UsageGuide/`）
