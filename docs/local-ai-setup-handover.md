# 引継メモ: ローカル AI 環境の整備（2026-09-28 作成 / Claude Code Web セッション）

別チャットで手順を実行するための引継。検討の経緯と出典は末尾。

## 前提

- 機材: 今は M1 16GB（macOS 27）。本運用は MacBook Air M5 32GB（2026-10-02 訂正。当初 64GB としていたが Air は 32GB が上限）。
  設定・配線は今から組み、モデルの重みは M5 で差し替える。
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
| ローカルのコード補助 | Qwen3-Coder 30B-A3B（Ollama） | M5 で導入。32GB では Gemma 4 と入れ替えで都度ロード |
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

## 手順 B: M5 32GB に移してからやること

32GB の制約（2026-10-02 見直し）:
- GPU が使えるメモリは既定で RAM の約 2/3（36GB 以下の機種）。32GB なら **約 21〜24GB** が上限。
  `sudo sysctl iogpu.wired_limit_mb=24576` で 24GB まで上げられる（再起動で戻る。macOS の分を残すため上げすぎない）。
- メモリ帯域は M5 無印 153GB/s で、下の実測値メモの M5 Pro（307GB/s）の半分。decode 速度もおおむね半分を見込む。
- **重いモデル（10GB 超）は 1 つずつ**。手順 A と同じく、画像・音楽を触るときは LLM を止める（`ollama stop <model>`）。
  Ollama は `OLLAMA_MAX_LOADED_MODELS=1` にして、Gemma 4 と Qwen3-Coder が同時に載らないようにする。

| 用途 | モデル | 目安のメモリ | 32GB での扱い |
|---|---|---|---|
| 日常の LLM | Gemma 4 26B-A4B Q4 | 16〜18GB（常駐 14〜16GB） | 単独なら常駐可。M5 32GB で約 22 tok/s の報告 |
| コード補助 | Qwen3-Coder 30B-A3B Q4_K_M | 約 19GB | Gemma 4 と入れ替え。同時に載せない |
| 画像（既定） | Z-Image Turbo **fp8** | ファイル約 6GB・実行時約 13GB | bf16（約 16GB）はやめて fp8 にする。LLM と同居させるなら E4B（常駐 3.2〜3.4GB）に落とす |
| 画像（品質重視） | Qwen-Image 2.1 **Q4 GGUF** | 約 11GB | 都度ロード。bf16（約 30GB）は載らない |
| 音楽 | ACE-Step 1.5 2B（既定）/ XL 4B | 2B 約 4.7GB / XL 約 9GB（推奨 16GB 以上） | XL は LLM を止めて単独で。LM は 1.7B まで（4B は 24GB 以上の区分） |

1. Ollama で `gemma4:26b-a4b`（Q4 で約 16〜18GB。ライブラリ上のタグ名は `gemma4:26b` の可能性あり、pull 前に確認）を入れ、OpenClaw のモデル名を差し替える。
   `contextTokens 32768` は KV キャッシュの分だけ常駐が増えるので、`ollama ps` で 21GB 以内に収まるか確かめる。
2. `scripts/measure_*.py` を 26B-A4B で回し、JEV との一致率を出す。ここで初めて判定の置換可否を判断する（このとき他のモデルは止める）。
3. Qwen3-Coder 30B-A3B（Q4_K_M 約 19GB）を入れる。Gemma 4 とは入れ替えで使う。上限ぎりぎりなので、遅い・落ちるときは
   上限を 24GB に上げるか、Gemma 4 26B-A4B にコードもさせる。
4. ComfyUI のモデルを Z-Image Turbo **fp8** に差し替える。常駐は「Gemma 4 + Z-Image」の 2 つではなく、
   **「Gemma 4 26B 単独」か「E4B + Z-Image fp8」**のどちらか。Qwen-Image 2.1 は Q4 GGUF を都度ロード。
5. ACE-Step は 2B のまま重みを取り、XL（4B）は LLM・画像を止めたときだけ使う。
6. 国産 LLM の並行検証（任意）: LLM-jp-4 32B-A3B（フルスクラッチ、Apache-2.0）を同じデータで測る。主力にはしない。
   32GB では単独ロード。サイズは pull 前に確認する。

## 保留・注意

- **Mac の LoRA 学習は今できない**: ACE-Step は MPS/MLX で勾配が非有限になる不具合（Issue #619、2026-02 から未修正）。
  Draw Things は FLUX.2 klein / Z-Image の学習が 0 ステップ目で落ちる（Issue #114、2026-08-12、未修正）。SDXL / FLUX.1 の学習は動く。
  急ぐなら fal.ai 等で学習し、LoRA だけ持ち帰る。
- **MusicGen の重みは CC-BY-NC 4.0（非商用）**。サイトや案件で使う音楽は ACE-Step に切り替える。
- **gpt-oss-120b・70B dense は 32GB に載らない**（gpt-oss-120b は MXFP4 で重み約 63GB。64GB 想定のときも載らなかった）。
- **Qwen3.8-Flash-Next（125B）は 32GB の Mac では動かない**: MLX 版（MTPLX）の最小構成で RAM 96GB 以上。
  Strata（12GB 級のグラボで動かす推論エンジン）は Windows / Linux の NVIDIA・AMD 専用で、Mac は対象外。
- **源内（デジタル庁）の 7 モデル**は政府内基盤で、個人で重みを落とせるのは Sarashina2.2 の小型と PLaMo 2 8B のみ。
  Llama-3.1-ELYZA-JP-70B はダウンロード不可（デモ・法人 API のみ）。2027-01 の評価公表で見直す。
- Qwen3.5 系は HHEM で 10〜12% と Gemma 4 より作話が多い。推論型（thinking 付き）は総じて率が上がる。
- 指数のスコアは版で数値が変わる。順位関係だけを見る。

## 実測値のメモ（M5 Pro 64GB、Ollama、2026-08-17 更新の第三者ベンチ）

M5 無印（Air）は帯域が半分なので、下の数字のおおむね半分を見込む。64GB 前提の数字で、32GB に載らないものも含む。

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

## 出典（32GB 見直し・2026-10-02 追加）

本文を直接確認したもの:
- https://support.apple.com/en-us/126320（MacBook Air 13 インチ M5 の仕様。メモリは 24GB / 32GB）
- https://support.apple.com/en-us/126321（同 15 インチ）
- https://github.com/ace-step/ACE-Step-1.5/blob/main/docs/en/GPU_COMPATIBILITY.md（メモリ区分ごとの DiT / LM の可否）
- https://github.com/youssofal/MTPLX（Qwen3.8 系の必要メモリ）
- https://github.com/niko1221/strata（対応 OS・GPU）

検索結果の要約のみ:
- https://www.apple.com/newsroom/2026/03/apple-introduces-the-new-macbook-air-with-m5/（M5 の帯域 153GB/s）
- https://en.wikipedia.org/wiki/Apple_M5（M5 Pro 307GB/s）
- https://modelpiper.com/blog/iogpu-wired-limit-mb-mac（GPU に回せるメモリの既定値と `iogpu.wired_limit_mb`）
- https://contracollective.com/blog/mac-unified-memory-wired-limit-gpu-large-local-llm-2026（同上）
- https://modelfit.io/macbook-pro/m5/（Gemma 4 26B-A4B が M5 32GB で約 22 tok/s）
- https://dev.to/purpledoubled/how-to-run-googles-gemma-4-locally-with-ollama-all-4-model-sizes-compared-2pbh（gemma4:26b のサイズ）
- https://llmconfigurator.com/en/guides/coding-agents/run-qwen3-coder-locally（qwen3-coder:30b は Q4_K_M で 19GB）
- https://www.stablediffusiontutorials.com/2025/11/z-image-turbo.html（Z-Image Turbo fp8 約 6GB・GGUF 3.79〜7.22GB）
- https://localaimaster.com/blog/z-image-turbo-comfyui（fp8 の実行時メモリ約 13GB）
- https://freeaimusictools.com/blog/ace-step-apple-silicon-install/（XL は 16GB 以上でページングなし）

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

## 実施記録（2026-09-29・手順 A を M1 16GB で実施 / ローカル Claude Code セッション）

詳細は **OpenClaw_Local** `docs/local-ai-setup.md`（入れた場所・設定・実測の全体。独立リポジトリ `~/Documents/Claude/OpenClaw_Local`）。ここは JEV 側の要点だけ。
ローカル AI 環境は内部用の開発動作環境で、VM の OpenClaw（Pinay・公的）とは混同しない（2026-09-29 本人方針。当初 OpenClaw_Pinay のブランチに置いたものを同日移設）。

- **手順 1**: Ollama 0.34.4（CLI 版、`~/.local/ollama`。Homebrew は Intel 版で不可）。`gemma4:e4b` は Ollama 上 **9.6GB**（Q4_K_M でも同じ 8.95GiB。
  「約 3GB」は `ollama ps` の常駐量 3.2〜3.4GB の話）。QAT 版 `e4b-it-qat` は 5.7GiB。初回起動だけ GPU 検出が 30 秒でタイムアウト（再起動で Metal 認識）。
- **手順 2**: OpenClaw 2026.8.1 に `api:"ollama"`・`/v1` なし・`reasoning:false`・`think:false`・`keep_alive 15m`・`timeoutSeconds 300` で設定。
  `contextTokens` は **32768**（8192 だと main のシステムプロンプト約 1 万トークンが入らず compact_only に落ちる）。
  M1 の E4B はプロンプト処理 41 tok/s なので、main（1 万トークン）は 1 往復 5 分半。軽量エージェント `local`（最小ツール）で **42 秒・ツール呼び出し成功**。
- **手順 3**: `OpenClaw_Local/plugins/local-draft`（ツール `local_draft`）。語彙（実行を伴う依頼は対象外）→ Ollama 生成 → 語彙（元の文に無い数字・URL）→
  JEV Noul「draft は source に無い事実を断定しているか」（qa_audit の質問の置き換え、しきい値 0.7）→ 未応答は `OK_UNCHECKED`。共通部品 `plugins/_shared/local_llm.js`。
- **手順 4**: `client/jev_client.py` に `JEV_BACKEND=ollama`（`/api/chat` の構造化出力で noul / choice を代行。score は unsupported）。
  `scripts/measure_local_vs_jev.py` で 6 セット 120 件を JEV live と比較（結果は下表、`vm_samples/local_vs_jev_gemma4_e4b.json`）。
  既存の `measure_*.py` は `JEV_BACKEND=ollama` を付けるだけで同じデータをローカルで回せる。

| set | n | local 正答 | JEV 正答 | 一致率 | local ms | JEV ms |
|---|---|---|---|---|---|---|
| stop | 20 | 100% | 100% | 100% | 2494 | 232 |
| pushback | 20 | 90% | 100% | 90% | 2636 | 215 |
| sheet | 20 | 95% | 100% | 95% | 3083 | 218 |
| assert | 20 | 100% | 100% | 100% | 2453 | 203 |
| approval | 20 | 100% | 100% | 100% | 2512 | 203 |
| reply（Choice） | 20 | 95% | 100% | 95% | 2787 | 192 |

  E4B は配線確認用。速度は JEV の 12 倍遅い。採用判断は M5（32GB）の 26B-A4B で `--model gemma4:26b-a4b` を回してから（手順 B-2）。
- **手順 5**: ComfyUI はソース版 0.37.0（MPS）+ comfy プロバイダ 2026.8.1 + SDXL base。Comfy Desktop（1.1.3）は `~/Applications` に置いたが初回ウィザードは GUI のため未実行。
- **手順 6**: `OpenClaw_Local/local_ai/text_overlay.py`（Pillow・ヒラギノ）。
- **手順 7**: ACE-Step 1.5 は uv 環境のみ（重み未取得・ディスク残量の都合）。`ACESTEP_NO_INIT=true` で API 起動、`/health`・`/docs` 200 を確認。
  REST を叩く小プラグイン `OpenClaw_Local/plugins/acestep-music`（ツール `music_generate_local`）。
- **手順 8**: 設定断片・ワークフロー JSON・プラグイン・実測スクリプトをGit に入れた（OpenClaw_Local `main` 初回コミット、このリポジトリ `local-ai-stage-a`）。重みは入れていない。
