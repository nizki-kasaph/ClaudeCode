# JEV（TypeSafe AI の判定専用モデル）使い方まとめ

元記事: [爆速で爆安。判定専用AI「JEV」を徹底解説 ― 使い方・料金・実例と、実際に作った4つのプロダクトの裏側（AGIラボ、2026-09-18 18:50 公開）](https://chatgpt-lab.com/n/n746a127b4074)

> 本書の位置づけ。元記事は PDF（12 ページ、画像化）で入手し、§1〜§5 と §6-1 の途中までを本文から転記した。
> PDF は §6-1「質問は2つを1回で」のコード冒頭で切れており、§6-1 の残りと §6-2〜§6-4（ペルソナ調査・AIウミガメのスープ・ことばクエスト）は未取得。該当箇所は「未取得」と明記した。
> 元記事の記述は出典 [^article] で示し、それ以外の補足は TypeSafe 公式 SDK・PyPI・npm・Cloudflare 公式・mizchi 氏の実測レポートで裏を取った。
> 情報のスナップショットは 2026-09-18 時点。早期アクセス中のため、価格・上限・モデル名は変わり得る。

---

## 0. 元記事の章立て

| 章 | 内容 | 本書での取得状況 |
| --- | --- | --- |
| 1 | JEV とは？「文章を書かない」判定専用の AI | 取得済み |
| 2 | JEV の料金（TypeSafe 公式 / Cloudflare Workers AI） | 取得済み |
| 3 | 話題の活用事例（X の投稿 5 件） | 取得済み |
| 4 | JEV はどこから使える？（2 つの入口） | 取得済み |
| 注意点 | 日本から使うときの通信の遅延（レイテンシ） | 取得済み |
| 5 | 具体的な使い方（JS の呼び出し例・Cloudflare Workers・使いこなしのコツ） | 取得済み |
| 6 | 実際に作った 4 つのプロダクトの裏側 | 6-1 の途中まで。残りは未取得 |

---

## 1. JEV とは

- 米 TypeSafe 社が開発した「System One モデル」の第 1 弾。2026-09-15 に早期アクセスを発表。[^article][^gihyo]
- 名前の由来はダニエル・カーネマン『ファスト＆スロー』。LLM が「システム 2」的にじっくり文章を組み立てるのに対し、JEV は「システム 1」＝一瞬の判断に特化する。[^article]
- 文章を一切書かない。「はい／いいえ」「A と B と C のどれか」「0〜4 点で何点か」といった**判定だけを、確率つきで、非常に速く・安く**返す。[^article]
- 開発元 TypeSafe AI は元 OpenAI 研究者 Diogo Almeida が CEO。[^gigazine]

### LLM との違い（元記事の比較表）[^article]

| 観点 | LLM（ChatGPT・Claude など） | JEV |
| --- | --- | --- |
| 出力 | 文章 | 型の決まった答え＋確率 |
| 得意 | 書く・考える・説明する | 判定・分類・採点 |
| 速さ | 数秒〜 | 0.2〜0.8 秒 |
| 扱い | パースが必要 | そのままコードで分岐 |
| 入力 | テキスト・画像など | **テキストのみ**（文字列・JSON・配列。画像・音声・動画は非対応） |

LLM に「JSON で答えて」と頼むと JSON が壊れたり前置きが付いたりするが、JEV は最初から型の決まった答えしか返さないのでその心配がない。[^article]

### 3 種類の「質問」[^article]

| タイプ | 問い | 返り値 | 元記事の例 |
| --- | --- | --- | --- |
| **Noul（ヌル）** | はい／いいえ | 「はい」である確率 `noul`（0〜1） | 「このメールは返信が必要？」→ 0.79 |
| **Choice（チョイス）** | 選択肢から 1 つ | 選んだ `choice`、各選択肢の確率、`confidence` | 「担当部署は？（経理／技術／営業）」→ 経理 87%・技術 13%・営業 0% |
| **Score（スコア）** | 段階評価 | 点数 `score`、各段階の確率、`confidence` | 「顧客の怒り度は？（0:平静／1:不満／2:激怒）」→ 1.04 |

- 3 つを **1 回の呼び出しで何個でも同時に**聞ける。質問は独立・並列に評価されるので、質問を増やしても応答時間はほとんど変わらない。[^article]
- Noul の 0.5 付近は「中くらい」ではなく「判断がつかない」を意味する。[^awesome]
- 順序のある結論は Choice ではなく Score で聞くこと。実測で正解率 19/24 → 23/24 に改善した。[^mizchi-practice]

### 最大の特徴は「確率が信用できる」こと[^article]

JEV の確率はキャリブレーション（校正）されている。「80%」と答えたものを大量に集めると実際に約 8 割が当たるように訓練されている。これにより確率をそのままプログラムの判断材料に使える。

- 確信度が高い → 自動で実行
- 確信度が中くらい → ユーザーに確認
- 確信度が低い → 人間や上位の LLM に回す

LLM の「自信があります！」とは違い、JEV の「わかりません（確率が割れている）」は信用できるシグナルになる。

### 主なスペック（2026 年 9 月時点）[^article]

| 項目 | 値 |
| --- | --- |
| モデル名 | `jev-1.13.0`（エイリアス `jev-latest`） |
| 入力 | テキストのみ（文字列・JSON・配列）。画像・音声・動画は非対応 |
| コンテキスト長 | 1 リクエスト 64k トークン（うち state と最長の質問の合計で 32k トークンまで） |
| 言語 | 英語が最も得意。**日本語も問題なく使える**（筆者の検証で日本語のメール判定・クイズ判定は十分な精度） |

---

## 2. 料金

### TypeSafe 公式 API[^article]

| 項目 | 値 |
| --- | --- |
| 入力 | **$0.042 / 100 万トークン**（約 6 円。1 ドル 150 円換算で 6.3 円） |
| 出力 | **無料** |
| レート制限 | 1 秒あたり 25 万トークン／1 分あたり 1,200 リクエスト（需要増のため変動中と公式に記載あり） |

筆者が実際に使った量での試算（1 ドル 150 円換算）:[^article]

| 用途 | 入力トークン | 費用 |
| --- | --- | --- |
| メール 1 通の返信要否判定 | 約 2,600 | **約 0.016 円** |
| 架空ペルソナ 150 人 × 6 問（計 900 判定） | 約 19.5 万 | **約 $0.008（約 1.2 円）** |
| X 投稿 3,282 件の分析（1 投稿 8 問、事例 ⑤） | 約 425 万 | **$0.1282（約 19 円）** |

1 通あたり 0.02 円以下でメールを仕分けられる計算。

- 「価格は補助されている可能性があり、将来下がる見込み」と TypeSafe 自身が述べている。[^orca]
- **コンソールの Usage 画面（2026-09-19 実見）。** Tokens・Requests・Spend の 3 グラフ（日次・30 日）。本書の実測 6 リクエストで Tokens 3,984、Spend は $0.01 未満の表示。
  無料枠・クレジット残高・支払い方法の表示は無く、早期アクセス中の課金方法は画面からは分からない（請求が来るかどうかは未確認）。[^console]

### Cloudflare Workers AI 経由[^article]

- Cloudflare Workers AI にも `typesafe/jev` として提供されている。
- Cloudflare 経由の単価は公開ドキュメントに記載がなく、**Cloudflare のダッシュボード（AI > Models > typesafe/jev）で確認する形式**になっている（2026 年 9 月時点）。
- ダッシュボードの実表示（2026-09-19 確認）: **Input tokens (per 1M) $0.042、Context length 32,000 tokens、Provider model jev-latest**。TypeSafe 公式と同額で、Neuron 換算ではなくトークン単価で表示されている。[^cf-dash]
- 参考: Workers AI 全体の課金単位は Neuron。1 日 10,000 Neuron まで無料、超過分は $0.011 / 1,000 Neuron（Workers Paid プラン）。jev のトークン単価と Neuron 無料枠の対応関係はダッシュボードに表示がなく、未確認。[^cf-pricing]
- ダッシュボードのモデルページに「Generate API Token」ボタンと cURL 例があり、Worker を書かずに REST API から直接呼べる。[^cf-dash]
- **REST の実測（2026-09-19）。** 第三者モデルは URL にモデル名を入れる形（`/ai/run/typesafe/jev`）では `7000 No route for that URI` になる。正しくは `POST /accounts/<ACCOUNT_ID>/ai/run` に本文 `{"model": "typesafe/jev", "input": {"state": …, "questions": …}}` を送る。[^cf-jev]
- **課金は Workers AI の Neuron 無料枠ではなく AI Gateway の Unified Billing（前払いクレジット）。** 残高ゼロの状態で呼ぶと `402 {"code": 2021, "message": "Insufficient balance; add money to your gateway or use BYOK"}` が返った。クレジットは AI Gateway > Credits Available > Manage > Top-up credits から追加する。BYOK は TypeSafe 自身の API キーを AI Gateway に登録して自前課金にする方式（早期アクセスの招待が必要）。[^cf-billing]

---

## 3. 話題の活用事例（元記事が X から引用した 5 件）[^article]

| # | 事例 | 投稿者 | 内容 |
| --- | --- | --- | --- |
| ① | EC のリアルタイム接客 | Rinte さん | 音声対話 AI（gpt-live-1）と JEV の組み合わせ。会話の途中でもユーザーの発話に合わせておすすめ商品を即座に表示。対話内容に応じてアバターの表情も変える。「今の発話はどの商品カテゴリの話か」「ユーザーの感情は？」を会話を止めずに裏で判定し続ける |
| ② | スマブラを 4 キャラ同時に操作 | Mau Baron さん | 大乱闘スマッシュブラザーズの 4 キャラクターを JEV が同時に操作して自分自身と対戦。一瞬ごとに「今どの技を出すのがベストか」を判定。この試合で 2,200 万トークン以上を使ってもコストは数セント程度。「gpt-6 astra の代わりにはならないが、即応性で広がる可能性は無限大」 |
| ③ | 話した内容に合わせてスライドが自動で切り替わる | Rinte さん | プレゼン中に、話している内容にマッチしたスライドを自動表示。PC やポインターに触らずにページが切り替わる。「今の発話はどのスライドの話か」を Choice で判定し続けるだけで実現 |
| ④ | 300 ms ごとに売買判断するトレーディング Bot | Jarrod Watts さん | 通貨ペアの価格フィードを見て JEV が「買い」か「売り」かを判定し、実際に取引を執行。Monad チェーン上のオンチェーン板（Kuru）に 300 ms ごとのブロックで注文。デモ: jev-trader.vercel.app。※投資判断を AI に任せるのはリスクが伴う。あくまでデモ |
| ⑤ | 自分の X 投稿 3,282 件を分析 | Ian Nuttall さん | 累計 1 億ビューの投稿 3,282 件を JEV に読ませ、1 投稿につき 8 つの質問（トピック・フック・トーン・何かを教えているか など）を判定。使用トークン約 425 万、費用 $0.1282（約 19 円）、所要 8 分 34 秒。「How-to 系の投稿はいいね中央値 150（全体の中央値は 44）」「AI×コーディングの話題は 1.9 倍」 |

### 一次資料で確認できる同種の実装（補足）

| 実装 | 内容 | 出典 |
| --- | --- | --- |
| Jev Ultrafast（browser-use） | ブラウザ操作エージェント。要素表から操作と対象を JEV が 1 リクエストで選ぶ。Google Flights 検索を 7.1 秒 | [^ultrafast] |
| jev-trader | サブ秒の相場判断ループ。既定はドライラン | [^awesome] |
| typesafe-snake | スネークゲーム。合法手をコードが生成し、JEV が 1 手選ぶ | [^awesome] |
| HA-Jev | Home Assistant の自動化エンティティとして Noul / Choice / Score を公開 | [^awesome] |
| jev-mcp | コーディングエージェント向け MCP サーバー（主張検証、内容スクリーニング、順位付け） | [^awesome] |
| jev-playground（mizchi） | 五目並べ・MOBA・チェス・ESLint プラグイン・Claude Code の PreToolUse hook 等の実測集 | [^mizchi] |
| Doom / Wikiracing | TypeSafe 公式のローンチデモ | [^launch] |

公式が挙げる用途カテゴリ: サポート振り分け、意図ルーティング、確信度ゲート付きの自動化、RAG の passage フィルタ、再ランキング、引用検証、LLM のガードレール、構造化抽出、複合スコアリング、階層分類、スマートホーム操作、エージェントの skill 選択。[^awesome]

---

## 4. どこから使えるか（2 つの入口）[^article]

| | A. TypeSafe 公式 | B. Cloudflare Workers AI |
| --- | --- | --- |
| 特徴 | Playground で試せる／API キーで呼び出し／Python・JS SDK | `env.AI.run` で 1 行／API キー管理が不要／請求をまとめられる |
| 向いている人 | どこからでも HTTP で呼びたい、SDK を使いたい、レート制限やモデルのバージョンを細かく管理したい | すでに Cloudflare Workers でサービスを作っている、Web サービスとしてすぐ公開したい（元記事のゲーム 2 本はこの方法） |

### 入口 A: TypeSafe 公式

**2026 年 9 月時点では、公式 API は早期アクセス（ウェイトリスト制）。** すぐには使えないので、まず TypeSafe の公式サイトの「Join Waitlist」から登録し、招待を待つ。[^article]

1. 招待が届いたら [TypeSafe のコンソール](https://console.typesafe.ai/)にログイン。
2. まず Playground（ブラウザ上で試せる画面）で、文章と質問を入れて試す。
3. 本格的に使うなら API キーを発行し、`https://api.typesafe.ai/v1/systemone` を呼ぶ。環境変数 `TYPESAFE_API_KEY` に入れる。[^sdk-py][^sdk-js]
4. 公式の Python SDK・JavaScript SDK も用意されている。

| 項目 | 値 |
| --- | --- |
| エンドポイント | `POST https://api.typesafe.ai/v1/systemone` |
| モデル別名 | `jev-latest`（実体は `jev-1.13.0`）。`jev-preview` も一覧に出る[^mizchi] |
| モデル一覧 | `GET /v1/models`[^mizchi] |
| 認証 | `Authorization: Bearer <API キー>` |
| Python SDK | `pip install typesafe-sdk`（v0.7.0）[^sdk-py][^pypi] |
| JS/TS SDK | `npm install @typesafe-ai/sdk`（v0.6.0、Node.js 20 以上）[^sdk-js][^npm] |

> 注意。`typesafe-ai` という PyPI パッケージは本物ではなく、名前の乗っ取り防止のために第三者が登録したリダイレクト用シムである。正規は `typesafe-sdk`。[^pypi-shim]

### 入口 B: Cloudflare Workers AI

- Cloudflare Workers AI のモデルカタログに `typesafe/jev` として登録されている。ドキュメント: https://developers.cloudflare.com/ai/models/typesafe/jev/ [^article]
- Workers の中から `env.AI.run('typesafe/jev', ...)` の 1 行で呼べる。API キーの管理が不要で、請求も Cloudflare にまとまる。[^article]
- 欠点は次節の遅延問題が解消しないこと（日本のエッジから結局米国へ渡る）。[^article][^henteko]
- そのほかの経路として OpenRouter（`typesafe/jev-1.13`）と Vercel AI Gateway にも掲載がある。[^openrouter][^vercel]

---

## 注意点: 日本から使うときの通信の遅延（レイテンシ）[^article]

TypeSafe は「応答は 70〜500 ms」とうたっているが、これは**サーバーの近くから呼んだ場合**の数字。公式 API のサーバーは米国西海岸（AWS のオレゴンリージョン）にあり、日本から呼ぶと太平洋を往復する通信時間が毎回上乗せされる。

筆者が日本から測った結果（2026 年 9 月、東京）:

| 計測 | 値 |
| --- | --- |
| 日本 ⇄ API サーバーの往復 | 約 0.16 秒（接続を新しく張るときは暗号化の準備も含めて約 0.33 秒） |
| Cloudflare Workers（東京）経由で JEV を 1 回呼ぶ | 0.19〜0.85 秒（中央値 約 0.33 秒） |
| 公式 API を直接呼ぶ | 0.16〜0.44 秒 |
| 例外 | ごくまれに 1 回だけ数秒〜数十秒かかることもあった |

メールの仕分け、チャットの返答、クイズの判定のような用途なら体感はほぼ「一瞬」で問題ない。一方、スマブラのデモのように 1 秒に何回も判断させる使い方や、数百ミリ秒を争う取引では、この往復時間が効いてくる。

### 日本から使うときのコツ[^article]

| コツ | 内容 |
| --- | --- |
| 質問は 1 回の呼び出しにまとめる | 質問を増やしても時間がほとんど変わらないので、往復の回数を減らすのが一番効く（mizchi 氏の実測: 20 問を 20 回に分けると 5,227 ms、1 回にまとめると 246 ms。答えの平均差 0.011[^mizchi-api]） |
| 並列で投げる | ペルソナ 150 人の調査は 20 並列で 900 判定を約 5 秒で終えている |
| 接続を使い回す | 毎回新しく接続すると、そのたびに約 0.3 秒余計にかかる |
| 先回りして聞いておく | 次に必要になりそうな判定を、ユーザーの操作を待たずに投げておく（公式ドキュメントで「Speculative fan-out」として紹介されている考え方） |
| 待ち時間の上限と代わりの手を決めておく | メール判定では、JEV が失敗したら LLM に切り替える。ゲームでは「考え中…」の表示を出すだけでも体験がかなり変わる |
| 本当にリアルタイム性が必要なら、処理をするサーバーを米国に置く | 日本のユーザーには結果だけを返す構成にすれば、判断の往復は米国内で完結する |

---

## 5. 具体的な使い方[^article]

### 基本の形: 「state（判断材料）」と「questions（質問）」を渡すだけ

公式 API の場合（JavaScript）:

```js
const res = await fetch('https://api.typesafe.ai/v1/systemone', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${process.env.TYPESAFE_API_KEY}`,
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({
    model: 'jev-latest',
    // 判断材料。文字列でも JSON でも OK
    state: '決済が3日間ずっと失敗しています！至急対応してください。',
    questions: {
      is_urgent: {
        type: 'noul',
        instructions: 'このメッセージは緊急性を伝えていますか？',
      },
      department: {
        type: 'choice',
        instructions: 'どのチームが対応すべきですか？',
        criteria: {
          billing: '支払い・請求・返金',
          technical: '不具合・障害・連携',
          sales: '料金プラン・新規契約',
        },
      },
      frustration: {
        type: 'score',
        instructions: '顧客はどのくらい苛立っていますか？',
        criteria: ['落ち着いている', '不満がある', '激怒している'],
      },
    },
  }),
})
const { answers } = await res.json()
```

返ってくる答え（イメージ）:

```json
{
  "model": "jev-1.13.0",
  "answers": {
    "is_urgent": { "type": "noul", "noul": 0.95 },
    "department": {
      "type": "choice",
      "choice": "billing",
      "confidence": 0.8,
      "probabilities": { "billing": 0.87, "technical": 0.13, "sales": 0 }
    },
    "frustration": {
      "type": "score",
      "score": 1.04,
      "confidence": 0.94,
      "probabilities": { "0": 0, "1": 0.96, "2": 0.04 }
    }
  },
  "usage": { "input_tokens": 426, "output_tokens": 73 }
}
```

あとは `if (answers.is_urgent.noul > 0.8)` のように、普通のプログラムとして分岐するだけ。

- `state` は文字列・オブジェクト・配列のいずれも可。会話ログを配列のまま渡せる。[^mizchi-api]
- Choice の `criteria` の値に `null` を置くと「選択肢名だけで解釈」になる。名前が内容を説明していれば説明文は省略できる。[^mizchi-api]

### Cloudflare Workers の場合

`wrangler.jsonc` に AI バインディングを追加して、

```jsonc
{
  "name": "my-app",
  "main": "src/index.ts",
  "ai": { "binding": "AI" }
}
```

Worker のコードから呼び出す。

```js
const r = await env.AI.run('typesafe/jev', { state, questions })
// Cloudflare 経由では結果が result に包まれて返ってきた
// { state: "Completed", result: { model, answers, usage } }
const { answers } = r.result ?? r
```

筆者の環境では Cloudflare 経由だとレスポンスが `result` で包まれて返ってきたので、上のように両対応にしておくと安全。

### SDK での書き方（公式 README より）

Python:[^sdk-py]

```python
from typesafe_sdk import Choice, Noul, Score, TypeSafeClient

with TypeSafeClient() as client:
    response = client.system_one(
        state={"ticket": "I was charged twice and need the duplicate refunded today."},
        questions={
            "intent": Choice(
                instructions="What is the customer's main request?",
                criteria={"refund": None, "technical_help": None, "other": None},
            ),
            "is_urgent": Noul(instructions="Does the ticket explicitly communicate time pressure?"),
            "frustration": Score(
                instructions="How frustrated does the customer appear?",
                criteria=["Calm and neutral", "Concerned but civil", "Very angry"],
            ),
        },
    )

print(response.answers["intent"].choice, response.answers["is_urgent"].noul, response.answers["frustration"].score)
```

JavaScript / TypeScript:[^sdk-js]

```ts
import { choice, TypeSafeClient } from "@typesafe-ai/sdk";

const client = new TypeSafeClient();
const response = await client.systemOne({
  state: { document: "I was charged twice. Please fix this ASAP." },
  questions: {
    category: choice("What is this ticket about?", { billing: null, technical: null, other: null }),
  },
});

console.log(response.answers.category.choice);
```

### 使いこなしのコツ（筆者が実際に作って分かったこと）[^article]

1. **質問は「一瞬で答えられる粒度」に分解する。** 「このスタートアップのピッチを評価して」ではなく、「市場規模は？」「技術的に実現可能？」「差別化されている？」と分けて聞き、点数の合成はコード側でやる。公式ドキュメントでも推奨されている考え方。
2. **選択肢の説明文は、その場で動的に作ってよい。** RPG では、選択肢を「赤いスライム。主人公から見て右上に 3 マス」のように、その時点のマップの状況から毎回生成した。これだけで「右上のスライムを倒して」が正しく解釈できる。
3. **JEV は「作る」のは苦手、「選ぶ」のは得意。** 文章も計画も生成できないが、候補をプログラムで作って JEV に選ばせると、生成 AI のようなことができる。
4. **確率・確信度を UX や業務ルールに使う。** 「確信度 70% 未満なら人間に回す」「はい 58% のように確率ごと見せる」など、確率そのものが価値になる。

---

## 6. 実際に作った 4 つのプロダクトの裏側[^article]

元記事が AGI ラボで実際に JEV を使って作ったもの:

1. **メールの返信要否判定**（業務で毎時稼働中）
2. **架空ペルソナ 150 人への導入意向調査**
3. **AI ウミガメのスープ**（Web ゲーム）
4. **ことばクエスト**（言葉だけで操作する RPG）

### 6-1. メールの返信要否判定 ― LLM から JEV に置き換えた

**何をしているか。** 筆者の Gmail では、1 時間ごとに自動で動くプログラム（AGI Wings というサーバーレス基盤上のハンドラー）が新着メールを仕分けている。

1. 新着スレッドを取得
2. **「自分が返信すべきメールか」を判定**
3. 「AI/返信要」「AI/返信不要」のラベルを付ける
4. 返信要のメールには、返信の下書きを LLM で作成しておく

朝メールを開くと、返信すべきものだけに下書きが用意されている。このうち 2. の判定を、LLM（OpenRouter 経由の gpt-5.4-mini）から JEV に置き換えた。下書きの作成は文章の生成なので LLM のまま。

**なぜ JEV に置き換えたか。**

- 判定は「生成」ではなく「分類」だから。LLM に JSON で答えさせてパースする方式は、ときどきパースに失敗していた。
- 速くて安い。判定だけなら JEV で十分。
- 確率が取れる。「返信要 79%」のように、どれくらい迷ったかが分かる。

**前処理はプログラムで。** JEV に聞く前に、明らかなものはプログラムで弾く。AI に聞かなくていいことは聞かない。これは LLM でも JEV でも同じ鉄則。

- 最後のメッセージが自分の送信 → スキップ
- 送信元に noreply を含む → 返信不要
- To/Cc に自分が含まれていない → 返信不要

**JEV に渡す state の設計。** ポイントは、LLM 版で使っていた「判断基準」の文章をそのまま state に入れていること。state は JSON で構造化できるので、「受信者の情報」「判断基準」「スレッド」「最新メール」を分けて渡すと、質問文の中で「reply_criteria に従って」「latest_message について」と名前で参照できる。

```js
const state = {
  recipient: '私は石川陽太です。必ず私の立場で判断してください。',
  recipient_role: 'CC のみで受信（直接の宛先ではない）', // または「直接の宛先(To)」
  reply_criteria: `1. お知らせやメルマガには返信不要
2. 質問や依頼を含むメールには返信が必要
3. 個人的なメッセージや重要な業務連絡には返信が必要
4. 自動生成されたシステムメッセージには通常返信不要`,
  thread: threadContext,          // スレッド全体（古い順、最大8,000文字）
  latest_message: { from, to, cc, subject, date, body }, // 判定対象の最新メッセージ
}
```

**質問は 2 つを 1 回で。** 1 つ目は本題の「返信が必要か」（Noul）。PDF はこのコードの冒頭で切れているため、2 つ目の質問と以降の記述は未取得。

### 6-2〜6-4（未取得）

架空ペルソナ 150 人への導入意向調査、AI ウミガメのスープ、ことばクエストの各節は PDF に含まれておらず未取得。元記事の他の箇所から分かっている範囲:

- ペルソナ調査: 150 人 × 6 問（計 900 判定）、入力約 19.5 万トークン、約 $0.008（約 1.2 円）。20 並列で約 5 秒。（§2・注意点より）
- ゲーム 2 本（ウミガメのスープ・ことばクエスト）は Cloudflare Workers AI 経由で作られた。（§4 より）
- ことばクエスト: 選択肢を「赤いスライム。主人公から見て右上に 3 マス」のようにマップ状況から毎回生成し、候補をプログラムで作って JEV に選ばせる方式。（§5 コツより）

---

## 本書での実測（2026-09-19、横浜、TypeSafe 公式 API 直接）

`client/jev_client.py` で公式 API を呼んだ結果。記事の「公式 API を直接呼ぶ 0.16〜0.44 秒」と整合する。

| 呼び出し | 応答時間 | 備考 |
| --- | --- | --- |
| 記事 §5 の例（Noul + Choice + Score、state 1 文） | 645 ms | セッション新規。`is_urgent` 0.98、`department` billing 0.85、`frustration` 1.88（激怒 0.88） |
| 日本語メール返信要否（Noul + Choice、state は JSON 4 項目・661 トークン）1 回目 | 599 ms | 接続確立を含む |
| 同 2〜4 回目（`requests.Session` で接続再利用） | 205〜269 ms | `needs_reply` 0.96〜0.97、`category` request（confidence 0.99〜1.00）で安定 |

- 日本語の state・質問・選択肢の説明文は、そのままで問題なく判定できた。
- Score の応答には記事に無い `legend`（段階番号と説明文の対応表）が含まれる。
- `usage.output_tokens` は返るが課金は入力のみ。
- **Cloudflare 経由は本書では実測できず。** 第三者モデルは AI Gateway の前払いクレジットが必要で、本アカウントでは決済（複数カード・PayPal）が Cloudflare 側で通らなかった。

### 公式コンソールでの入手手順（2026-09-19 時点の実際）

1. https://typesafe.ai/ 右上の「Join Waitlist」からメールアドレスを送信。GitHub プロフィール、作ったもの、知った経緯などの質問が続く。
2. 本書の場合は送信直後に console.typesafe.ai へログインできた（待機時間なし）。
3. 「Meet Jev」の案内 → 「Can you chat with Jev?」のクイズ（答えは No）→ コンソール。
4. 左メニュー「API Keys」でキーを発行し、環境変数 `TYPESAFE_API_KEY` に入れる。
5. コンソールの構成: Home（Cookbooks・Demos・Quickstart）、Playground（state と questions を JSON で書いて `jev-latest` に Run。
   Noul / Choice / Score の練習問題 3 本と、実務例「Resumé screening」「Support agent audit」「Helpdesk ticket triage」が同梱）、Usage、API Keys。
   Cookbook には「Parallel questions（13 問を 1 回にまとめると 11.5 倍安く 9.6 倍速い）」「SDE cascade（mini → verify → reasoning の 2 段抽出）」
   「Self-consistency（同じ入力に対する Noul の安定性）」、Demo に「Wikirace（1.7 秒で 6 判定）」「Smart home assistant（先回り質問＋LLM フォールバック）」がある。[^console]
6. コンソールの Quickstart に Claude Code 用プラグイン（`claude plugin marketplace add typesafe-ai/skills` → `claude plugin install typesafe@typesafe-ai`）の案内あり。
   本環境では 2026-09-19 に導入済み（typesafe@typesafe-ai v0.5.7、user スコープ）。中身は docs.typesafe.ai の読み方と設計指針を示す SKILL.md で、
   実行コマンドは含まない。設計時は https://docs.typesafe.ai/llms.txt から該当ページ（`.md` を付けると Markdown で読める）を参照する。

## 付録: 実装時の落とし穴（実測ベース）

以下は元記事の範囲外だが、実際に使う際に効く注意点である。出典はすべて mizchi 氏の実測レポート。[^mizchi-api][^mizchi-practice]

| やってはいけないこと | 何が起きるか |
| --- | --- |
| Noul の `criteria` に `true` / `false` をトップレベルで置く | サーバーは 200 を返して**黙って捨てる**。`criteria: { "true": …, "false": … }` と入れ子にせよ |
| 順序のある結論を Choice で聞く | 隣接レベルの迷いが「低 confidence」に化けて閾値が引けない。Score を使え |
| 「該当なし」を Choice の選択肢に混ぜる | 答えのある難問までそこへ逃げる。スコープ判定は別の Noul で聞け |
| 閉じた世界を仮定する | 範囲外入力が confidence 0.96 で誤ルーティングされる |
| 閾値を質問文に書く | 再校正のたびに質問が変わり、過去の測定と比較できない。閾値はコード側 |
| 複数の質問に共通の閾値を使う | 尺度が質問ごとに違う。質問ごとに閾値を引け |
| 1 問に 256 個以上の選択肢を入れる | `400 Too many choices. Must have at most 255 choices.` |
| state を大きくしすぎる | state は約 32Ki トークン、リクエスト全体は約 64Ki トークンで `max_tokens_exceeded`。質問数自体に上限はない（1,220 問が通る） |
| 判定結果をそのまま副作用にする | 認可・決定的バリデーション・人のレビューの代替にはならない。境界帯は人へ |

推奨の実装境界（公式ドキュメント経由）:[^awesome]

1. state を組み立て、必要な判定を列挙する。
2. 同じ state への質問は 1 リクエストにまとめて投げる。
3. 答え・確率・業務ルールの合成はコードで行う。
4. 副作用はリスク別の閾値でゲートする。
5. モデルのバージョン、質問定義、分布、選んだ経路を記録する。
6. 代表的なラベル付きデータで閾値を校正し、モデル更新のたびに見直す。

---

## 出典

[^article]: AGI ラボ「爆速で爆安。判定専用AI『JEV』を徹底解説 ― 使い方・料金・実例と、実際に作った4つのプロダクトの裏側」2026-09-18 https://chatgpt-lab.com/n/n746a127b4074 （PDF 12 ページ分。§6-1 途中で終了）
[^gihyo]: gihyo.jp「TypeSafe AI、AIモデル『Jev』の早期提供を開始 ―判断結果を構造化データで高速出力」 https://gihyo.jp/article/2026/09/jev-early-access （検索結果の要約から引用）
[^launch]: TypeSafe AI Blog「Introducing System One Models & Jev」 https://typesafe.ai/blog/introducing-system-one-models-and-jev （awesome-jev 経由で参照）
[^gigazine]: GIGAZINE (EN) 2026-09-16 https://gigazine.net/gsc_news/en/20260916-system-one-jev/ （検索結果の要約から引用）
[^awesome]: Anil-matcha/awesome-jev-by-typesafe README（2026-09-18 スナップショット） https://github.com/Anil-matcha/awesome-jev-by-typesafe
[^mizchi]: mizchi/jev-playground README https://github.com/mizchi/jev-playground
[^mizchi-api]: 同リポジトリ docs/00-api-notes.md「API の実挙動メモ」 https://github.com/mizchi/jev-playground/blob/main/docs/00-api-notes.md
[^mizchi-practice]: 同リポジトリ docs/practice.md「実践ガイド」 https://github.com/mizchi/jev-playground/blob/main/docs/practice.md
[^sdk-py]: typesafe-ai/typesafe-sdk-python README https://github.com/typesafe-ai/typesafe-sdk-python
[^sdk-js]: typesafe-ai/typesafe-sdk-js README https://github.com/typesafe-ai/typesafe-sdk-js
[^pypi]: PyPI `typesafe-sdk` 0.7.0 https://pypi.org/project/typesafe-sdk/
[^pypi-shim]: PyPI `typesafe-ai` 0.1.0（リダイレクト用シム、TypeSafe 非公式） https://pypi.org/project/typesafe-ai/
[^npm]: npm `@typesafe-ai/sdk` 0.6.0 https://www.npmjs.com/package/@typesafe-ai/sdk
[^cf-pricing]: Cloudflare Workers AI Pricing https://developers.cloudflare.com/workers-ai/platform/pricing/
[^console]: TypeSafe コンソール https://console.typesafe.ai/ の Home / Playground / Usage 画面（2026-09-19 のスクリーンショットより）
[^cf-billing]: Cloudflare AI Gateway「Unified Billing」 https://developers.cloudflare.com/ai-gateway/features/unified-billing/ と、2026-09-19 の実測エラー（402 code 2021）
[^cf-dash]: Cloudflare ダッシュボード AI > Models > typesafe/Jev（2026-09-19 のスクリーンショットより。Pricing・Context length・Quick Start の表示）
[^henteko]: Zenn（henteko）「Cloudflare WorkersでJevを使ったら高速か検証してみた」 https://zenn.dev/henteko/articles/1d159d10413312 （検索結果の要約から引用）
[^orca]: OrcaRouter「Jev: TypeSafe's Decision Model, Speed and Cost Explained」 https://www.orcarouter.ai/blog/jev-typesafe-system-one-what-we-know （検索結果の要約から引用）
[^ultrafast]: browser-use/jev-ultrafast README https://github.com/browser-use/jev-ultrafast
[^openrouter]: OpenRouter「Jev 1.13」 https://openrouter.ai/typesafe/jev-1.13
[^vercel]: Vercel AI Gateway「Jev」 https://vercel.com/ai-gateway/models/jev
