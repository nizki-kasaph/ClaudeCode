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
- 前セッション（クラウド）のローカルコミット `f72009d` / `a7c76e7` はコンテナ消滅で失われた前提。GitHub には何も上がっていない。
- `ClaudeCode` リポジトリはこの Mac にクローンされていない（`~/Documents/Claude` 配下・`~` 直下に存在せず）。

## ブロッカー
1. **§6 の残りが未取得。** 元記事を最後まで PDF 化し直す（ブラウザの「ページ全体を保存」で 12 ページ以降も含める）か、本文を貼り付ける。
2. **GitHub 反映は未着手。** リモートが空（ベースブランチなし）のため、`main` を先に作るか、ブランチ直 push で終えるかはユーザー判断。
   この Mac の `gh` は nizki-kasaph で認証済み（scope: repo）、`git ls-remote` も通る（リモートは空を確認）。push 自体は可能で、方針決定待ち。

## 次にやること（順番）
1. 元記事の §6 残りを入手し、`jev-usage-guide.md` の「6-1 質問は2つを1回で」以降と「6-2〜6-4（未取得）」を埋める。
2. push 方針（main を作る / ブランチ直 push）を決めたら、`ClaudeCode` をローカルにクローンして `docs/jev-usage-guide.md` と `docs/HANDOVER.md` を置き、コミット・push・draft PR。

## 参照ファイル
- `~/Downloads/jev-usage-guide.md` … 成果物（改訂版）
- `~/Downloads/JEV.pdf` … 元記事 PDF（12 ページ、画像のみ。テキスト抽出不可、PyMuPDF でページ画像化して読んだ）
- `~/Downloads/HANDOVER.md` … 本メモ
