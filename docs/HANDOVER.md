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

## 2026-09-19 深夜の到達点
- **TypeSafe 公式 API で JEV の実測に成功。** 待機リスト送信直後に console.typesafe.ai にログインでき、API キーを発行。
  `.env` に `TYPESAFE_API_KEY` を追加し、`python3 client/jev_client.py`（既定 `JEV_BACKEND=typesafe`）で Noul / Choice / Score が返った。
  応答時間: 初回 600〜650 ms、接続再利用で 205〜269 ms。日本語 state で問題なし。詳細はガイド「本書での実測」。
- Cloudflare 経路は課金ブロックのため未実測のまま（コードは残してある）。
- Claude Code に TypeSafe プラグイン導入済み（typesafe@typesafe-ai v0.5.7、user スコープ）。新しいセッションから `typesafe-ai` スキルが使える。

## 2026-09-19 朝: 組み込み先 1（support@ 取り込み）の実測
- VM の gmail_intake.py を `vm_samples/`（git 除外）に取得。台帳は件名・差出人・結果のみで本文なし。
  読み取り専用の `vm_samples/dump_support_samples.py` で直近 60 日・40 通の本文を取得（Gmail は list/get のみ）。
- **現状の事実**: 40 通中 38 通が「イベント No. を特定できず」で捨てられ、顧客の実返信はほぼ未取り込み。唯一 posted の 1 通は
  TOTO の自動送信（受付 No を問い合わせ No と誤検出）。
- **JEV 実測（Noul is_customer / Choice category / Score urgency、40 通 11.1 秒）**: 自動送信・広告・求人は is_customer 0.02〜0.09、
  顧客本人の返信は 0.78〜0.93 で明確に分離。0.24〜0.53 の境界帯は法人客の担当者・取引先・社内（林誠一/laterre、YABE、Liu Wenwen、TRIO STYLE、
  村上良一の Re:）で、「顧客」の定義（法人客の窓口を含めるか）を質問文に明記すれば解消できる見込み。緊急度は「明日の予約の件」1.64、
  キャンセル 0.95、決済依頼への返信 0.95 と妥当。結果は `vm_samples/jev_results.json`。
- 組み込み先 3（台帳検索）の実質問を VM の transcript_events（各 agent の openclaw-agent.sqlite、列 event_json）から 42 件抽出し
  `vm_samples/suzuki_queries.txt` に保存（git 除外）。型は「解約者の中から〈自由記述の条件〉でピックアップ」が大半:
  解約理由＝引越し／不明／スタッフ退職、アンケート回答の有無、特記事項の有無、欠勤・遅刻イベントの有無と原因（迷子・乗り間違い・時間間違い）。
  JEV の役割は pinay_pick の各行の自由記述（解約理由・更新記事抜粋・特記事項）に対する Noul / Choice の一括判定（1 行 1 リクエストにまとめる）。
- VM の環境変数は `~/.openclaw/.env` が存在（中身未読）。配備時はここに TYPESAFE_API_KEY を足す想定。
- 組み込み先 1 の方針: 境界帯の差出人は「全部顧客」（法人客の窓口を含む）。No. 無し顧客メールは差出人メールアドレスから台帳・イベントを引く方針だが、
  **訂正: 抽出台帳 `/home/NIZ-ki/pinay_ledger/pinay_ledger.sqlite3`（VM、毎朝取り込み）の customers テーブルに `email` 列あり（約 2.5 万行）。**
  events テーブル（customer_id, event_no, status, progress, occurred_at, category_*）で顧客→イベントを引ける。
  40 通の差出人で照合すると 21 件が customers に一致（うち 19 件はイベントあり）。未一致 19 件の大半は広告・自動送信。
  → 設計: JEV is_customer ≥ 閾値 → 差出人 email で customers → 直近イベントへ記録。顧客だが未一致なら Chat 通知（人が No. を付ける）。
- 組み込み先 2（中止・指摘の検知）はローカル実測済み: 言い換え全検知、引っかけ否定 9 件全て非検知、境界帯は既存キーワードで補完する二段構成。

## ブロッカー（解消済みを含む履歴）
1. **§6 の残りが未取得。** 元記事を最後まで PDF 化し直す（ブラウザの「ページ全体を保存」で 12 ページ以降も含める）か、本文を貼り付ける。
2. **Cloudflare 経由の呼び出しは残高待ち。** `client/jev_client.py` を作成し、正しい REST 形式（`/ai/run` に `{"model","input"}`）まで到達したが、
   `402 Insufficient balance; add money to your gateway or use BYOK` で止まっている。第三者モデルは Workers AI の Neuron 無料枠ではなく
   AI Gateway の前払いクレジットで課金される。ユーザーが AI Gateway > Credits Available > Manage > Top-up credits で入金すれば、
   `python3 client/jev_client.py` がそのまま通る見込み。`.env`（gitignore 済み）に CLOUDFLARE_ACCOUNT_ID / CLOUDFLARE_API_TOKEN 設定済み、トークンは verify で active を確認。
3. **Cloudflare の課金がアカウント側でブロック（2026-09-19）。** AI Gateway credits の Top-up（最小 $10＋手数料 $1、最大 $50）で
   「決済手段を認証できませんでした」、カード追加で「There was an error processing your card」。ユーザーは複数のカードで普段の海外決済も
   問題なし、登録はできるが決済だけ通らない。**PayPal も不可（ユーザー確認済み）。** 残る手段は Cloudflare Billing サポートへの問い合わせのみ。
4. **TypeSafe 公式は招待制（invite-only）。** console.typesafe.ai は「Sorry, TypeSafe is currently invite-only. For an invite, join the waitlist at typesafe.ai」。
   待機リストは typesafe.ai トップ右上の「Join Waitlist」（ページ読込後に出る。メール 1 欄のフォーム）。Discord: https://discord.gg/typesafe
5. **第 3 の経路: Vercel AI Gateway** に `typesafe-ai/jev` が同単価（$0.042/1M 入力）で掲載。AI SDK の `evaluate({model, state, questions})` 形式。
   Vercel アカウントと課金設定が必要。ユーザーの Vercel アカウント有無は未確認。OpenRouter は 404 で不可。 公式 API は招待待ち（公式サイトに待機リストのフォームは見当たらず、問い合わせ先 hello@typesafe.ai）。今すぐ使えるのは Cloudflare Workers AI（`typesafe/jev`）。OpenRouter 経路はモデルページ 404 で不可（2026-09-19 確認）。

## 次にやること（順番）
1. 元記事の §6 残りを入手し、`jev-usage-guide.md` の「6-1 質問は2つを1回で」以降と「6-2〜6-4（未取得）」を埋める。
2. 公式 API で実測済み。次は実用途への組み込み（メール返信要否判定など）。コンソールの Usage で消費量・課金の表示を確認し、料金節に反映する。

## 参照ファイル
- `docs/jev-usage-guide.md` … 成果物（改訂版）
- `source/JEV.pdf` … 元記事 PDF（12 ページ、画像のみ。テキスト抽出不可、PyMuPDF でページ画像化して読んだ）
- `docs/HANDOVER.md` … 本メモ
- リポジトリ: https://github.com/nizki-kasaph/ClaudeCode （ローカル `~/Documents/Claude/JEV-UsageGuide/`）
