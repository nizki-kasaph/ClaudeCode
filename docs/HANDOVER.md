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

## 2026-09-19 午後: 組み込み先 1 を実装（ローカル検証済み・VM 未配備）
- 実装先はワークスペースの正本 `~/Documents/Claude/OpenClaw_QA_chat/backend/`（VM `~/mugi-relay/` と同一だったことを diff で確認）。
  - 新規 `support_triage.py`: JEV 3 問（Noul is_customer / Choice category 7 択 / Score urgency 3 段）を 1 リクエスト、
    台帳 `pinay_ledger.sqlite3` を読み取り専用で開き `customers.email`（小文字・trim 比較）→ その顧客の最新イベント
    （`COALESCE(updated_at, registered_at, occurred_at)` 降順、`deleted_at IS NULL`）。閾値は冒頭の定数 `CUSTOMER_THRESHOLD=0.15` / `URGENT_THRESHOLD=1.5`。
  - `gmail_intake.py` の変更: 本文空チェック → JEV → 非顧客は No. があっても skip / 顧客＋No. あり → その No. / 顧客＋No. なし → 台帳の最新イベント /
    引けない・イベント無し・複数一致 → `chat_notify.send` で通知し台帳に `notified` として記録（ラベルは付けない）/ 緊急度 ≥ 1.5 は記録＋通知。
    社内差出人（@pinay.jp）は JEV を通さず従来動作。JEV 未応答時は No. ありなら従来どおり記録、No. なしなら台帳に残さず次回再試行。
  - テスト `backend/tests/test_support_triage.py`（18 件）と `backend/tests/test_gmail_intake_flow.py`（Gmail・bay・Chat・JEV・台帳を偽物にした流れ 2 件）が全て通る。
- **新質問文の実測（40 通、10.7 秒、入力 64,753 トークン ≒ $0.003）**: `vm_samples/jev_results_v2.json`。
  非顧客 0.01〜0.04（TOTO 自動送信の No.1309 誤検出も 0.02 で skip に変わる）。旧版で 0.13〜0.53 だった法人窓口
  （林誠一 / YABE / Liu Wenwen / Philix / 村上）は 0.83〜0.94 に上がり顧客側に確定。残る境界は TRIO STYLE の 0.22 / 0.24
  （営業寄りの取引先。閾値 0.15 の上なので顧客扱い → No. なし → 台帳未一致なら通知、人が判断）。
  緊急度 ≥ 1.5 は「明日の予約の件」1.99 と Philix の日程連絡 1.57 の 2 通。
- 台帳照合は VM の実データでは未実行（ローカルに台帳が無い）。`customers.email` に複数アドレスが入る行があれば完全一致で漏れる（要 VM dry-run で確認）。
- **VM 配備済み（2026-09-19 07:45 JST）**: `~/mugi-relay/gmail_intake.py`（退避 `gmail_intake.py.backup-20260919`）と `support_triage.py` を配置、
  `~/mugi-relay/.env` に `TYPESAFE_API_KEY` を追加。VM 上の dry-run（実データ 40 通）: 記録 18 / 通知 8 / 対象外 14 / 失敗 0。
  台帳の日付は ISO 形式で最新イベント選択は正常（`updated_at` は空なので `registered_at` で代替）。複数一致の 2 件（cn11@docomo / mmjgd22）は
  実際に顧客 ID が 2 つあるため通知が正しい。取引先 YABE（alj-jro.com）は台帳に無く通知。
- **追加ルール（配備時に発見）**: 本文の別の数字を No. と誤検出した 973698（台帳の最大 No. 57,513 の範囲外）が CRM の「イベントIDエラー」で
  15 分ごとに 140 回失敗し続けていた。`event_no_plausible`（台帳に存在 or 最大 No.+500 以内）を通らない No. は「No. なし」として
  差出人照合→通知へ回す。差し替え後の dry-run で当該メールは notify に変わった。
- **未処理の過去分**: 配備前に「イベントNo.を特定できず」で台帳に記録済みの顧客メール（直近 60 日で約 19 通）は already_seen で再処理されない。
  取り込みたい場合は intake 台帳の該当行を消して cron に拾わせる（ユーザー判断待ち）。
- 配備手順（参考・実施済み）: (1) VM `~/mugi-relay/gmail_intake.py` を backup-YYYYMMDD で退避 (2) `support_triage.py` と `gmail_intake.py` を配置
  (3) `~/mugi-relay/.env` に `TYPESAFE_API_KEY` を追加（support_triage は `mugi-relay/.env` → `~/.openclaw/.env` の順で読む）
  (4) `.venv/bin/python3 gmail_intake.py --dry-run --days 60 --limit 40` で action / jev / reason を目視 (5) 問題なければ cron に任せる。

## 2026-09-19 08:31 JST: 組み込み先 1 の範囲を縮小して再配備（確定版）
- **ユーザー確定**: support@ 取り込みの対象は「件名か本文にイベント No. が書かれたメール」（/tool/ の返答文案アシスタントから
  送ったメールへの返信）だけ。No. の無いメールは別の対応で扱うため、従来どおり対象外に戻す。
  → 差出人メールでの台帳照合→最新イベント記録、Chat 通知（台帳未一致・緊急度）は撤去。JEV は is_customer 1 問のみ。
- 残した事故防止 2 種（No. 付きメールの中）: JEV 非顧客（TOTO 自動送信の受付番号誤検出）と、台帳に無く範囲外の No.
  （No.973698 の無限再試行）。どちらも台帳に「対象外」として記録し再試行しない。社内差出人・JEV 未応答時は従来どおり記録。
- 配備: VM `~/mugi-relay/gmail_intake.py`・`support_triage.py`（Claude-all の最新コミットと sha 一致）。実データ 40 通の dry-run:
  No. 付きは 973698 の 1 通のみで対象外、残り 39 通は No. なしで対象外、JEV 呼び出し 1 回。
- 08:00 JST の cron 実行で「イベントIDエラー」の再試行は止まった（07:59 JST にユーザーの手動実行で 973698 が notified 記録済み。
  この時点の版は通知ありの中間版で、DM に通知が 1 件届いた）。
- 上の「2026-09-19 午後」「追加ルール」「未処理の過去分」の記述は中間版の記録として残す。過去分の再取り込みは不要（No. なしは対象外が正）。

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

## 次セッションの開始手順（2026-09-20 21:00 JST 更新: 追加 4 件も配備済み・再起動待ち → 組み込み先 3 へ）
0. 組み込み先 1 は完了・VM 配備済み（下の「08:31 JST 確定版」参照）。触らない。
0.5 追加 4 件（2026-09-20 本人決定・実装・VM 配布済み、**gateway 再起動で有効**。成約後オペ側のデプロイが終わってから本人が時間を選ぶ）:
   - シート出力の意図: `OpenClaw_Pinay/scripts/session_intent.py`（第 2 段 `default_ask_noul`、閾値 0.6、直近 5 発話）＋ Python 部品
     `scripts/jev_noul.py`。VM `~/.openclaw/workspace/scripts/` へ直接 install 済み（`deploy_pinay_picklist.sh` は pinay_pick.py の未コミット別作業を
     巻き込むので使っていない）。VM 実呼び出し 0.83 / 0.04、0.5〜0.8 秒。pinay-picklist の未使用 `SHEET_INTENT_RE` は削除（その 1 行だけを部分ステージ）。
   - evidence-gate の断言判定（Noul、閾値 0.6、止められた実行がある番だけ）、drive-url-guard の承認要求判定（Noul、閾値 0.6、プレビュー中 ID を含む
     返答だけ）、pinay-content-search の返答分類（Choice confirm/add/remove/other、confidence 0.7、語が取れなければ `TERM_ASK` で 1 行聞き返す）。
   - `plugins/_shared/jev.js` は `createJevAsker`（生 answer・state 渡し）を土台に `createNoulAsker` / `createChoiceAsker`。
   - 実測: `scripts/measure_jev_questions.py`（このリポジトリ）。sheet 0.66〜0.95 / 0.02〜0.06（質問文を 1 回練り直し: v1 は「タブごとに分けて」0.46）、
     assert 0.78〜0.98 / 0.02〜0.22、approval 0.84〜0.98 / 0.03〜0.12、reply 20/20 confidence 1.0。結果は `vm_samples/jev_questions_v1.json` と
     `jev_questions_v2_sheet.json`（git 除外）。
   - テスト: VM node で 6 本全通過（shared 6/6・stop 15/15・pushback・evidence・drive-url-guard・content-search 30/30）、Mac python で session_intent 12/12。
   - 再起動後の確認: journal に 5 プラグインの registered と、`TYPESAFE_API_KEY が無いため` の警告が**出ない**こと。実機 e2e は Chat DM から
     「そこまでで結構です」（stop）、「それ違うよ」（pushback）、下書き待ちで「うん」（content-search confirm）。sheet 意図は「先月の欠勤を出して」→
     「後で見返せるように残しておいて」→ pinay_pick_export が止まらないこと。
1. 組み込み先 2（中止・指摘の検知）は **実装・VM 配布済み。gateway 再起動で有効になる**（再起動は本人が時間を選んで
   `sudo systemctl restart openclaw`。journal に `[stop-word-gate]` / `[pushback-debug-inject]` の registered 行と、
   `TYPESAFE_API_KEY が無いため` の警告が**出ない**ことを確認する）。
   - 確認した前提: gateway の hook runner は async ハンドラを await する（`~/openclaw/dist/hook-runner-global-*.js` の
     `runVoidHook`（並列・各 hook にタイムアウト）と `runModifyingHook`（優先順に逐次）。`before_tool_call` / `before_prompt_build` は
     15 秒打ち切り）。よって JEV は同期経路（before_prompt_build / message_received）に入れられる。
     `~/.openclaw/.env` は起動時に `process.env` へ読み込まれる（`dist/dotenv-global` の `loadGlobalRuntimeDotEnvFiles`。
     systemd の unit は `openclaw.service`、Environment は OPENCLAW_HOME と GOOGLE_* だけ）。
   - 成果物（OpenClaw_Pinay、ブランチ feat/ops-contract-automation 上にコミット）:
     `plugins/_shared/jev.js`（fetch＋AbortController、fail-open）、`plugins/stop-word-gate/index.js`（`onMessageJev`、
     既定 threshold 0.8 / maxChars 40）、`plugins/pushback-debug-inject/index.js`（`onPromptBuildJev`、既定 0.7 / 300）、
     両 `openclaw.plugin.json` に `jev` 節、`tests/test_shared_jev.mjs`（4 件）＋既存 2 本に第 2 段の検証を追加（VM node 22 で全通過）。
     docs は `docs/stop-word-gate-plugin.md` / `docs/pushback-debug-inject-plugin.md` / `docs/plugin-shared.md`。
   - 質問文と実測: `scripts/measure_stop_pushback.py`（このリポジトリ）。40 件全件正解。中止: true 0.94〜0.98 / false 0.02〜0.08。
     指摘: true 0.84〜0.96 / false 0.01〜0.40（最大は「違いがあれば教えて」0.40）。往復 200〜660 ms、VM から 460〜650 ms。
     結果は `vm_samples/jev_stop_pushback_v1.json`（git 除外）。
   - VM `~/.openclaw/.env` に `TYPESAFE_API_KEY` を追加済み（値は Mac の `JEV-UsageGuide/.env` と同じ）。VM の deployed code で
     実呼び出し 2 件成功。
   - 未了: 再起動後の実機 e2e（Chat DM から「そこまでで結構です」→ journal に `source=jev`、「それ違うよ」→ `injected … source=jev`）。
     CLI agent は message_received を発火しないので DM から送る。自動化台帳は既存項目の実体更新＋改善記録（新項目にしない）。
2. 組み込み先 3（pinay_pick の判定 `judge`）: **実装・VM 配布済み・再起動待ち**（2026-09-20 23:00 JST）。
   - 形: `pinay_pick` ツールの引数 `judge`（条件文）で一体に呼ぶ（別ツールの 2 段は Mugi が 2 段目を飛ばす等の理由で不採用・本人確認）。
     プラグインが pinay_pick → `scripts/pinay_judge.py --saved … --criterion …` を続けて実行。docs は `OpenClaw_Pinay/docs/pinay-judge.md`。
   - 判定: 20 行を 1 回にまとめて Noul（`scripts/measure_judge_batch.py`、合成 60 行: まとめ呼び 56/60・0.3〜0.7 秒、1 行ずつ 52/60・6〜7 秒）。
     該当 0.6 以上／要確認 0.25〜0.6／非該当。VM 実データ（遅刻 20 行）1.4 秒で該当 9・要確認 3・非該当 8。同じ文が並び位置で 0.60 と 0.11 に割れた例あり。
   - `vm_samples/suzuki_queries.txt` は 12 問（旧記載の 42 件は誤り）。列で絞れる条件（引越し→progress_detail「顧客の引越／転勤／帰国」、不明）は
     プラグインの REASON_SYNONYMS で既に対応済み。judge は自由記述を読む条件（迷子・鍵の話など）用。
   - 成果物: `scripts/pinay_judge.py`・`scripts/jev_noul.py`（`ask_many` 追加）・`plugins/pinay-picklist/index.js`（`judgeSaved`、judge 引数、
     判定件数を【この数字を使う】に）・`tests/test_pinay_judge.py`（7 件）・`tests/test_pinay_picklist_judge.mjs`（VM node 通過）。
     pinay-picklist の index.js は 9/16 の未コミット別作業と同居しているため、judge を含む hunk だけを部分ステージしてコミット。
   - 再起動後の確認: Chat DM から「今期の遅刻イベントで、迷子や乗り間違いが理由のものを出して」→ journal に `[pinay-picklist] judged criterion=…`、
     本文先頭に「【この数字を使う】判定件数」。AGENTS.md には足していない（ツール説明で誘導。必要なら 1 行だけ）。
3. 残り: 自動化台帳（既存項目の実体更新＋改善記録）。元記事 §6-1 後半〜§6-4 の転記（PDF 未取得）。

## 次セッションの開始手順（2026-09-19 引継・旧）
1. 作業ディレクトリは `~/Documents/Claude/JEV-UsageGuide/`（独立リポ、GitHub nizki-kasaph/ClaudeCode main）。`.env` に TYPESAFE_API_KEY / CLOUDFLARE_* 設定済み。
2. 設計前に TypeSafe プラグインの指針どおり公式 docs を読む: https://docs.typesafe.ai/llms.txt → noul / confidence / cookbooks（hierarchical_classification, rerank）。
3. 組み込み先 1（support@ 取り込み）から実装。VM は `gcloud compute ssh NIZ-ki@openclaw-gateway --zone asia-northeast1-a`（権限バイパス時のみ私が直接実行可）。
   - 差し込み位置: gmail_intake.py の load_message 後・post_event_detail 前。JEV 3 問（is_customer / category / urgency）を 1 リクエスト。
   - 「顧客」の定義は法人客の窓口・取引先担当者を含む（ユーザー確定）。
   - 顧客 → 差出人 email で pinay_ledger.sqlite3 の customers → events（直近）へ記録。未一致は Chat 通知。
   - 確定（2026-09-19 ユーザー回答）: 記録先は該当顧客の**最新**イベント。通知は既存の chat_notify（仁月さん・土屋さんの DM）。
4. 組み込み先 2（stop-word-gate / pushback-debug-inject）: キーワード一致を第 1 段、未一致のみ JEV Noul（Node fetch、~/.openclaw/.env のキー）。実測済みの質問文は本セッションのログ参照（HANDOVER の実測節）。
5. 組み込み先 3（pinay_pick 再ランキング）: `vm_samples/suzuki_queries.txt` の質問型に対し、行ごとの自由記述へ Noul / Choice を一括判定。
6. すべてローカル（dry-run）で検証してから VM へ 1 回だけ配備。VM 上のファイル変更前にバックアップ（既存慣行 backup-YYYYMMDD）。

## 次にやること（順番）
1. 元記事の §6 残りを入手し、`jev-usage-guide.md` の「6-1 質問は2つを1回で」以降と「6-2〜6-4（未取得）」を埋める。
2. 公式 API で実測済み。次は実用途への組み込み（メール返信要否判定など）。コンソールの Usage で消費量・課金の表示を確認し、料金節に反映する。

## 参照ファイル
- `docs/jev-usage-guide.md` … 成果物（改訂版）
- `source/JEV.pdf` … 元記事 PDF（12 ページ、画像のみ。テキスト抽出不可、PyMuPDF でページ画像化して読んだ）
- `docs/HANDOVER.md` … 本メモ
- リポジトリ: https://github.com/nizki-kasaph/ClaudeCode （ローカル `~/Documents/Claude/JEV-UsageGuide/`）
