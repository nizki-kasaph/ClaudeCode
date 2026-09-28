# 引継メモ: ローカル AI 環境の整備（2026-09-28 作成 / Claude Code Web セッション）

別チャットで手順を実行するための引継。検討の経緯と出典は末尾。

## 前提

- 機材: 今は M1 16GB（macOS 27）。本運用は M5 64GB を想定。設定・配線は今から組み、モデルの重みは M5 で差し替える。
- 用途: 日常用途の LLM とサイト、低ハルシネーション、OpenClaw（OpenClaw_Pinay）との連携で特化プラグインを組む。
  画像は一枚絵で日本語の文字を入れる。音楽も生成する（現在 MusicGen → ACE-Step へ切替）。
- 判定（Noul / Choice 型）は JEV を継続。ローカル LLM は「生成」担当、JEV は「検証」担当。
- 出自の扱い: Qwen（Alibaba）・Z-Image / Qwen-Image（Alibaba）・ACE-Step（ACE Studio + StepFun）は中国本土製。
  採用範囲を「コード生成」「画像の日本語文字入れ」「音楽」に限る。組織としての扱いは別途判断。

## 決定した配分

| 役割 | 担当 | 備考 |
|---|---|---|
| 設計・複雑なコード・重い推論 | Claude（Sonnet 5 / Opus 5） | ローカル 30B 級は Haiku 4.5 相当で 1〜2 世代差 |
| 日常の要約・分類・下書き・秘匿データ | Gemma 4 26B-A4B（Ollama） | HHEM 5.2%、Apache-2.0。M1 では E4B で代用 |
| ローカルのコード補助 | Qwen3-Coder 30B-A3B（Ollama） | M5 で導入 |
| 判定 | JEV（TypeSafe） | 置換は同一データで一致率を測ってから |
| 一枚絵・日本語文字あり | Z-Image Turbo（既定）/ Qwen-Image 2.1（品質重視） | FLUX.2 klein は漢字が崩れる |
| 一枚絵・文字なし・出自回避 | FLUX.2 klein 9B + 文字はコードでフォント合成 | |
| 音楽 | ACE-Step 1.5（生成のみ） | MIT。REST API `acestep-api` |
| 動画・高解像度・LoRA 学習 | クラウド（fal 等） | Mac の LoRA 学習は未修正の不具合あり |

## 手順 A: 今の M1 16GB でやること

常駐は 1 つまで。画像・音楽を触るときは LLM を止める。

1. **Ollama** を v0.19 以降にする（Apple Silicon の MLX バックエンド）。`ollama pull gemma4:e4b` で E4B（約 3GB）を入れる。
2. **OpenClaw の Ollama プロバイダ** を設定する。
   - `baseUrl: "http://localhost:11434"`（`/v1` を付けない。付けるとツール呼び出しが平文 JSON になる）
   - Gemma 4 は `reasoning: false`
   - ツール呼び出し・タイムアウト（起動直後は遅い）・keep-alive を確認する
3. **特化プラグインの雛形** を OpenClaw_Pinay の既存形式で作る: 第 1 段 語彙 → 第 2 段 ローカル LLM（生成）→ JEV（検証: evidence-gate / qa_audit）→ 未応答は fail-open。
4. **実測スクリプトにローカル backend を足す**: このリポジトリの `scripts/measure_*.py` と `client/jev_client.py` に Ollama 経由の呼び出しを追加し、E4B で JEV との一致率を取る。
   E4B の数値は配線確認用で、採用判断には使わない。
5. **ComfyUI**（Mac ネイティブ app）を入れ、OpenClaw の ComfyUI プロバイダを `mode: local`、`baseUrl: http://127.0.0.1:8188` で繋ぐ。
   `image` / `music` のワークフロー JSON とプロンプト・出力ノード ID を固定する。
   16GB では Z-Image Turbo が LLM と同居できないので、配線確認は SDXL か FLUX.2 klein 4B の量子化版で行い、モデル名だけ後で差し替える。
6. **文字合成の処理** を書く（絵は生成、日本語の文字は Pillow 等でフォント合成）。GPU 不要。
7. **ACE-Step 1.5** を macOS 用スクリプト（`start_api_server_macos.sh`）で起動し、量子化・オフロードで REST API の接続確認まで行う。XL は M5 待ち。
   OpenClaw からは ComfyUI の `music_generate` ではなく REST API を直接叩く小プラグインの方が既存形式に近い。
8. 設定ファイル（OpenClaw config、ComfyUI のワークフロー JSON、プラグインのコード、実測スクリプト）を Git に入れる。モデルの重みは Git に入れず、M5 で取り直す。

## 手順 B: M5 64GB に移してからやること

1. Ollama で `gemma4:26b-a4b`（Q4 で約 16GB）と Qwen3-Coder 30B-A3B を入れ、OpenClaw のモデル名を差し替える。
2. `scripts/measure_*.py` を 26B-A4B で回し、JEV との一致率を出す。ここで初めて判定の置換可否を判断する。
3. ComfyUI のモデルを Z-Image Turbo（約 16GB）に差し替え、常駐は Gemma 4 + Z-Image の 2 つ（合計 32GB 前後）。
   Qwen-Image 2.1（bf16 で約 30GB、Q4 GGUF なら約 11GB）は都度ロード。
4. ACE-Step を XL（4B、12〜20GB）に上げる。LLM と同時には載せない。
5. 国産 LLM の並行検証（任意）: LLM-jp-4 32B-A3B（フルスクラッチ、Apache-2.0）を同じデータで測る。主力にはしない。

## 保留・注意

- **Mac の LoRA 学習は今できない**: ACE-Step は MPS/MLX で勾配が非有限になる不具合（Issue #619、2026-02 から未修正）。
  Draw Things は FLUX.2 klein / Z-Image の学習が 0 ステップ目で落ちる（Issue #114、2026-08-12、未修正）。SDXL / FLUX.1 の学習は動く。
  急ぐなら fal.ai 等で学習し、LoRA だけ持ち帰る。
- **MusicGen の重みは CC-BY-NC 4.0（非商用）**。サイトや案件で使う音楽は ACE-Step に切り替える。
- **gpt-oss-120b は 64GB に載らない**（MXFP4 で重み約 63GB）。70B dense は載るが 15〜20 tok/s で判定用途には向かない。
- **源内（デジタル庁）の 7 モデル**は政府内基盤で、個人で重みを落とせるのは Sarashina2.2 の小型と PLaMo 2 8B のみ。
  Llama-3.1-ELYZA-JP-70B はダウンロード不可（デモ・法人 API のみ）。2027-01 の評価公表で見直す。
- Qwen3.5 系は HHEM で 10〜12% と Gemma 4 より作話が多い。推論型（thinking 付き）は総じて率が上がる。
- 指数のスコアは版で数値が変わる。順位関係だけを見る。

## 実測値のメモ（M5 Pro 64GB、Ollama、2026-08-17 更新の第三者ベンチ）

| モデル | decode tok/s |
|---|---|
| Qwen3.6-35B-A3B Q4_K_M + MTP | 84.9 |
| gpt-oss-20b MXFP4 | 66〜80 |
| Gemma 4 26B-A4B nvfp4 | 55.5 |
| Qwen3.8-27B dense MLX | 33.8 |
| Gemma 4 31B dense Q4 | 約 7 |

ハルシネーション率（Vectara HHEM、2026-09-22）: Phi-4 3.7 / Llama-3.3-70B 4.1 / Qwen3-8B 4.8 / Gemma-4-26B-A4B 5.2 /
Gemma-4-31B 7.4 / Qwen3.5-35B 10.5 / Qwen3.5-27B 12.1 / gpt-oss-120B 14.2（%）。

## このリポジトリの関連ファイル

- `docs/HANDOVER.md`: JEV 利用箇所 12 か所と共通方針（語彙 → JEV → fail-open）。プラグインの形式はここに従う。
- `client/jev_client.py`: JEV クライアント。ローカル backend を足す土台。
- `scripts/measure_*.py`: 実測スクリプト。同じデータでローカル LLM を測る。

## 出典（本文を直接確認したもの）

- https://github.com/daniel29348679/m5pro-llm-bench
- https://github.com/vectara/hallucination-leaderboard/blob/main/README.md
- https://github.com/openclaw/openclaw/blob/main/docs/providers/ollama.md
- https://github.com/openclaw/openclaw/blob/main/docs/providers/comfy.md
- https://github.com/ace-step/ACE-Step-1.5
- https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/LoRA_Training_Tutorial.md
- https://github.com/ace-step/ACE-Step-1.5/issues/619
- https://github.com/drawthingsai/draw-things-community/issues/114
- https://github.com/llm-jp/awesome-japanese-llm

## 出典（検索結果の要約のみ。本文はセッションのネットワーク制限で未読）

- https://nowokay.hatenablog.com/entry/2026/04/28/034311（Qwen3.6 と Gemma 4 の比較）
- https://ikuriblog.com/qwen-image-2-guide-flux2-comparison-2026/（Qwen-Image と FLUX.2 の日本語文字）
- https://pareido.jp/architecture/ai/ai-image/dit-checkpoint-tour-3/（Z-Image Turbo 実機検証）
- https://kgptalkie.com/tutorials/llm-benchmarking/qwen-image-2-1-macbook-pro-m5-max-comfyui（Qwen-Image 2.1 on M5 Max）
- https://releases.drawthings.ai/p/introducing-lightning-draft-interactive（Draw Things M5 Max）
- https://artificialanalysis.ai/models/comparisons/gemma-4-26b-a4b-vs-claude-4-5-haiku（等級比較）
- https://ledge.ai/articles/digital_agency_gennai_domestic_llm_selection_government_trial（源内）
- https://ledge.ai/articles/gpt_oss_qwen3_swallow_japanese_reasoning_llm_tokyo_science_aist（Qwen3 Swallow）
- https://elyza.ai/news/2024/10/25/（ELYZA 70B の提供形態）
- https://huggingface.co/spaces/facebook/MusicGen/blob/main/LICENSE_weights（MusicGen ライセンス）
- https://fal.ai/models/fal-ai/flux-lora-fast-training（クラウド LoRA 学習）
- https://benchlm.ai/anthropic/api-pricing（Claude API 価格）
- https://aiagent-navi.com/special/image-gen-api-pricing/（画像 API 価格）
- https://lumimusic.ai/blog/suno-pricing（Suno 価格）
