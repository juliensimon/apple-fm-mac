# Apple on-device Foundation Model: what a black-box look shows

Measured on 2026-10-24. Machine: MacBook Pro, Apple M3 Max, 48 GB, macOS 27.0.1 (build 26A434).
Tool: `/usr/bin/fm` (Apple Foundation Models CLI), plus read-only listings of exported symbols
and the unified log. Raw data is in `data/`.

*Companion copy. Sections 3, 24 and 25 are left out (stubs below), with the symbol lists, package file names and asset identifiers they rest on. Section numbers are unchanged.*

Each claim has one tag:

- **[M]** measured by a command in this report
- **[N]** read from a name in a symbol table, log line or transcript. The name is real. What it means is a reading.
- **[I]** inferred. A guess that fits the evidence and is not proven.

## Scope and limits

- The macOS license forbids reverse engineering. The `fm` terms also forbid programmatic use of the
  models "except as expressly permitted". This work stayed small: several hundred short requests in all, 300 of them benchmark
  questions (27.4), no bulk output collection. No disassembly, no weight access, no SIP change.
- Symbol work means exported names from `dyld_info -exports`. It does not mean code.
- Root tools: `lsof`, `vmmap`, `footprint`, `powermetrics` and `fs_usage` need root. The script `data/inspect_fm.sh`
  ran them as one read-only pass on 2026-10-24 (results in section 11). A second script, `data/inspect_maps.sh`,
  saves the full region maps (run at 14:27, section 12).
- Declined: stack sampling and memory dumps of the model processes. A memory dump of the inference
  provider copies the model weights, and stack sampling shows Apple's internal call structure.
  Both go past observing the system and into reverse engineering it, which the license forbids.
  Both were declined on 2026-10-24. Section 10 lists what answers the same
  questions without crossing it.
- Every timing is a single run, except where noted. Treat them as ranges, not as exact figures.

## 1. Model inventory [N]

The log and the saved transcript name these assets. Versions are as logged on 2026-10-24.

| Asset | Role (reading) | Version seen |
|---|---|---|
| `instruct_3b.base` (variant `generic_sparse`) | base model, sparse variant | not logged |
| `instruct_3b.fm_api_generic_3b` | adapter on the base, for the public API | 16.1.0.13.103120 |
| `instruct_3b.fm_api_generic` | bundle that joins base and adapter | n/a |
| `instruct_3b.fm_api_generic.draft` | draft model for speculative decoding | 16.0.81525.13.204770 |
| `instruct_3b.shared_experts_cost_placeholder_3b` | shared expert weights, counted as zero cost | n/a |
| `instruct_3b.tokenizer` | tokenizer | 16.0.0.13.204691 |
| `instruct_3b.image_encoder` | image encoder | n/a |
| `instruct_300m.base` | 300M model | 14.3.81525.13.204821 |
| `instruct_300m.tokenizer` | tokenizer for the 300M model | 14.3.0.13.204674 |
| `instruct_300m.safety` | safety classifier | 14.3.0.13.103108 |
| `instruct_300m.mm_guard` | multimodal guard | n/a |
| `instruct_300m.image_tokenizer` | image tokenizer | n/a |
| `tokenoutputdenylist.template` | output deny-list | n/a |
| `safety.output.configuration` | output safety configuration | n/a |

The transcript from `--save-transcript` lists three assets per response: the draft, the tokenizer and the
adapter bundle, all `generic_sparse`.

The log also shows two inference providers, one for the 3B-labeled bundle and one for the 300M models. They run as separate processes.

**The system model is AFM 3 Core Advanced.** [M] The public API says so: `SystemLanguageModel.default.variant.displayName`
returns "AFM 3 Core Advanced", and `variant == .coreAdvanced3` is true (`data/public_api_query.swift`). The same
answer comes back for the content-tagging use case and for permissive guardrails, so use cases change the adapter,
not the base variant. Apple's AFM 3 page ([machinelearning.apple.com](https://machinelearning.apple.com/research/introducing-third-generation-of-apple-foundation-models))
describes Core Advanced as a 20B sparse model that activates 1 to 4B parameters. The asset name `instruct_3b` is
therefore a label, not a size: it does not mean a dense 3B model. The 20B and 1-to-4B figures are Apple's
claim. Nothing measured here confirms or contradicts them.

## 2. Request pipeline [N]

One `fm respond` call creates several sessions at the system daemon (`modelmanagerd`) over XPC.
The `fm` process itself holds no model. The log shows, in order:

1. a text sanitizer from `SensitiveContentAnalysisML` (`SCMLTextSanitizer`, `SafetyGuardrailTextSanitizerBackend`)
2. a session for the 3B generation bundle
3. a session for the 300M safety model
4. a session for the 300M `mm_guard` model and a multimodal sanitizer
5. a token output deny-list

The use case is logged as `FMFramework.onDevice.Public`. The daemon logs "Unentitled inference allowed" for it.
The `fm` client sees no model weights. Inference runs in an inference provider process, which belongs to
the system user `_modelmanagerd`.

## 3. Architecture evidence from symbols [N]

Not included in this repository. This section counted and listed the names exported by seven Apple frameworks (`dyld_info -exports`). The few exported names that later sections quote are names only: no code was read.

## 4. Measurements

### 4.1 Prefill and decode [M]

| Prompt tokens (counted) | Wall time, one run |
|---|---|
| 58 | 0.30 s |
| 506 | 0.57 s |
| 1,010 | 0.89 s |
| 2,004 | 1.75 s |
| 3,012 | 2.65 s |
| 4,090 | 3.90 s |
| 5,000 | 5.52 s |
| 5,994 | 7.27 s |

Wall time includes about 0.25 s of process start and session setup.
The marginal prefill rate is roughly 1,100 to 1,150 tokens/s from 1,000 to 3,000 tokens.
It falls to about 560 tokens/s between 5,000 and 6,000 tokens. The slowdown is steady and fits attention
cost that grows with length. [I]

Decode: 309 output tokens in 7.43 s, with the first streamed chunk at 0.60 s. That is about 45 tokens/s on
the M3 Max. One run.

The stream delivered 177 chunks for 309 tokens, so a chunk carried 1.75 tokens on average. This fits
speculative decoding that accepts several draft tokens per step. It does not prove it, because the CLI may
batch output. [I]

Compare with the IFP paper: 4,000 input tokens, 100 output tokens on GPU servers. The Mac is in the same
order of speed as the paper's 3B models, but the setups differ and the figures are not comparable. [I]

### 4.2 Context window [M]

The limit is 8,192 tokens in total on this Mac (M3 Max, 48 GB). Apple's WWDC26 session 241 does not state the window and tells
developers to read `contextSize` at run time "to adapt your app to the hardware it's running on", so the size can differ by
device ([session 241](https://developer.apple.com/videos/play/wwdc2026/241/)). A prompt counted at 8,102 tokens worked. One counted at 8,158 failed with
"The session's transcript exceeded the model's context size." The gap of 34 to 90 tokens is the framing
that `respond` adds.

### 4.3 Tokenizer [M]

`count-tokens` returns one token more than the text needs. Tokens below are counted minus 1.

| Text | Tokens |
|---|---|
| English word, short | 1 |
| 100 repeats of "the " | 101 |
| 10 digits | 10 (one per digit) |
| 40 digits | 40 |
| 10 identical emoji | 10 (one per emoji) |
| 64 spaces | 3 |
| 64 random hex characters | 56 |
| French sentence, 20 words | 23 |
| German compound, 41 characters | 14 |
| Japanese, 15 characters | 10 |
| Chinese, 16 characters | 10 |
| Arabic, 28 characters | 8 |
| URL, 50 characters | 21 |
| `<start_of_turn>`, `<end_of_turn>`, `<mask>`, `<s>`, `</s>` | 1 each |
| `<start_of_tur>` (one letter short) | 7 |
| `<bos>`, `<eos>`, `<pad>`, `<unk>`, `[INST]` | 3 each |
| `<|im_start|>`, `<|im_end|>`, `<|endoftext|>` | 6 each |

Digits are split one by one. That is the common design for models that must do arithmetic. [I]

The control strings `<start_of_turn>` and `<end_of_turn>` are single tokens. A one-letter change makes them 7.
This could mean the strings are reserved or very common in the training text. It does not show where the
tokenizer comes from. [I]

### 4.4 Instructions and framing [M]

- A bare prompt gets no extra text. "hi" costs 1 token.
- Any instruction adds a fixed **46 tokens**, whatever its length. Checked with 1, 2, 5, 20 and 100 words.
  So Apple wraps instructions in a template of 46 tokens that `count-tokens` does include.
  The template text is not shown anywhere. [I]
- User and response turns add about 9 tokens of framing in total (the transcript "Say hi." / "Hello!" counts 14
  where the text alone is 5).
- When asked to repeat its instructions, the model returned only the instruction text (or "NONE" with
  none set). A model's answer about its own prompt is not evidence. The template stays unseen.

### 4.5 Sampling and determinism [M]

- Greedy (`-g`) gave identical output on 3 of 3 runs.
- Default sampling also gave identical output on 3 of 3 runs on two different prompts (the octopus sentence
  and "Name a fruit", answer "Apple" three times). So the default sampler looks close to deterministic
  for short answers. Two prompts is a small sample.

### 4.6 Behavior [M]

- **Structured output** works. With a three-field schema, the answer was valid JSON
  `{"age": 22, "name": "Marie", "student": true}`. The keys came out in alphabetical order while the schema
  lists `x-order` as name, age, student. The CLI may sort keys when it prints. [I]
- **Use case** changes behavior. `--use-case content-tagging` returned a comma list of tags. The same prompt in
  the general case returned "# Technology". This fits a separate adapter per use case. [I]
- **Safety model** fires on repetitive nonsense. Prompts made from the same sentence repeated about 7,000 to
  8,000 tokens raised "The model's safety guardrails were triggered" in 4 of 8 runs. The trigger is not tied to length.
- **Images.** `respond --image` works and described an icon correctly. `count-tokens --image` fails with
  `ModelManagerError 1001` for every size. Latency with an image was 0.33 s at 64 px and 0.45 s at 2048 px,
  against 0.29 s for text. The cost is small and almost flat with resolution. This fits an encoder with a
  fixed input size. [I]

## 5. Processes and memory (no root) [M]

From `ps`, 2026-10-24:

| Process | User | RSS |
|---|---|---|
| Main inference provider (pid 9704) | `_modelmanagerd` | 1.04 GB at idle, 1.25 to 1.31 GB after inference |
| Second inference provider (pid 9700) | `_modelmanagerd` | about 340 MB |
| Safety inference provider | `_modelmanagerd` | 17 MB |
| `modelmanagerd` | `_modelmanagerd` | about 48 MB |
| `modelcatalogd` | root | 27 MB |
| `aned` | root | 100 to 155 MB |
| `ANECompilerService` | root | 100 to 160 MB |

The larger provider is most likely the 3B instance and the smaller one the 300M instance, from size alone. [I]

From the log:

- Two warnings read "Resident pages of model 40685 reported as greater than total pages 40680" and
  "11614 ... 11611". At a 16 KiB page size (`pagesize` returns 16384) these are 636 MiB and 181 MiB of model
  pages that the provider tracks as resident. They fit the two instances above. [I]
- The ANE maps a "mutable weights buffer" of 30,081,024 bytes (28.7 MiB). Mutable weights on the ANE
  suit adapter weights that change per use case. [I]
- MPSGraph resolves kernels "with adapter resource" from one of the model's asset folders. So some work
  runs on the GPU as well as the Neural Engine. [N]
- `modelmanagerd` logs "unloadIfNeededToMakeRoom skipping for zero-cost inference" many times. The
  `shared_experts_cost_placeholder` asset is the likely cause: the shared expert weights are mapped but
  not charged against the memory budget. [I]
- A metric named `com.apple.modelmanager.ifp_cache_expert_stats` is sent to analytics. The IFP expert cache
  produces statistics per request. The event failed to send on this machine. [N]
- The Neural Engine registry (`ioreg -rc H11ANEIn`) shows 16 cores, architecture `h15g`, version 176.


## 6. Hardware

### 6.1 The machine [M]

Apple M3 Max: 12 performance cores and 4 efficiency cores (`hw.perflevel0/1.logicalcpu`), 40 GPU cores
(`system_profiler`), a 16-core Neural Engine of architecture `h15g`, version 176 (`ioreg -rc H11ANEIn`), 48 GB
of unified memory, 16 KiB pages. One ANE is present ("Single-ANE System" in the log).

### 6.2 Where the compute runs [M, with an inference]

GPU load comes from `ioreg` (`AGXAccelerator`, "Device Utilization %"), sampled every 50 ms. Provider CPU time comes
from `ps cputime` on the two inference provider processes. Script: `data/hw.py`, raw samples in `data/hw.json`.

| Phase | Duration | GPU utilization mean / max | Provider CPU time | Share of one CPU core |
|---|---|---|---|---|
| Idle (before) | 1.9 s | 1.1% / 13% | 0 s | 0% |
| Prefill, 5,000-token prompt | 7.4 s | 0.1% / 6% | 0.84 s | 11% |
| Decode, 400-word story | 12.1 s | 1.8% / 21% | 2.94 s | 24% |
| Image request | 1.8 s | 0.0% / 0% | 0.45 s | 25% |
| Idle (after, three windows) | 1.8 to 1.9 s each | 0.3% to 5.1% / up to 23% | 0 s | 0% |

The idle windows reach 23%, so a 21% peak during decode is noise from the display and other apps. In short: the GPU did
not do the work, and the CPU did a small part of it. The work that remains is on the Neural Engine. [I] This is the
design the symbols point to (`ANEAJAXE5MLModel`, `ANE_MapMutableWeightsBuffer` in the log). `powermetrics` would
confirm it by showing ANE power during the run. That check needs root and is in `data/inspect_fm.sh`.

One counter-signal: the log shows MPSGraph resolving kernels "with adapter resource" from the model asset folder.
MPSGraph can dispatch to the ANE, the GPU or the CPU. Its presence does not mean GPU work. [I]

### 6.3 What the log shows the Neural Engine doing [N]

- For each request the provider maps ANE programs (`ANE_ProgramMemoryMapRequest ... success`) and unmaps them
  afterwards (`ANE_ProgramMemoryUnMapRequest`). Counts in one 25-second capture: 10 maps, 20 unmaps across the providers.
- The ANE maps a "mutable weights buffer" of 30,081,024 bytes (28.7 MiB) through `IOConnectMapMemory64`. It did this
  six times in the capture. Weights that are mutable at run time are what an adapter needs when it switches per use case. [I]
- `setAneHint(...)` calls fail with status `0xe00002f0`. Cosmetic: the hint is optional.

### 6.4 Memory arithmetic [I]

- The provider with the 3B-class asset has an RSS of 1.04 GB idle and 1.25 to 1.31 GB after inference.
- The log counts 40,680 model pages in that provider. At 16 KiB per page this is 636 MiB (667 MB). It is the part of the model
  the provider tracks as resident.
- If 667 MB is the weight set read for each token, then at 1B, 2B and 4B active parameters the average is
  5.3, 2.7 and 1.3 bits per parameter. Apple publishes none of these. The arithmetic shows only that the model cannot
  be stored as 16-bit weights in this footprint, and that a low-bit format or a cache of active experts has to be
  involved.
- Decode ran at about 45 tokens/s. If every resident byte were read per token, that is about 30 GB/s. Apple lists
  400 GB/s of memory bandwidth for the 40-core M3 Max (a spec, not measured here). Decode is therefore not limited by
  the chip's memory bandwidth. The ANE path, the draft-and-verify loop, or per-step overhead sets the speed. [I]
- `modelmanagerd` logs "unloadIfNeededToMakeRoom skipping for zero-cost inference" on most requests. The shared
  expert weights have an asset called `shared_experts_cost_placeholder`. The reading: the daemon charges them as free
  because they are mapped from storage and not held as a loaded cost. [I]

### 6.5 Hardware gates [N]

`deviceSupportsInstructionFollowingPruningModels` is a MobileGestalt flag. The catalog also has `isIFPEligible` in the
availability key and `isIFPEnabled(gestalt:)`. So IFP models are chosen per device. Which devices qualify is not visible
from here, but Apple has said so in public: an Apple Designer's accepted answer on the Apple Developer Forums (thread 843063, August
2026) lists them. AFM 3 Core Advanced (20B) runs on iPhone Air, iPhone 17 Pro and iPhone 17 Pro Max. AFM 3 Core (3B) runs on
iPhone 15 Pro, iPhone 15 Pro Max and iPhone 16 or later. Earlier Apple Intelligence devices run a prior version of the 3B model
(source not captured). A forum reporter says the two models report different context sizes, 4,096 for Core and 8,192
for Core Advanced; Apple's prose documentation and staff still say 4,096, and the only 8,192 in Apple's own material is a code
comment in WWDC26 session 241. This Mac is a Core Advanced device, so every measurement in this report is of Core Advanced; nothing
here measures Core, the model most iPhones run. Apple also says the model changes with the OS: three model versions so far (iOS 26.0
to 26.3, 26.4 and 27.0), with no API to pin one.

## 7. API-level details

### 7.1 Apple's public Swift API (`FoundationModels.framework`) [M]

Source: `FoundationModels.swiftinterface` in the Xcode SDK (macOS 27, Swift 6.4, module version 2.0.68). It is Apple's
published interface, 3,647 lines. A program that calls it (`data/public_api_query.swift`) returned, on this Mac:

| Query | Answer |
|---|---|
| `SystemLanguageModel.default.availability` | available |
| `.variant.displayName` | AFM 3 Core Advanced |
| `.contextSize` | 8192 |
| `.capabilities` | vision yes, guided generation yes, tool calling yes, reasoning no |
| `.supportedLanguages` | 24 locales: da-DK, de-DE, en-AU/GB/IN/US, es-419/ES/US, fr-CA/FR, it-IT, ja-JP, ko-KR, nb-NO, nl-NL, pt-BR/PT, sv-SE, tr-TR, vi-VN, zh-Hans-CN, zh-Hant-HK/TW |
| `tokenCount(for: "Say hi.")` | 4 (same as `fm count-tokens`) |
| `tokenCount(for: Instructions("Be brief."))` | 50 (the 46-token wrapper plus the text) |
| `PrivateCloudComputeLanguageModel().availability` | available (no request sent) |

Shape of the API:

- **Models.** `SystemLanguageModel` (on device) and `PrivateCloudComputeLanguageModel` (Apple's server model, with
  quota objects: `QuotaUsage`, `QuotaLimitReached`, `LimitIncreaseSuggestion`). Both conform to `LanguageModel`
  and have an `Executor`; a `LanguageModelExecutor` protocol lets code supply another backend.
- **Variants.** `SystemLanguageModel.Variant.core3` ("AFM 3 Core") and `.coreAdvanced3` ("AFM 3 Core Advanced").
  This Mac reports the second.
- **Use cases and guardrails.** `UseCase.general`, `.contentTagging`. `Guardrails.default`, `.permissiveContentTransformations`.
- **Adapters.** `SystemLanguageModel.Adapter(fileURL:)` and `Adapter(name:)`, `compile()`,
  `compatibleAdapterIdentifiers(name:)`, `removeObsoleteAdapters()`, `creatorDefinedMetadata`. So third-party
  adapters are part of the public design. The compiled form is tied to the base model version.
- **Context size.** `contextSize` is back-deployed: before macOS 26.4 it returns the constant 4096. From 27.0 it reads an
  internal value. On this Mac it is 8192, which matches the measurement in 4.2.
- **Token counting.** `tokenCount(for:)` takes a prompt, instructions, `[Tool]`, a `GenerationSchema` or transcript entries.
  The tools and the schema cost tokens, which matches the +48 tokens measured with one tool in 7.2.
- **Generation options.** `GenerationOptions`: `sampling` (`.greedy`, `.random(top: k, seed:)`,
  `.random(probabilityThreshold:, seed:)`), `temperature`, `maximumResponseTokens`, and `toolCallingMode`
  (`.allowed`, `.required`, `.disallowed`).
- **Guided generation.** `Generable`, `GenerationSchema`, `GenerationGuide<Value>`, `GeneratedContent`.
- **Prompt content.** Images through `Attachment(CGImage | CIImage | CVPixelBuffer | imageURL:)`, with an optional label.
  The public interface has no audio or video attachment.
- **Errors.** `LanguageModelError`: `contextSizeExceeded`, `rateLimited`, `guardrailViolation`, `refusal`,
  `unsupportedCapability`, `unsupportedTranscriptContent`, `unsupportedGenerationGuide`,
  `unsupportedLanguageOrLocale`, `timeout`. `SystemLanguageModel.Error.assetsUnavailable`. The server error
  "An unsupported generation guide was used" (7.2) is the second-last of these.
- **Dynamic instructions and profiles.** `DynamicInstructions`, `LanguageModelSession.DynamicProfile` and modifiers,
  `SessionPropertyKey`. A session can change its instructions and profile as it goes.
- **Executor channel.** `LanguageModelExecutorGenerationChannel` streams events with `Usage` (input and output counts
  and a metadata dictionary), `Reasoning`, `ToolCalls`, text fragments and text segment replacements. The type model has
  room for reasoning content even though this model reports no reasoning capability.

### 7.2 The `fm serve` HTTP server (OpenAI-compatible) [M]

Started with `fm serve --host 127.0.0.1 --port 18976` (loopback only). Endpoints from `--help`:
`GET /health`, `GET /v1/models`, `POST /v1/chat/completions`. Scripts: `data/api.py`, `data/api2.py`.

- `GET /health` returns `{"status":"fm serve is running","models":[{"available":true,"name":"system"}]}`.
- `GET /v1/models` lists one model: id `system`, `owned_by` "Apple".
- **Streaming is the default.** A request without `"stream": false` gets server-sent events (`chat.completion.chunk`,
  a role chunk, content deltas, a `finish_reason` chunk, then `data: [DONE]`).
- **Usage block** (non-streamed): `prompt_tokens`, `completion_tokens`, `total_tokens`,
  `prompt_tokens_details.cached_tokens`, `completion_tokens_details.reasoning_tokens` (always 0).
- **Fixed prompt overhead.** "Say hi in 3 words." reports 62 prompt tokens. With a system message it reports 65. The text
  alone is about 7 tokens, so about 55 tokens are added by the template. This matches the 46-token wrapper plus turn
  framing measured in 4.4. [I]

Parameter behavior, tested on one prompt ("Write one sentence about the sea.") unless noted:

| Parameter | Result |
|---|---|
| `max_tokens: 5` | Ignored. 13 tokens came back (non-streaming only) |
| `temperature: 0` | Greedy-looking: same text as `top_p: 0.1` and as the `logprobs` request |
| `temperature: 2` | Same text as the default and as an unknown parameter, so it looks ignored or clamped |
| `top_p: 0.1` | Greedy-looking text |
| `seed: 1` | Changes the text, so `seed` is honored |
| `presence_penalty`, `frequency_penalty` | Accepted. One changed the text, one did not |
| `logprobs: true` | Accepted; whether log probabilities come back was not checked |
| `stop: ["."]` | 400: "stop sequences are not supported. Truncate the model's output client-side." |
| `n: 2` | 400: "n=2 is not supported. Only a single completion per request is implemented." |
| `response_format: json_object` | 400: "not supported. Use 'json_schema' instead." |
| `response_format: json_schema` (strict) | Works: `{"age": 22, "name": "Marie"}` |
| unknown parameter (`banana`) | Ignored, no error |
| `tool_choice: "required"` | 500: "An unsupported generation guide was used." |

- **Sampling is nearly deterministic.** "Name a color." returned "Blue" in 5 of 5 runs at temperatures 0, 1 and 2.
  The default call repeats exactly. Variety needs `seed` or the sampling options in the Swift API. [I]
- **Key order.** JSON output keys came back alphabetical (`age`, `name`), not in schema order, on both paths (CLI and API).
- **System role** works and changes behavior ("Answer only in French" gave "Je vais bien, merci.").
- **Tools.** One function tool adds 48 tokens (110 vs 62). The model answered with the arguments as plain text
  `{"city": "Paris"}` in `content`. No `tool_calls` field came back, so a client cannot run the standard
  tool loop against this server as it stands. With an unrelated request ("Tell me a joke.") it refused in text.
  The Swift API has a real tool protocol and `toolCallingMode`, so this is a limit of the HTTP wrapper. [I]

### 7.3 Caching [M]

`cached_tokens` stayed 0 on all 10 calls. Latency confirms it:

| Test | Prompt tokens | Time per call |
|---|---|---|
| Same prompt, 4 times | 2,024 | 2.01 s, then 1.41 s three times |
| Same long prefix, three different tails | 2,023 | 1.41 s, 1.59 s, 1.48 s |
| Chat turns 1, 2 and 3 (history grows) | 2,028, 2,056, 2,077 | 1.77 s, 1.66 s, 1.67 s |

There is no prefix caching across requests at this layer. A chat that resends its history pays the full prefill each turn.
The first call is slower, which fits a one-time warm-up. The KV cache objects in the symbol table
(`createKVCacheEntry`, `moveKVCacheEntry`) may serve a single session. [I]

## 8. Modalities

| Modality | Status | Evidence |
|---|---|---|
| Text in, text out | Works | everything above |
| Image in | Works | capability `vision` is true; `respond --image` and the API path both accept images |
| Structured output | Works | `Generable` / JSON schema, valid output on every test |
| Tool calling | Works in Swift; text-only arguments over HTTP | 7.1, 7.2 |
| Reasoning | No | capability `reasoning` is false; `reasoning_tokens` is always 0 |
| Audio in or out | Not exposed | no flag in `fm`, no public API type; internal symbols exist (below) |
| Video | Not exposed | internal symbols exist (below) |
| Image generation | Not on this model | Apple lists a separate server image model |

**Images.** [M]
- Four test images were made with `data/make_test_images.swift`. Plain vision transcribed all of them exactly:
  English invoice text, French text with accents, the euro sign and French number spacing (`1 284,50 €`),
  Simplified Chinese with a full-width colon, and 11-point small print.
- The `--tool ocr` flag gave identical output on all four. For clean images it adds nothing. It may help on
  hard cases; none were tested.
- Latency: 0.33 s with a 64-px image, 0.45 s with 2048 px, against 0.29 s for text. The image cost is small
  and almost flat with resolution, which fits an encoder with a fixed input size. [I] `count-tokens --image` fails
  with `ModelManagerError 1001` at every size, so image token counts are not available.
- **Machine-readable codes.** Plain vision cannot decode them: for a Code128 barcode it said "This barcode does
  not encode any information", which is wrong. With `--tool barcode` it returned `INV20261042`, exactly. The same
  tool did not decode my QR code (it answered generically). The QR image was a 12x scaled generator output with no
  extra border, and a quiet-zone problem is possible, so treat the QR result as a failed test, not a verdict.

**Languages.** [M] The public API lists 24 supported locales (7.1). The model answered correctly in all ten test
languages with one prompt each: French, Japanese, Spanish, German, Korean, Arabic, Hindi, Portuguese, Russian
and Italian. Arabic, Hindi and Russian are outside the 24, so the list is a support statement, not a hard limit.
One prompt per language says nothing about quality in each.

**Audio and video: what the symbols show.** [N] Counts of matching exported names: Audio 382, Speech 154, Voice 354,
Dictation 164, Video 46. Examples: `AudioFormat.opus16K / opus24K / opus48K / pcm16K`,
`AssetBackedSpeechTokenizerBase`, `AssetBackedSpeechDetokenizerBase`, `AssetBackedVoicesOverridesBundle`,
`DictationStreamingPromptRequest`, `DictationPromptDelta`, `E5RunnerVideoTokenizerObjC`,
`Prompt.MediaCollectionAttachment.VideoFrame` (with a `timing` field). This matches Apple's AFM 3 page, which
lists dictation and expressive-voice features. The runtime has speech tokenization and detokenization, a streaming
dictation request type and a video-frame tokenizer. None of it is reachable through `fm` or the public Swift interface on
this build. What is exposed to the user is text, images, tools and structured output.

**Safety layers.** [M, N] Every request passes a text sanitizer, the 300M `safety` model and an output deny-list
(section 2). In testing, long repetitive prompts triggered "The model's safety guardrails were triggered" in 4 of 8 runs.
Permissive guardrails exist as a documented option (`permissiveContentTransformations`).

## 9. How this compares with Apple's claims

| Apple says (AFM 3 page, June 2026) | What this machine shows |
|---|---|
| Core Advanced is a 20B sparse model, 1 to 4B active | The public API reports "AFM 3 Core Advanced" on this Mac. [M] The 20B and 1-to-4B figures are not measured |
| IFP, with the full model in NAND flash | IFP symbols, a file-backed expert cache and a per-device IFP gate exist. [N] The model files cannot be read here, so flash residency is unproven |
| Active size fixed per use case | `IFPVariantConfig`, per-use-case adapters and a content-tagging use case exist. [N] Active size was not measured |
| Natively multimodal | Images work. [M] Audio and video code exists but is not exposed. [N] |
| No context length given | 8,192 tokens, from both measurement and the public API. [M] |
| No tokenizer details | Digits split one by one, 24 locales listed, 46-token instruction wrapper. [M] |
| Not mentioned | A separate draft model ships, with a configurable draft token count. [N] |
| Not mentioned | No cross-request prefix caching at the HTTP layer. [M] |
| Not mentioned | Two always-on 300M models (safety and multimodal guard) run next to the main model. [N] |

## 10. What to run next

Done on 2026-10-24: `data/inspect_fm.sh` (section 11), `data/inspect_maps.sh` (section 12), `data/inspect_scale.sh`
(section 18). Open, in order of what they would teach:

1. **Expert loading trace (root): `data/inspect_ifp.sh`.** Apple's AFM 3 page says the model "selects a fixed set of
   experts during initial processing, periodically reselecting them during generation". The earlier trace
   (section 11.4) saw no reads of the 4.6 GiB weight file in a 13-second decode, which used two prompt types. This
   script traces file activity of the main provider over ten different prompts (code, math, French, Japanese, biology,
   extraction, a content-tagging use case, and a long essay that changes topic five times). Reads on the weight
   file would show how often experts are reloaded and how many bytes each reload moves. That byte count is the size of
   one expert's feed-forward block (`expertFFNsByteSize` in the symbols), which at 2 bits per weight gives its parameter
   count. No reads would say that on a 48 GB Mac the working set stays resident.
2. **KV pool lifetime (root): `data/inspect_pool.sh`.** Samples IOSurface size once a second for 90 seconds after one
   long request (18.8).
3. **Done: ANE weight-streaming benchmark (no root), section 20.** The ANE streams 128 to 140 GB/s.
4. Cold start: let the providers unload (the log shows "Unloading InferenceProvider asset"), then time the first request.
5. Run the prefill series three times to put error bars on 4.1.
6. Compare `--use-case content-tagging` with the default on latency and output length to size the adapter switch.
7. Check `logprobs` in the API response and `max_tokens` on a streamed call; test `--tool ocr` on a blurred image;
   rebuild the QR test image with a white border of four modules and retest the barcode tool.

**Not on this list, by decision:** stack sampling, memory dumps, a debugger attach, and any change to SIP. The first
two copy or expose Apple's internals and are outside the license. The questions they would answer (which compute
unit runs the model, how big the resident weights are, what files it reads, how the KV cache is laid out) are covered
by the scripts above, which read layout, counters and file activity only.

## 11. Root run, 2026-10-24 14:22 (`data/inspect_fm.sh`)

Raw files: `data/root_run_2026-10-24/` (this copy keeps the power samples, their summary and the phase marks; the process
snapshots, the `fs_usage` trace and the entitlement listing name files inside Apple's protected asset folder and are left out).
All figures are measured [M] unless tagged. The memory figures describe
layout and counters. No process memory was read.

### 11.1 Power: the Neural Engine runs the model [M]

`powermetrics` at 250 ms, 160 samples over 40 s, matched to the workload phases by clock second.
CPU power is for the whole machine (it includes the processes that ran the measurement). ANE and GPU power are
near zero when nothing else uses them, so they belong to the workload.

| Phase | Duration | ANE power mean / max | GPU power mean / max | CPU power mean / max |
|---|---|---|---|---|
| Idle (window overlaps the tail of the warm-up request) | 2.0 s | 555 / 6,107 mW | 60 / 99 mW | 1,450 / 6,114 mW |
| Prefill, about 5,000 tokens | 5.7 s | **4,212 / 8,101 mW** | 65 / 157 mW | 1,678 / 6,114 mW |
| Decode, 400-word story | 13.1 s | **3,758 / 4,467 mW** | 62 / 110 mW | 1,669 / 3,258 mW |
| Idle (after) | 4.0 s | 0 / 0 mW | 63 / 106 mW | 765 / 1,209 mW |
| Image phase | invalid | | | the test image could not be written, see below |

- Whole run: ANE mean 1,955 mW, max 8,101 mW. GPU mean 65 mW, max 157 mW. Combined CPU + GPU + ANE mean 3,417 mW,
  max 10,240 mW.
- The GPU stayed at its idle clock (mean 341 MHz, max 579 MHz) with 11% residency, the same as with no load.
  **The GPU does not run the model.** The ANE draws 3.8 to 4.2 W in both phases and exactly 0 W when idle.
  This settles the inference in 6.2.
- Energy, from ANE power times phase length: prefill about 24 J for roughly 5,000 prompt tokens (about 5 mJ per
  token); decode about 49 J for the 400-word answer. Output tokens were not counted in this run, so there is no
  per-token decode figure.
- Prefill peaks near 8.1 W and then settles. Decode is steady near 3.8 W with a low peak (4.5 W). Decode is
  the lower-power phase, which fits a loop limited by step latency, not by compute. [I]
- Bug in the script, now fixed: the image phase took 25 ms because the output folder belonged to root, so
  `sips` could not write the test image. The image phase has no valid data.

### 11.2 Memory layout of the main inference provider (pid 9704) [M]

`vmmap -summary` and `footprint`, taken at idle and after the workload. These two snapshots agree to within a few
percent. **That is misleading: both were taken when no request was running.** The three-snapshot run in section 12
shows that IOSurface memory grows to 932 MB during a 5,000-token prefill and falls back afterward.

| Quantity | Value |
|---|---|
| Physical footprint | 293 MB (peak 1.0 GB, at load) |
| `ps` RSS | 1.44 GB |
| Resident (vmmap TOTAL) | 1.6 GB, of which dirty 310 MB |
| Virtual size | 388.9 GB (of which a 385 GB guard reservation with 0 resident) |
| Process age | started 13:47:03, so the model was loaded 35 minutes before the snapshot |

Where the memory is:

| Region | Virtual | Resident | Regions | What it is |
|---|---|---|---|---|
| **Neural-owned** ("Owned physical footprint (unmapped) (neural) (nofootprint)") | 1,066 MB | not in footprint | 7 | Memory owned on behalf of the Neural Engine. Marked "nofootprint", so it does not count against the process. It holds the static model pages (636 MiB), the draft pages, the mutable weights buffer and an expert-sized buffer (28.1). [I] |
| **IOSurface** | 245.0 MB | 244.9 MB, all dirty | 11 | Shared tensor buffers for the ANE and GPU. 245 MB is the baseline between requests. It grows during a request (section 12). |
| Untagged | 738.5 MB | 28.1 MB | 2,616 | Many small mappings, mostly not touched. 702 MB shows as reclaimable |
| Mapped file | 356.2 MB | 268.3 MB | 11 | File mappings. Only 356 MB, so most of the 4.6 GiB weight file is not mapped here (11.3) |
| `__LINKEDIT` | 1.6 GB | 581 MB | 2 | Shared-cache framework metadata |
| `__TEXT` | 476 MB | 257 MB | 484 | Framework code from the shared cache |
| `__OBJC_RO` | 118 MB | 81 MB | 1 | Objective-C metadata |
| Malloc (small, large, tiny) | 126 MB | 121 MB | 80 | Heap. Only 25 MB of it dirty |
| Everything else (`__AUTH`, `__DATA*`, stacks, dispatch) | small | small | | |

How to read this:

- **RSS is a poor guide.** `ps` reports 1.44 GB. Most of that is read-only framework pages shared with other
  processes (`__TEXT`, `__LINKEDIT`, `__OBJC_RO`: about 840 MB resident, "ReadOnly portion of Libraries"). The
  dirty memory the process really owns is 310 MB, 245 MB of it IOSurface.
- **The weights are outside the process footprint.** The 1,066 MB neural-owned allocation is larger than all other
  categories together. Its peak shows up as the 1.0 GB "peak footprint" at load time. It then moved to the neural
  owner and out of the footprint. [I]
- **Heap is small.** 25 MB of dirty malloc memory is all the Swift runtime and request handling cost.

The second provider (pid 9700), which runs the 300M models:

| Quantity | Value |
|---|---|
| Footprint | 140 MB (peak 308 MB) |
| Neural-owned | 535 MB |
| IOSurface | 128.1 MB, 10 regions, all dirty |
| Mapped file | 183.5 MB virtual, 135.5 MB resident |
| Virtual / resident | 387.8 GB / 1.3 GB |

The daemons are small: `modelmanagerd` footprint 8.4 MB, `modelcatalogd` 5.3 MB, `aned` 5.2 MB, the safety provider
5.1 MB, each `ANECompilerService` 4.7 to 4.8 MB. System state: 48 GB of RAM, no swap used, 6,888 pages in
the compressor at the end, so memory pressure played no role.

### 11.3 Files on disk and the weight file [M]

Open files of pid 9704 (`lsof`): 15 regular files, 3 directories, 3 character devices (all `/dev/null`).

| File | Size |
|---|---|
| `model.od`, the weight file | **4,948,197,376 bytes (4.61 GiB)**, open as fd 3 read-only |
| `model.odixpackage/main-h15c.odix`, the compiled ANE program (lsof printed its name truncated; vmmap names it in section 12.4) | 262,739,470 bytes (250.6 MiB), mapped twice |
| the main model's tokenizer | 11,937,280 bytes |
| two Biome instrumentation streams (`GenerativeModels.GenerativeFunctions.Instrumentation`, `...SystemInstrumentation`) | 5,242,880 bytes each, open read-write |
| `icudt78l.dat`, `dyld`, `Error.loctable`, `events.allowlist` | system files |

Pid 9700 holds `model.odi` of 136,779,240 bytes (130 MiB) and a tokenizer of 8,639,816 bytes.

What the numbers allow [I]:

- **Compression.** Apple states 20B parameters for Core Advanced. If `model.od` holds all of them, 4.948 GB is
  about 2.0 bits per parameter on average. That implies aggressive quantization. If the file holds only part of the
  model, the figure is lower.
- **Loaded share (replaced by 28.1).** The neural-owned figure is not a weight count: it moves between 1,068 and 1,173 MB across
  snapshots. The static model pages are 40,680 × 16 KiB = 636 MiB, and the routed experts chosen for a prompt are 150 to 230
  further units of 288 KiB (21). Apple says 1 to 4B of 20B parameters are active (5% to 20%); 28.1 gives about 2.9 billion per pass.
- **Two counters, one total (28.1).** The log's "40,680 model pages" (636 MiB, section 5) are part of the neural-owned memory. With
  the draft pages and the mutable weights buffer they fill the reserved ANE ranges to within 0.8%; the IOKit (neural) buffer of
  354.5 MiB comes on top.
- **Telemetry.** The provider holds two Biome stream files open for writing. Each request logs instrumentation
  events (the earlier log shows `BMStoreSource.sendEvent` on every request). The content of these events was not read.

### 11.4 File activity during the workload (`fs_usage`) [M]

12,515 lines over about 44 s, for the provider processes. Operation counts: `stat64` 9,165, `access` 638, `close` 531,
`fstat64` 399, `open` 357, `getattrlist` 227, `read` 212, `mmap` 127, `pread` 116, `map_fd` 66, `PAGE_IN_FILE` 13, `PgIn` 5,
`RdData` 5, `RdMeta` 1.

- **The weights were not streamed from storage.** Across a 5,000-token prefill and a 400-word decode, the providers
  read under 250 KB from disk: one 48 KiB read of the shared cache, five 16 KiB reads of `program.odix` (the 300M
  model's program file), and 16 to 32 KiB page-ins of Biome files. No page-in touched `model.od`. This machine has
  48 GB, so the configured weights stay loaded. On a phone with less memory, the flash paging Apple describes may
  show up; this run cannot say. `fs_usage` does not log soft faults on pages already in the file cache, so
  "not read from disk" is the claim, not "never touched".
- **Most file traffic is lookups.** 9,165 `stat64` calls in 44 s: the runtime re-checks many small asset files on
  every request. 220 opens touched asset folders. The folder of the general adapter (the one the log ties to MPSGraph
  kernels) was touched 395 times, that of the 300M program 345 times, that of the 4.6 GiB weights 183 times, and that of
  the draft model (22.1) 179 times.
- **Package format.** Model assets use `model.od`, `model.odi` and a directory `model.odixpackage` that holds
  `program.odix`, `main-unspecialized.odix` and `program-delegates`. The names are as found. Their meaning is not
  documented.

### 11.5 Entitlements of the provider [N]

From `codesign -d --entitlements` on the inference provider's app extension (names only): `com.apple.aned.private.allow`, `com.apple.aned.private.adapterWeight.allow`,
`com.apple.aned.private.processModelShare.allow`, `com.apple.developer.ane.increased-model-size-limit`,
`com.apple.modelcatalog.full-access`, `com.apple.keystore.sik.access`, `com.apple.appattest.spi`,
`com.apple.mobileactivationd.device-identifiers`, `com.apple.PerfPowerServices.data-donation`.

- `adapterWeight.allow` fits per-use-case adapter weights loaded into the ANE (6.3).
- `processModelShare.allow` fits the ANE model memory being shared across processes, such as the neural-owned
  allocation in 11.2.
- `increased-model-size-limit` is the ANE's per-model size limit, raised for this process.
- The ANE is `H11ANEIn`, power state 0 at idle (it powers down when unused), maximum state 1.

### 11.6 What 11 changes in sections 6 and 10

- 6.2 is now measured: the ANE runs the model, the GPU does not.
- 6.4's open question about where the weights live is answered in part: the static model pages (636 MiB) and the expert buffers sit in a
  neural-owned allocation outside the footprint (about 1.0 GiB in all, 28.1), backed by a 4.6 GiB file on disk.
- The flash-paging claim (section 9) is not testable on a 48 GB Mac. A test needs a memory-limited device or a forced
  memory squeeze.
- Next step, if wanted: `data/inspect_maps.sh` saves the full region maps (every region with its address range, size,
  residency and backing file) at three points: idle, 3 s into a prefill, and after. That allows a region-by-region diff.
  Still metadata only, no memory contents.

## 12. Memory maps at three points (`data/inspect_maps.sh`, 2026-10-24 14:27)

Raw data: 93 files (for each process and snapshot, the full `vmmap -v -interleaved` region list, the summary, `footprint`
and `lsof`), left out of this copy because they list file paths inside Apple's protected asset folder; the tables derived
from them are `data/plots/memory_by_region_type.csv`, `iosurface_regions.csv`, `neural_and_gpu_regions.csv` and
`footprint_categories.csv`. Parser: `data/maps_parse.py`. Only layout was saved, no memory
contents. Snapshots: **idle** (1 s after a one-word request), **during** (3 s into a 5,000-token prefill), **after**.

### 12.1 Main provider (pid 9704): what changes with a request [M]

| Counter | Idle | During prefill | After |
|---|---|---|---|
| Dirty memory, all regions | 473 MB | **1,010 MB** | 308 MB |
| IOSurface regions (count) | 65 | 66 | fewer |
| IOSurface resident | 406 MB | **936 MB** | 245 MB |
| Malloc small, dirty | n/a | 33.8 MB | 24.6 MB |
| Mapped files, resident | 311 MB | 314 MB | 268 MB |

(`vmmap -v` lists every split shared-cache library, so total "resident" includes pages shared with the whole system.
Use dirty memory and IOSurface to read the process's own cost.)

**This corrects section 11.2.** The earlier idle and after snapshots both fell between requests and showed a constant
245 MB. The IOSurface footprint is not constant. A request allocates tensor buffers and frees them when it ends.

### 12.2 IOSurface: a baseline and transient buffers [M]

All IOSurfaces carry the tag `ODIE` (an ANE client label; one more carries `MetalPerformanceShadersGraph`). IDs differ
between snapshots (for example `0x115` at idle and `0x11e` during), so the buffers are recreated for each request.

| Snapshot | Large surfaces (8 MB and up) | Total |
|---|---|---|
| After | 192.0 MB (`0x17a`) + 52.9 MB (`0x179`) | **244.9 MB**, the persistent baseline |
| Idle (after a tiny request) | baseline + 8 more between 12 and 32 MB each | 404 MB |
| During 5,000-token prefill | baseline + **two 280.0 MB surfaces** (`0x148` at `0x706e684000`, `0x14a` at `0x707fe84000`) + 7 of 12 to 24 MB | 932 MB |

- The two 280 MB surfaces sit in the ANE's address window, right after the 354.5 MB "IOKit (neural)" mapping
  that ends at `0x706e684000`. They existed in neither the idle nor the after snapshot. [M]
- **Corrected by section 18:** these two surfaces are the K and V caches sized for the 8,192-token bucket
  (293,601,280 bytes each, exactly 8,192 × 35,840). The 17.5 MiB pair at idle is the same cache at the 512-token bucket
  (18,350,080 bytes, exactly 512 × 35,840). Their size follows the bucket, not the exact prompt length.
- Memory for the ANE is not a fixed cost. The K and V pair adds 35 MiB at the 512 bucket and 560 MiB at the 8,192 bucket
  on top of the 245 MB baseline, the fixed scratch buffers and the roughly 1.0 GiB of neural-owned memory (static model pages and expert buffers, 28.1).

### 12.3 The ANE address space [M]

`vmmap` labels these region types:

| Type | Regions | Virtual size | Resident to the CPU |
|---|---|---|---|
| Neural Engine (reserved) | 7 | 678.6 MB | 0 |
| IOKit (neural) | 1 | 354.5 MB | 0 |
| GPU Carveout (reserved) | 3 | 75,673.6 MB (51.2 GB + 12.3 GB + 12.2 GB) | 0 |

- The ANE ranges are **five slabs of 128.0 MB plus one of 27.6 MB**, contiguous from `0x7000000000`, plus one of
  11.0 MB near `0x127630000`. Slabs of equal size look like an allocation pool. [I]
- The CPU never touches these pages (0 resident), which is why they are "nofootprint". Together they come to
  1,033 MB, close to the 1,066 MB that `footprint` reports as owned by the neural engine. The 3% gap is not explained.
- The "GPU Carveout" is 75.7 GB of reserved, unallocated address space. It is Metal's reservation. No GPU memory is
  used, in line with the power data in 11.1. The 385 GB "Guard" region is also a reservation.
- The 300M provider (pid 9700) reserves 849 MB of ANE ranges while a request runs and **releases all of them when
  idle** (0 MB in the "after" snapshot). The main provider keeps its 678.6 MB reserved between requests.

### 12.4 Mapped files: the model package [M]

Mapped files of pid 9704 at idle, grouped by file. The `model.odixpackage/` files belong to the base model's asset:

| File | Regions | Virtual | Resident | Share mode |
|---|---|---|---|---|
| `model.odixpackage/main-h15c.odix` | 2 | 501.2 MB | 246.7 MB | shared alias |
| `model.odixpackage/ifp/ifp_rasterized_weights.bin` | 3 | 49.5 MB | 14.6 MB | copy-on-write |
| `model.odixpackage/ifp/project_experts.mlasset/...` | 1 | 9.0 MB | 9.0 MB | private |
| the draft model's `program.odix` | 1 | 33.5 MB | 32.6 MB | private |
| the tokenizer | 1 | 11.4 MB | 4.0 MB | private |
| the general adapter's `adapter.odixpackage/program.odix` | 1 | 0.3 MB | 0.3 MB | private |
| Biome instrumentation streams (2 files) | 4 | 10.0 MB | 3.0 MB | shared alias |
| `icudt78l.dat` | 1 | 34.4 MB | 0.8 MB | shared alias |

- `main-h15c.odix` is the file lsof showed as 262,739,470 bytes (250.6 MiB), mapped twice. Its name carries the chip
  family `h15` (this Mac's ANE is `h15g`): a program compiled for the ANE generation. [N]
- The 4.6 GiB `model.od` has **no mapping**. It is open on file descriptor 3 and nothing else. A pread-driven reader
  fits `FileBackedExpertCache` and `CacheExpertExpertCache`, whose constructor takes an `expertPath` and a
  `weightBaseOffset`. That reading is confirmed in section 21: `model.od` is `ifp/ifp_rasterized_weights.bin`, and the provider reads
  it in 288 KiB units while it generates. [M]
- `ifp/ifp_rasterized_weights.bin` and `ifp/project_experts.mlasset` are the on-disk side of the IFP names in the
  symbols (`IFPExpertCache`, `ExpertProjector`). "Rasterized" suggests weights pre-arranged in a layout for fast fetch. [I]
- The adapter is a program file of 0.3 MB (`adapter.odixpackage/program.odix`), tiny next to the base. [M]

The 300M provider (pid 9700): the 300M model's `program.odix` is mapped in 3 regions (391.5 MB virtual, 128.9 MB
resident), plus a tokenizer (8.2 MB) and two 0.1 MB adapter programs. Its IOSurface memory runs 166 MB (idle), 257 MB
(during) and 128 MB (after).

### 12.5 File descriptors [M]

The set of open descriptors of pid 9704 did not change between idle and during (18 regular files, 3 directories,
3 character devices in both). No descriptor is opened per request. The `stat64` traffic in 11.4 uses short-lived calls.

## 13. Architecture summary: what is known and what is not

**Update after sections 18 to 20.** Three things changed this summary: the KV cache is allocated in buckets of 512 to 8,192
tokens at 35,840 bytes per token for K and for V (35 layers × 8 KV heads × 128 × 1 byte, a reading that fits 56 layers in
total); decode cost follows the bucket, so attention runs over padded shapes; and the model is not memory-bandwidth-bound
(the ANE streams 128 to 140 GB/s, decode consumes 38 GB/s, 200 GB/s of competing CPU traffic costs 10 to 20%). The bullets
below that mention a 245 MB baseline plus transient buffers are corrected in section 18. Sections 21 to 25 add: experts are read
from the 4.6 GiB file in 288 KiB units, reselected about every 33 tokens, and loaded ahead of topic changes; the default API
uses the 3B-active configuration of a model with 1B, 2B and 3B variants (25, not included); adapters are rank-48 LoRAs run by
MPSGraph; the compiled packages are ODIE programs with BNNS and MPSGraph backends (24, not included); section 26 maps what is
still unknown.

### Identity and interface [M]

AFM 3 Core Advanced, as reported by Apple's public API. Context 8,192 tokens. Vision, tool calling and guided generation:
yes. Reasoning: no. 24 supported locales. Default sampling is nearly deterministic.

### The system around the model [N]

One request touches five models and three filters:

1. A text sanitizer (SensitiveContentAnalysisML).
2. A 300M safety classifier and a 300M multimodal guard, in a separate provider process.
3. The main model: a base, plus an adapter for the use case (`fm_api_generic`), plus a draft model for speculative
   decoding, plus a "shared experts" asset, plus its own tokenizer and image encoder.
4. An output deny-list and an output safety configuration.
5. Telemetry events to Biome streams.

The main model and the 300M models run in two different processes with different tokenizers (11.9 MB and 8.6 MB files).

### The sparse design [N, I]

The pieces match the IFP method that Apple's AFM 3 page names:

- Files: `ifp/ifp_rasterized_weights.bin`, `ifp/project_experts.mlasset`, and a 4.6 GiB weight store.
- Code: `IFPExpertPicker`, `IFPExpertCache`, `FileBackedExpertCache`, `ExpertProjector(hiddenState:topK:sharedExpertsPerLayer:)`,
  `IFPSwizzler`, a per-device IFP gate, and per-layer sizes in the cache constructor (`expertsPerLayer`,
  `expertFFNsByteSize`, `layerCount`).
- Numbers: the weight store is 4.95 GB. The ANE holds 636 MiB of static model pages (28.1) and the prompt selects 150 to 230
  expert units of 288 KiB. Apple states 20B parameters with 1 to 4B active (5% to 20%). At 2 bits the static pages are at
  most 2.7 billion weights and the selected experts add about 0.2 billion: about 2.9 billion per pass, the 3B configuration
  (25, not included). If the file holds all 20B parameters, the average is about 2 bits per parameter.
- A hypothesis worth testing: the IFP paper's sparsity predictor has a 302M-parameter backbone, and a 300M
  base model runs next to the main model on every request. The 300M base could be that predictor, or only the
  safety classifier. The paper's predictor also has a small MLP head, and `project_experts.mlasset` could be it.
  A test: change the use case and watch whether the 300M provider's activity changes the experts read from
  `model.od` (`fs_usage`).

### How it runs on the hardware [M]

- Compute is on the Neural Engine: 3.8 to 4.2 W during prefill and decode, 0 W idle. The GPU is idle (65 mW).
- The model is compiled ahead of time for the ANE family (`main-h15c.odix`) and loaded into ANE-owned memory
  (636 MiB of static pages, about 1.0 GiB of ANE ranges and buffers in all, 28.1). The CPU never maps those pages.
- Adapters use a 28.7 MiB mutable weights buffer on the ANE. The adapter program file is 0.3 MB.
- Per-request memory is a persistent 245 MB baseline of IOSurface buffers, about 160 MB of fixed scratch buffers, and a
  K and V pair sized by the context bucket (512, 1,024, 2,048, 4,096 or 8,192 tokens): 35,840 bytes per token each,
  560 MiB for the pair at 8,192 (section 18).
- There is no prefix cache between requests. A draft model generates candidate tokens (speculative decoding).
- Prefill runs near 1,100 tokens/s at 1,000 to 3,000 tokens and about 560 tokens/s near 6,000. Decode runs near 45 tokens/s.

### Not known

Layer count, hidden size, number of experts, expert size, attention variant, vocabulary size, bit widths, the draft
model's size, and the routing method in detail. Apple does not publish these and the work here did not look for them
beyond names and sizes.

## 14. Compute against context length (`data/profile_ctx.py`)

Method: for nine prompt lengths (20 to 6,881 tokens), two runs each, `fm respond --stream -g`. Time to first chunk
(TTFT) measures prefill plus about 0.25 s of process start. Decode speed is output tokens divided by the time from
first to last chunk. The task is "count from 1 to 60", 172 output tokens, which keeps the output identical across
lengths for the first seven rows. Raw data: `data/profile_ctx.json`.

| Prompt tokens | TTFT | Decode tok/s | ms per decoded token |
|---|---|---|---|
| 20 | 0.47 s | 72.1 | 13.9 |
| 511 | 0.63 s | 68.9 | 14.5 |
| 1,001 | 0.99 s | 62.0 | 16.1 |
| 1,981 | 1.60 s | 50.0 | 20.0 |
| 2,961 | 2.68 s | 49.8 | 20.1 |
| 3,941 | 3.60 s | 41.8 | 23.9 |
| 4,921 | 5.58 s | 35.6 | 28.1 |
| 5,901 | 7.53 s | 32.1 | 31.1 (different output, see below) |
| 6,881 | 9.48 s | 32.6 | 30.7 (different output) |

### 14.1 Prefill is quadratic [M]

- A linear fit gives R² = 0.951. A quadratic fit gives R² = 0.998 and cuts the residual sum of squares 24.3-fold (root-mean-square error 0.680 s against 0.138 s, 18 runs; a cubic term adds nothing). Corrected 2026-10-25: an earlier version said 30-fold.
- Fitted: TTFT = 0.498 s + 0.247 ms × n + 0.156 µs × n². The constant is process start and setup.
- The linear term (0.247 ms per token) is the cost of the dense layers: projections and feed-forward. The quadratic
  term is attention.
- At 1,000 tokens the quadratic term is 0.16 s of 0.99 s. At 4,000 it is 2.5 s of 3.7 s. At 8,000 it is
  10 s against 2 s of linear work. **Beyond about 2,000 tokens, attention dominates prefill.**
- Attention here is full (global) over the prompt on enough layers to keep the quadratic term. A design with local layers
  and a few global ones, as in Apple's server model and in Gemma 3, would still show a quadratic term from the global
  layers, with a smaller coefficient. No flattening appears up to 6,881 tokens, so the data show no short window on all
  layers; they do not exclude a mix of local and global layers. [I]

### 14.2 What the linear term implies [I]

- 0.247 ms per token is a dense-layer rate of about 4,050 tokens/s: the rate without the fixed 0.5 s and without the attention
  term. The observed rate is lower (about 1,100 tokens/s between 1,000 and 3,000 tokens, 4.1).
- A forward pass costs about 2 FLOPs per active parameter per token. At 4,050 tokens/s: 1B active parameters need
  8 TFLOP/s, 2B need 16, and 4B need 32.
- Apple's published peak for an M3 Neural Engine is 18 TOPS (from memory, not measured here). A sustained 32 TFLOP/s
  does not fit that. Two readings: the prefill touches fewer than all the weights of a pass (Apple's 2025 design skips
  the second block of layers, 37.5% of them, during prefill because it has no K and V projections), or the active set is
  nearer 2B than 4B. With about 2.9 billion weights per pass (28.1), 62.5% of them is 1.8 billion, which needs 14.6 TFLOP/s
  at 4,050 tokens/s and fits under 18 TOPS. The first reading fits. Neither is proven.

### 14.3 Decode slows with context, in steps [M]

- At 20 tokens of context decode runs at 72 tokens/s. At 4,921 tokens it runs at 36.
- Linear fit on the seven rows with identical output: **13.4 ms + 2.79 µs per context token** per decoded token.
  The 2.79 µs is the extra cost of reading the KV cache for every context token, once per decoded token.
- The cost is stepped: 1,981 and 2,961 tokens give the same 20.0 ms. A flat stretch between rows points to compiled
  shapes with bucketed KV lengths (`FlexibleShapeAJAXE5MLModel` in the symbols). [I]
- The KV size is now known (section 18): 71,680 bytes per bucket token for K and V. Refitting against the bucket gives
  1.90 µs per bucket token and about 37.8 GB/s of effective read bandwidth (18.5).
- The two longest rows had a different output: the model did not stop at 60 numbers and repeated the filler
  sentence for 1,241 and 2,221 tokens. Repeated text is easy to predict, so speculative decoding accepts more draft
  tokens and the rate is not comparable. The speed of 72 tokens/s on counting also exceeds the 45 tokens/s on prose
  for the same reason. **Decode speed depends on how predictable the text is**, which supports a draft-and-verify loop. [I]
- A prompt that asks for a short, closed answer can still run to the end of the context if the model does not stop.
  `maximumResponseTokens` in the Swift API is the guard; `max_tokens` over HTTP is ignored (7.2).

### 14.4 Memory against context length

Measured in section 18: IOSurface memory steps up at powers of two (512 to 8,192 tokens), as the KV cache is
allocated per bucket.

## 15. The Google connection

Apple's AFM 3 page says the third generation is "custom-built in collaboration with Google". This section lists what
the Mac shows that bears on it. It is evidence about the tokenizer, not about the architecture.

### 15.1 The tokenizer shares Gemma's reserved tokens [M]

`fm count-tokens` on single strings (tokens, overhead removed):

| String | Tokens | Note |
|---|---|---|
| `<start_of_turn>`, `<end_of_turn>` | 1, 1 | Gemma chat-template tokens |
| `<start_of_image>`, `<end_of_image>` | 1, 1 | Gemma 3 image delimiters |
| `<unused0>`, `<unused99>` | 1, 1 | Gemma reserved slots |
| `<mask>`, `[multimodal]` | 1, 1 | Gemma special tokens |
| `<table>`, `<caption>`, `<thead>`, `<tr>`, `<td>`, `<h1>`, `<blockquote>`, `<code>`, `<div>`, `<span>`, `<ul>`, `<li>` | 1 each | HTML tokens |
| `<p>` | 3 | one HTML tag that is not a token |
| `<unused12>` | 5 | a reserved slot that is not a token here |
| `<2mass>`, `<image_soft_token>` | 4, 7 | Gemma tokens that are missing here |
| `<bos>`, `<eos>`, `<pad>`, `<unk>` | 3 each | Gemma's own BOS and EOS markers are not single tokens |
| `<unused>`, `<unused1234567>`, `<start_of_turns>`, `<begin_of_turn>`, `<start_of_audio>` | 3, 10, 7, 7, 7 | near-misses cost many tokens |
| `<|im_start|>`, `<|begin_of_text|>`, `<|start_header_id|>`, `<|endoftext|>`, `<|fim_prefix|>` | 6, 8, 8, 6, 6 | other families' markers: plain text |

Reading: a one-token `<start_of_turn>` and `<unused99>`, with near-misses at 7 to 10 tokens, cannot happen by chance.
The vocabulary contains Gemma's reserved strings, including image delimiters and HTML table tags. It does not contain
all of them (`<bos>` is plain text, `<unused12>` is changed). Section 27.1 settles the question: the token counts equal
Gemma 3's on 429 of 429 strings, so this is Gemma 3's tokenizer with changed reserved slots and control strings. [M, I]
Digits split one by one, which Gemma's tokenizer also does.

### 15.2 What Gemma 3n does that Apple's design resembles [sources, not measured]

From Google's public Gemma 3n material ([developer guide](https://developers.googleblog.com/en/introducing-gemma-3n-developer-guide/),
[InfoQ](https://www.infoq.com/news/2025/07/gemma-3n-architecture), [Hugging Face on MatFormer](https://huggingface.co/blog/rishiraj/matformer-in-gemma-3n)):

| Technique | Gemma 3n | Apple on-device (Apple's 2025 report and this Mac) |
|---|---|---|
| KV-cache sharing across layers | Yes. Top layers reuse K and V of lower layers. About 2x faster prefill versus Gemma 3 4B | Yes. Block 2, 37.5% of layers, has no K and V projections and reuses Block 1's cache. Prefill skips Block 2 |
| Parameters kept out of accelerator memory | Per-layer embeddings computed on the CPU. Only the core 2B or 4B must fit | IFP: the full model (20B per Apple) stays on storage and about 1 to 4B active parameters load |
| Nested or elastic sizes | MatFormer: E2B is a sub-network of E4B | "Inference-time elasticity": a fixed active size per use case |
| Low-bit weights | not the point of the design | 2 bits per weight with quantization-aware training, 4-bit embeddings, 8-bit KV cache |

The shared idea is "run fewer parameters than you store, and reuse the KV cache". The mechanisms differ: Gemma 3n
nests sub-models and offloads embeddings; Apple selects an expert subset per prompt.

### 15.3 Open Google models to study for the unknowns

- **Gemma 3n** for KV sharing behavior and for the layer split between shared and unshared blocks.
- **Gemma 3** for the local and global attention mix (five local layers with a 1,024-token window to one global layer,
  per Google's report; this was not re-checked here) and for tokenizer behavior.
- A test that would link them: if Apple's model has local-attention layers, prefill cost would stop growing
  quadratically once a prompt passes the window. Section 14.1 shows no such break up to 6,881 tokens.

## 16. Language support

| Source | Result |
|---|---|
| Public API `supportedLanguages` | 24 locales: da-DK, de-DE, en-AU/GB/IN/US, es-419/ES/US, fr-CA/FR, it-IT, ja-JP, ko-KR, nb-NO, nl-NL, pt-BR/PT, sv-SE, tr-TR, vi-VN, zh-Hans-CN, zh-Hant-HK/TW |
| `supportsLocale()` on 35 test locales [M] | **True:** en-US, fr-FR, fr-CH, de-AT, es-MX, pt-BR, it-IT, nl-BE, ja-JP, ko-KR, zh-Hans-CN, zh-Hant-TW, tr-TR, vi-VN, da-DK, sv-SE, nb-NO. **False:** yue-HK, ar-SA, he-IL, hi-IN, ru-RU, uk-UA, pl-PL, cs-CZ, el-GR, th-TH, id-ID, ms-MY, fa-IR, fi-FI, ro-RO, hu-HU, bn-BD, sw-KE |
| Answers to one prompt each (CLI) [M] | Correct, in the right language, for French, Japanese, Spanish, German, Korean, Italian and Portuguese (supported) and also for **Arabic, Hindi and Russian (unsupported)** |
| Public API error type | `LanguageModelError.unsupportedLanguageOrLocale` exists. The CLI did not raise it on the three unsupported languages tested |
| Safety assets [N] | `instruct_300m.safety?language=en` and `instruct_300m.mm_guard?language=en` are requested per language, and the sanitizer logs the locale (`en_US`, `fr_FR`). A deny-list lookup is keyed to region and language and found "no deny list associated" for this one |

So the list is a statement of tested and safety-covered locales. The model's knowledge is wider. Safety classifiers
are the part tied to language, and they may not cover the unsupported ones. The two non-obvious facts:
variants of a supported language pass (fr-CH, de-AT, es-MX, nl-BE), while Hebrew, Arabic, Hindi and Russian do not.

### 16.1 Tokenizer efficiency across scripts [M]

The same sentence ("the weather is nice today, so we are going to walk in the park with our friends") in 18 languages:

| Group | Tokens relative to English (19 tokens) | Characters per token |
|---|---|---|
| German, Portuguese | 0.89 | 4.4 to 5.0 |
| French, Spanish, Dutch, Turkish, Italian, Swedish | 0.95 to 1.11 | 3.1 to 4.4 |
| Vietnamese | 1.16 | 3.5 |
| Japanese, Chinese, Korean | 0.74 to 0.84 | 1.6 to 2.1 |
| Hindi, Russian, Thai | 0.89 to 0.95 | 3.2 to 3.9 |
| Arabic | 1.21 | 2.6 |
| Hebrew | **1.37** | 2.5 |

No script costs more than 1.4 times English. Thai, Hindi and Russian cost less than English. That is the profile of a
large multilingual vocabulary, as Gemma 3's 262k vocabulary gives (27.1). Hebrew and Arabic are the most
expensive. Since Hebrew and Arabic are also locales marked unsupported, the tokenizer is not the bottleneck for
language support. [I]

## 17. Open architecture questions

### 17.1 MHA, GQA or MQA?

- **Symbols:** no name for any attention variant. The exports contain `selfAttention`, `fullAttention`, `isSelfAttentionModule`
  and `setSelfAttentionBuffer` for prompt handling, and `KVCacheEntry`, `KVCacheTokensMatchCount` for the cache.
  There are no head counts, no `GQA`, `MQA` or `MLA`, and no rotary or sliding-window names. (An earlier keyword
  count showed hits for `RoPE` and `MLA`; they were substrings of `Property` and similar words.)
- **Apple's own predecessor [source: [2024 tech report](https://arxiv.org/abs/2407.21075)]:** AFM-on-device used GQA
  with 8 KV heads, 24 query heads, head dimension 128, 26 layers, model dimension 3,072, SwiGLU, RoPE with base
  frequency 500k, a shared input and output embedding, vocabulary 49k, 2.58B non-embedding and 0.15B embedding parameters.
  The 2025 report ([arXiv 2507.13575](https://arxiv.org/abs/2507.13575)) states no layer or head counts for its
  successor. It describes KV sharing (62.5% / 37.5%), 2-bit QAT, a 4-bit embedding table and an 8-bit KV cache.
  None of this is a measurement of AFM 3 Core Advanced.
- **What the buffer sizes show (section 18):** one K or V tensor is 35,840 bytes per token of bucket capacity, seen as
  exact surface sizes at two buckets (512 and 8,192) and as the step sizes of a ten-prompt scaling run. That is
  35 layers × 8 KV heads × 128 head dimension × 1 byte, or an equivalent with 35, 70 or 140 KV layers. It fits
  grouped-query attention with 8 KV heads, the 8-bit KV cache of Apple's 2025 report, and 35 layers as 62.5% of 56.
  It does not fit 24-head multi-head attention. The numbers are consistent with that reading, not a proof of it.

### 17.2 Layers, hidden size, vocabulary

Not stated by Apple for AFM 3. The KV-cache size (18.4) gives a candidate of 56 layers, 35 of them with KV, and the 24 MiB buffer (18.6)
a candidate hidden size of 3,072. Both are inferences. What else exists:

- Vocabulary: 262,144 entries, Gemma 3's tokenizer (27.1). The tokenizer file is 11.9 MB for the main model and 8.6 MB for the
  300M models (different files). The 150k of the 2025 report belongs to the previous generation.
- Per-layer sizes appear only as constructor arguments (`expertsPerLayer`, `expertFFNsByteSize`, `layerCount`).
  The values sit inside asset configuration that was not read.
- Constraint from weights: 4.948 GB at 2 bits is 19.8B parameters; the 636 MiB of static pages at 2 bits are at most 2.7B (28.1). With a hidden size d,
  a layer count L and a SwiGLU feed-forward of width f per expert, parameters per layer are about 4d² (attention, less
  with GQA) + 3·d·f·(experts). Several (d, L, f, experts) combinations fit, so this does not isolate one.

### 17.3 Do we see up and down projections?

No, and not by name. The exported symbols contain no `up_proj`, `down_proj`, `gate_proj`, `Linear` or `MLP`. The only
feed-forward names are `expertFFNsByteSize` (one number, the byte size of one expert's whole feed-forward block),
`FileBackedSwizzler.expertFFNsByteSize`, `IFPSwizzler` (a weight layout routine), and `ExpertProjector.callAsFunction(hiddenState:topK:sharedExpertsPerLayer:)`
(the router). The weights are inside compiled ANE programs (`main-h15c.odix`) and weight files (`ifp_rasterized_weights.bin`,
`model.od`), and the memory layout shows them as opaque neural-owned regions of 128 MB slabs, not as named matrices.
The IFP paper ([arXiv 2501.02086](https://arxiv.org/abs/2501.02086)) prunes the feed-forward
intermediate dimension: columns of the first projection and rows of the second, which is the up and down projection pair.
Seeing the individual matrices would mean reading the weight files or the process memory, which stays out of scope.

### 17.4 Stack sampling

Not done, for the reason in the scope section. The software stack as a layering
is in sections 2 and 5: client, `modelmanagerd`, two providers, `aned`, hardware.

## 18. Memory against context length: the KV cache (`data/inspect_scale.sh`, 2026-10-24)

This section replaces the guesses in 12.2 and 17.1 about the two 280 MB buffers. The scale run gives the exact answer
to the shape of those buffers, and it ties the model to Apple's published KV-cache design.

### 18.1 Method [M]

Root script `data/inspect_scale.sh`, two passes over ten prompts of 17 to 540 repeats of one sentence (248 to 7,570
counted tokens). While each `fm respond --no-stream -g` ran, it sampled `vmmap -summary` of the main provider about
once per second and kept the largest IOSurface resident size. Output: `data/scale_run_2026-10-24/`
(`scale_summary.tsv`; the `vmmap -summary` kept at each peak is left out of this copy, its header names the provider process). Pass 1 only is used below.

### 18.2 Peak IOSurface memory steps up at powers of two [M]

| Counted prompt tokens | Plus about 56 template tokens | Bucket | Peak IOSurface, MiB | Step vs previous row |
|---|---|---|---|---|
| 248 | 304 | 512 | 406.6 | |
| 500 | 556 | 1,024 | 476.8 | +70.2 |
| 990 | 1,046 | 2,048 | 547.2 | +70.4 |
| 1,970 | 2,026 | 2,048 | 547.5 | +0.3 |
| 2,950 | 3,006 | 4,096 | 688.0 | +140.5 |
| 3,930 | 3,986 | 4,096 | 688.0 | 0.0 |
| 4,910 | 4,966 | 8,192 | 968.8 | +280.8 |
| 5,890 | 5,946 | 8,192 | 968.8 | 0.0 |
| 6,730 | 6,786 | 8,192 | 968.8 | 0.0 |
| 7,570 | 7,626 | 8,192 | 968.8 | 0.0 (this run ended after 3.4 s with a guardrail error; the value is the retained pool) |

Memory does not grow smoothly with the prompt. It grows only when the prompt crosses 512, 1,024, 2,048 or 4,096
tokens, counting about 56 tokens of hidden template. The bucket sizes are 512, 1,024, 2,048, 4,096 and 8,192,
the same ladder as the compiled-shape hints in the symbols (`FlexibleShapeAJAXE5MLModel`).

### 18.3 The steps are a K and V pair sized by the bucket [M]

One K or V tensor needs **35,840 bytes per token of bucket capacity**. Two independent facts give that number:

- The 280.0 MiB surfaces seen during the 5,000-token prefill (section 12.2) are 293,601,280 bytes each. That is
  exactly 8,192 × 35,840.
- The 17.5 MiB surfaces seen at idle (two of them, section 12.2) are 18,350,080 bytes each. That is exactly 512 × 35,840.

The same bytes per token at two different bucket sizes, in pairs, is what K and V caches look like.
The model "fixed 406.6 MiB + K and V pair for the bucket" reproduces the run:

| Bucket | K + V pair (2 × 35,840 × B) | Predicted peak | Observed | Error |
|---|---|---|---|---|
| 512 | 35.0 MiB (already in the fixed part) | 406.6 | 406.6 | 0.0 |
| 1,024 | 70.0 | 476.6 | 476.8 | +0.2 (0.04%) |
| 2,048 | 140.0 | 546.6 | 547.2 | +0.6 (0.11%) |
| 4,096 | 280.0 | 686.6 | 688.0 | +1.4 (0.20%) |
| 8,192 | 560.0 | 966.6 | 968.8 | +2.2 (0.23%) |

The error grows slightly with the bucket, a free fit gives 71,969 bytes per token against 71,680 predicted (0.4% more).
A few hundred bytes per token of other per-token buffers would explain it. Each new bucket frees the smaller pair
and allocates a larger one, which is why the steps equal the increase between pairs (70, 140, 280 MiB), not the pair itself.

### 18.4 What 35,840 bytes per token means [I]

35,840 = 2^10 × 5 × 7. A K or V tensor holds layers × KV heads × head dimension × bytes per value for each token.

- With the usual power-of-two head setups, the number of layers that hold a KV cache must be **35, 70 or 140**.
  The factor 5 × 7 cannot come from heads or dimensions that are powers of two. (The full list of 36 factorizations,
  including odd head counts, is in `data/plots/kv_factorizations.csv`.)
- **35 layers × 8 KV heads × 128 head dimension × 1 byte** is the natural reading. 8 KV heads of dimension 128 is
  the design Apple published for its first on-device model ([2024 report](https://arxiv.org/abs/2407.21075)), and Apple's
  [2025 report](https://arxiv.org/abs/2507.13575) says the KV cache is quantized to 8 bits.
- Apple's 2025 on-device design keeps K and V in the first 62.5% of the layers and shares them with the rest.
  **35 layers is exactly 62.5% of 56.** That would make the model 56 layers deep, 35 with their own KV cache and 21
  that reuse it. Only multiples of 5 give a whole number here, so the match is mild evidence (one chance in five),
  not proof.
- Other readings fit the bytes: 70 KV layers × 4 heads × 128 × 1 byte, 35 layers × 4 heads × 128 × 2 bytes (bf16), or
  35 layers × 8 heads × 64 × 2 bytes. All keep the factor 35 and a 1,024-byte KV slice per layer per token.
- **Attention is grouped-query, not 24-head multi-head**, for every power-of-two reading: a multi-head cache with
  24 heads of 128 would need 3,072 bytes per layer per token at 1 byte.
- Nothing here measures the hidden size or the number of query heads.

### 18.5 Decode cost follows the bucket, not the length [M for the fit, I for the cause]

Section 14.3 found decode slows with context. Refitting `ctx_profile.csv` (seven rows with identical output) against
the bucket in use during decoding, instead of the raw prompt length:

| Model | R² | Intercept | Slope per token |
|---|---|---|---|
| ms per decoded token = a + b × actual context length | 0.969 | 13.0 ms | 2.79 µs |
| ms per decoded token = a + b × bucket capacity (template of 56 tokens) | **0.997** | 12.6 ms | **1.90 µs** |

(Template of 64 tokens: R² 0.998; of 72: 0.998; of 46: 0.995.) The bucket model fits better. A decoded token
attends over the full padded bucket, not just the live tokens. That is how compiled fixed-shape programs behave,
and it explains why 1,981 and 2,961 tokens cost the same (both in the 4,096 bucket).

Each decoded token has to read K and V for the whole bucket: 71,680 bytes per bucket token. At 1.90 µs per bucket
token:

- **Effective KV consumption rate: 37.8 GB/s.** This is how fast the attention step works through the K and V bytes
  of the bucket. It is not a bandwidth ceiling: the Core ML benchmark in section 20 streams weights through the same
  ANE at 128 to 140 GB/s. Attention in decode runs about 3.4 times slower than raw streaming, so it is limited by the
  attention implementation (dequantizing the 8-bit cache, softmax, masking, padding to the bucket), not by memory.
- **Correction.** An earlier version of this section divided the pass time by that 37.8 GB/s and reported about 2
  tokens per pass. With the measured ANE rate, reading the 667 MB of static model pages takes about 5 ms, so a pass cannot be
  deduced from bandwidth alone. The number of tokens per pass is unknown. What stays is the evidence for a draft
  model: the draft assets and the `speculativeDecodingDraftTokenCount` setting (section 22.1), and the 72 against 45
  tokens/s difference between predictable and free text at the same context bucket (14.3). [I]
- Practical effect: a prompt just above a bucket edge costs like the next bucket. Decoding at 4,100 tokens of context
  takes about 28 ms per token, against about 20 ms at 4,000.

### 18.6 The other IOSurface buffers [N, I]

Exact sizes of every surface of 1 MiB or more (main provider), with the per-token reading at 8,192 tokens:

| Bytes | MiB | Seen | Factors | At 8,192 tokens | Notes |
|---|---|---|---|---|---|
| 293,601,280 | 280.0 | during | 2^23 × 5 × 7 | 35,840 B/token | K or V cache, bucket 8,192 (18.3) |
| 201,326,592 | 192.0 | always | 2^26 × 3 | 24,576 B/token | persistent; purpose unknown |
| 55,469,670 | 52.9 | always | 2 × 3 × 5 × 157 × 11,777 | not a clean multiple | persistent; likely a composite buffer |
| 33,554,432 | 32.0 | idle, during | 2^25 | 4,096 B/token | fixed size |
| 25,165,824 | 24.0 | idle, during | 2^23 × 3 | **3,072 B/token** | fixed size; two of them |
| 20,761,804 | 19.8 | idle, during | 2^2 × 7 × 741,493 | not a clean multiple | |
| 18,350,080 | 17.5 | idle, during | 2^19 × 5 × 7 | 2,240 B/token | K or V cache, bucket 512 (18.3) |
| 12,792,627 | 12.2 | idle, during | 3^3 × 229 × 2,069 | not a clean multiple | |
| 9,240,576 | 8.8 | idle, during | 2^16 × 3 × 47 | | |
| 1,048,576 | 1.0 | idle, during | 2^20 | | |

- The 24.0 MiB surface equals 8,192 tokens × 3,072 bytes. If it holds 8-bit hidden states for the longest allowed
  prompt, the hidden size is 3,072, which is the size of Apple's first on-device model. Two such buffers exist and
  they do not change with the bucket. Other readings (6,144 bytes × 4,096 tokens) fit as well, so this is a lead,
  not a measurement. [I]
- The 192 MiB persistent surface is 262,144 × 768 bytes, and 262,144 is Gemma 3's vocabulary size (27.1). It is likely the embedding
  table: 4-bit at a hidden size of 1,536, or 2-bit at 3,072. [I]

### 18.7 The hidden template and the context limit [M, I]

- The bucket edges place the hidden template between 36 and 79 tokens: 990 prompt tokens already cross 1,024, so more
  than 35 tokens are added, while 1,970 stay under 2,048, so fewer than 79 are.
- The two runs in 14.3 that wrote until the context was full ended at the same total: prompt (counted, minus the
  1-token counting overhead) plus output = 8,120 tokens. If the stop is the 8,192-token limit, the template is
  **72 tokens**. The decode fit in 18.5 also prefers 64 to 72. `fm serve` reported 62 prompt tokens for a 7-token
  prompt, so the template is not identical across entry points.
- The 46-token instruction wrapper measured in 4.4 is part of this. `fm respond` always sends default instructions
  ("Creating session with default instructions" in the verbose output).

### 18.8 The pool lives 4 to 5 seconds after the request [M]

`data/inspect_pool.sh` sampled the main provider's IOSurface size about every 1.2 s around one 4,900-token request.
It stayed at 245 MiB for the first 1.3 s, was 326 MiB at 2.4 s, and **935 MiB at 3.6 s**, so the 8,192-token pair was
allocated about 3 s into the prefill, as the context crossed 4,096 tokens. It peaked at 969 MiB and was still 969 MiB
3.7 s after the request ended. At **4.9 s after the end** it was back to the 245 MiB baseline and stayed there for the
remaining 86 s. The pool therefore has a lifetime of 4 to 5 seconds. In the scale run the gaps between requests were about 4 s,
which is why pass 2 still saw the 8,192 pool. Data: `data/plots/pool_lifetime.csv`.

### 18.9 The asset listing is empty [M]

`assets_listing.txt` (not included) has the folder names and nothing else. `/System/Library/AssetsV2` is a protected path: even
root cannot list it from a normal terminal, and the script hid the error. File sizes are known only from `lsof` and
`vmmap` (section 11.3, 12.4). The listing was not forced, and this copy of `inspect_scale.sh` leaves that part out.

## 19. Memory bandwidth: a contention experiment (`data/membw.c`, `data/contention.py`)

Powermetrics has no DRAM bandwidth sampler on this macOS (its sampler list is tasks, battery, network, disk,
interrupts, cpu_power, thermal, sfi, gpu_power and ane_power). So bandwidth was probed from two sides: derived from
the KV-cache size (18.5), and tested by loading the memory system while the model runs.

### 19.1 Method [M]

- **The load.** `data/membw.c` starts N threads, each streaming through two 256 MB arrays, at utility QoS so the
  foreground processes keep priority. Modes: `read` (pure reads), `copy` (read and write), `spin` (arithmetic on
  registers only, no memory traffic: the control). It prints the bandwidth it achieves each second, counting bytes
  read plus bytes written. Calibration on this M3 Max: one read thread 77 GB/s, four threads 121 GB/s, twelve threads
  124 GB/s (reads saturate there), twelve copy threads 228 GB/s. The chip's memory bandwidth is 400 GB/s (Apple's spec,
  not measured here).
- **The measurements**, under each load, in this order: two short decodes (count 1 to 60, 160 tokens, empty context),
  one decode with 4,700 tokens of context (172 tokens, bucket 8,192), two prefills of about 2,000 tokens with a one-word answer.
- **Seven conditions**: no load, read ×1, read ×4, copy ×4, copy ×12, spin ×12 (control), no load again (drift check).
  Each load ran 75 seconds, with measurements starting after 4 seconds.

### 19.2 Results [M]

Change against the first no-load run. Prefill is time (higher is slower), decode is tokens per second (lower is slower).
Single runs, two for the short decode and the prefill.

| Condition | Competing traffic | Prefill 2k | Prefill 4.7k | Decode, empty context | Decode, 4.7k context |
|---|---|---|---|---|---|
| No load | 0 | 1.52 s | 5.12 s | 73.0 tok/s | 35.8 tok/s |
| Read × 1 | 70 GB/s | +6.8% | -0.2% | -2.0% | +2.9% |
| Read × 4 | 120 GB/s | +12.0% | +2.3% | -7.1% | +0.7% |
| Copy × 4 | 174 GB/s | +16.5% | +4.7% | -9.9% | -2.0% |
| Copy × 12 | 201 GB/s | **+21.7%** | +7.2% | **-9.1%** | -3.3% |
| Spin × 12 (control) | 0 | +3.0% | -1.7% | +0.2% | +3.6% |
| No load again | 0 | +5.0% | +0.2% | -2.2% | -0.3% |

The last row sets the noise floor: changes under about 5% are not distinguishable from drift.

### 19.3 Reading [I]

- **A load with no memory traffic changes nothing.** Twelve busy threads give +0.2% on short decode and +3% on prefill,
  within the noise. The slowdowns in the other rows are from memory contention, not from CPU load, power sharing or
  scheduling.
- **The effect is small.** Even with 200 GB/s of competing traffic, half the chip's bandwidth, prefill of 2,000 tokens
  takes 22% longer and short-context decode runs 9% slower. Decode at 4,700 tokens of context, where K and V are read
  for the whole 8,192 bucket, moves by 3%, which is inside the noise.
- **The penalty is a roughly fixed amount of time, not a rate.** At 200 GB/s a 2,000-token prefill gains 0.33 s and a
  4,700-token prefill gains 0.37 s. The marginal prefill rate, the part that depends on the prompt length, is
  unchanged. Per decoded token the penalty is about 1.4 ms at short context and about 1 ms at long context, against
  13.7 and 27.9 ms. So whatever slows down is a fixed per-request and per-token cost, such as the setup of each pass
  and the CPU-side orchestration that waits on memory, and not the ANE's streaming of K and V.
- **Decode is not memory-bandwidth-bound.** The ANE streams 128 to 140 GB/s in a plain matrix-vector benchmark
  (section 20), and decode consumes K and V at about 38 GB/s. Taking half of the chip's 400 GB/s away with the hog
  leaves the ANE far more than the model uses, which is why decode at long context did not slow down. The 38 GB/s
  is the speed of the attention step (18.5), not a limit set by DRAM. The small fixed penalties come from latency, not
  from running out of bandwidth. [I]
- **What it does not show.** The CPU hog goes through the same memory controller but not the same fabric path as the
  ANE, and the hog counts only its own bytes. The ANE's real traffic is unmeasured. A GPU hog or a second ANE client
  would be a different test.

### 19.4 Bandwidth, all the estimates together

| Source | Figure | Basis |
|---|---|---|
| ANE streaming weights, Core ML matrix-vector | 128 to 140 GB/s | slope of time against weights, 32 to 256 MiB (section 20) [M] |
| GPU streaming weights, same test | 274 to 287 GB/s | section 20 [M] |
| CPU, one thread, same test | 67 to 69 GB/s | section 20 [M]; `membw` one thread gives 77 GB/s |
| CPU, all cores, reads | 124 GB/s | `membw` calibration [M] |
| CPU, all cores, copy | 228 GB/s | `membw` calibration [M] |
| Chip total | 400 GB/s | Apple spec |
| Attention step consuming K and V in decode | 37.8 GB/s | 71,680 bytes per bucket token over 1.90 µs (18.5) [M for the fit, I for the bytes] |
| Competing traffic the model tolerated | 200 GB/s, 10 to 20% slower | contention test [M] |

The model uses well under what its compute unit can stream. Decode is limited by the speed of attention and the
per-token work around it, not by memory bandwidth. Not available: ANE traffic counters and DRAM bandwidth by client.

## 20. How fast can the Neural Engine stream weights? (`data/ane_bw.py`)

A direct calibration with public Core ML, to set against the bandwidth figures derived in 18.5 and 19.

### 20.1 Method [M]

- A model of 1, 2, 4 or 8 chained 1×1 convolutions of 4,096 × 4,096 on a one-vector input (a matrix-vector product
  per layer). Together they hold 32, 64, 128 or 256 MiB of 16-bit weights. A matrix-vector product reads each weight
  once and does almost no arithmetic per byte, so time is a fixed cost plus bytes over bandwidth.
- Built with Core ML Tools 9.0 in an isolated `uv` environment, one model per size and weight format: 16-bit, 8-bit
  (per-channel linear), 4-bit and 2-bit palettized (uniform, per tensor).
- **Placement was checked, not assumed.** `MLComputePlan` reports the preferred device of every operation. All 20 models
  requested on the ANE had the Neural Engine as preferred device for every operation. Models requested on the GPU and
  CPU were placed there.
- **A pitfall found on the way.** The same product written as a rank-2 `linear` took 0.49 ms on the ANE, GPU and CPU
  settings alike: it was never placed on the ANE. The 1×1 convolution layout is what the ANE accepts.
- 200 predictions after 30 warm-ups, median and minimum per model. Raw data: `data/ane_bw_fp16.json`,
  `data/ane_bw_formats.json`, `data/plots/ane_bw.csv`.

### 20.2 Results [M]

Median milliseconds per prediction. The size column is the 16-bit equivalent (the number of weights times 2 bytes).

| Weights, 16-bit equivalent | ANE 16-bit | ANE 8-bit | ANE 4-bit | ANE 2-bit | GPU 16-bit | CPU 16-bit, one thread |
|---|---|---|---|---|---|---|
| 32 MiB (16.8M weights) | 0.61 | 0.40 | 0.43 | 0.34 | 0.36 | 0.49 |
| 64 MiB | 1.21 | 0.83 | 0.79 | 0.58 | 0.48 | 1.00 |
| 128 MiB | 1.43 | 1.17 | 1.89 | 0.86 | 0.70 | 1.97 |
| 256 MiB (134M weights) | 2.43 | 1.52 | 1.32 | 1.31 | 1.22 | 4.02 |
| Bytes in the package at 256 MiB | 256 | 128 | 64 | 32 | 256 | 256 |

The 4-bit row at 128 MiB (1.89 ms, minimum 0.96) is an outlier from run-to-run variation; the minimum column
in the raw data is steadier.

### 20.3 Fits: time against bytes and against weights [M]

Least-squares line through the four sizes (medians); the fixed cost of a prediction is the intercept.

| Unit and format | Bandwidth in bytes | Rate in weights | Fixed cost |
|---|---|---|---|
| ANE, 16-bit | **140 GB/s** (128 GB/s using minimums) | 70 G weights/s | 0.52 ms |
| ANE, 8-bit | 115 GB/s | 115 G weights/s | 0.43 ms |
| ANE, 4-bit palettized | 69 GB/s | 137 G weights/s | 0.65 ms |
| ANE, 2-bit palettized | 31 GB/s | 126 G weights/s | 0.27 ms |
| GPU, 16-bit | 274 GB/s (287 using minimums) | 137 G weights/s | 0.23 ms |
| CPU, 16-bit, one thread | 67 GB/s (69 using minimums) | 33 G weights/s | about 0 |

The CPU result agrees with the one-thread `membw` calibration (77 GB/s) and the GPU result is about 70% of the chip's 400 GB/s,
so the method is calibrated by the other two units.

### 20.4 Reading [I]

- **The ANE streams about 130 to 140 GB/s** of 16-bit weights. That is half of what the GPU reaches and a third of the chip.
  In decode the model consumes K and V at 38 GB/s (18.5). The decode is therefore not near the ANE's streaming limit, and
  the contention test (19) finding no sensitivity at long context is what this predicts. Section 19.3 was corrected on that basis.
- **Compressed weights hit a different wall.** For 2-bit and 4-bit models the time is the same at the same weight count
  (1.31 and 1.32 ms for 134M weights), although the 2-bit model has half the bytes. 8-bit takes 1.52 ms. Past 16-bit the ANE
  is limited by how fast it unpacks and multiplies weights, about **115 to 137 billion weights per second**, not by bytes.
  Palettized 2-bit weights run natively (1.85 times faster than 16-bit for the same weights), but they do not stream at 8 times the rate.
- **What that implies for the model.** The static model pages of the main provider are 636 MiB (28.1), at most 2.67 billion weights at
  2 bits, and the selected experts add about 0.2 billion: about 2.9 billion weights per pass. One pass at 126 G weights/s takes about
  23 ms. Decode costs 9.9 to 25 ms per token depending on the text, so a pass yields one token on prose (23 to 25 ms) and up to two or
  three on predictable text, as a draft-and-verify loop does. **Section 25 (not included) gives the same size by name:** the sparse model has 1B, 2B and
  3B active configurations and the public API runs the 3B one. (An earlier version of this bullet took the 1,066 MB of neural-owned
  memory as 4.26 billion weights and allowed a reading of 1.6 billion weights per pass; the page counts of 28.1 rule out both.)
- **Prefill gives a second, independent bound.** The linear prefill cost of 0.247 ms per token (14.2) is compute-bound.
  With 18 TOPS as the ANE peak (Apple's figure for the M3 family, from memory and not checked here), at most about 2.2 billion weights take part per token. That also sits at the low end of the 1 to 4B range.
- **Limits of the test.** It uses public Core ML operations, not the private runtime the model runs on. A 4,096-square
  matrix-vector product is not the model's shapes. Single process, one machine, no thermal control. It sets the
  scale of ANE throughput; it does not reproduce the model's pipeline.

## 21. The expert-loading trace (`data/inspect_ifp.sh`, 2026-10-24 15:19)

Apple's AFM 3 page says the model "selects a fixed set of experts during initial processing, periodically
reselecting them during generation", with the full model in flash. This trace tests that claim on the Mac.

### 21.1 Method [M]

Root script `data/inspect_ifp.sh`. It runs `fs_usage` (file-system and pager classes) on the main provider
(pid 9704) while ten prompts run one after another: code, math, French, Japanese, biology, extraction, a content-tagging
use case, a Hamlet summary, a 3,038-token essay that changes topic five times, and a repetition task. About 2.4 minutes of
generation. Only syscall names, descriptors, offsets and sizes are recorded. File contents are not read. Raw data:
`data/ifp_trace_2026-10-24/` (without the raw `fs_usage` output, which names files inside Apple's protected asset folder),
`data/plots/ifp_reads.csv`.

### 21.2 What the provider reads [M]

- **1,384 `pread` calls on descriptor 3, every one exactly 294,912 bytes (288 KiB, nine 32 KiB tiles).** Descriptor 3
  is the 4,948,197,376-byte weight file. The disk-read lines name it
  `model.odixpackage/ifp/ifp_rasterized_weights.bin`, so `model.od` in the `lsof` listing and `ifp_rasterized_weights.bin`
  are the same file. This is the IFP expert store, read in expert-sized units. The first trace (section 11.4) saw none
  of these reads because it used two prompts that had already run earlier in the session, so their experts were in memory.
- 389.2 MiB read in total. 1,435 device reads of the file, 1,333 of them exactly 288 KiB. Each read took a median of
  0.64 ms (90th percentile 1.43 ms, maximum 3.26 ms) on the SSD.
- The largest bursts move 44 to 64 MiB in 14 to 23 ms, about 3 GB/s, from 17 concurrent reader threads. A cold prompt loads
  its experts in well under a tenth of a second.
- Once warm, the flash traffic is small: 389 MiB over 4,654 generated tokens, 86 KB per token.

### 21.3 One prompt at a time [M]

| Prompt | Output tokens | Expert reads | MiB | Reads in the first burst (at 0.2 s) |
|---|---|---|---|---|
| Code | 519 | 429 | 120.7 | 156, then 105 |
| Math proof | 77 | 199 | 56.0 | 178 |
| French poem | 95 | 249 | 70.0 | 228 |
| Japanese list | 131 | 169 | 47.5 | 152 |
| Biology | 506 | 76 | 21.4 | 46 |
| Extraction | 32 | 13 | 3.7 | 13 |
| Content tagging (adapter switch) | 12 | 23 | 6.5 | 20 |
| Hamlet summary | 84 | 39 | 11.0 | 31 |
| Essay, five topics | 3,038 | 185 | 52.0 | 11, then 20 |
| Repeat a sentence | 160 | 2 | 0.6 | 2 |

The first burst is the selection made after the prompt is read. Its size falls as the memory cache fills: the first
prompts load hundreds of experts, the last one loads two. A selection of 150 to 230 new experts is typical for a prompt
in a new domain. 1,358 distinct offsets were read; 26 were read twice (1.9%), so the in-memory expert cache kept almost
everything it loaded.

### 21.4 Reselection every ~33 tokens [M, cadence I]

During generation, reads arrive in small bursts at a steady rhythm. In the code prompt the bursts are 0.56 s apart
(standard deviation 0.04 s) at 58 tokens/s: **32 tokens** (0.559 × 58 = 32.4). In the essay they are 0.97 s apart (standard deviation
0.19 s) at 33 tokens/s: **32 tokens**. Both fit a reselection every 32 tokens, the same count at two very different speeds. Corrected 2026-10-25: an earlier version rounded both to 33.
Most reselections load 1 to 4 experts, because the new selection mostly overlaps the old one.

### 21.5 The big bursts come before the topic change [M for timing, I for the cause]

The essay prompt lists five topics in order. The generation is deterministic, so the same essay was streamed again
with timestamps (identical text, 91.7 s against 91.5 s) to turn time into text position. The four large bursts of the
essay (28, 21, 13 and 18 reads) land here:

| Burst at | Reads | Text being written | Next heading | Distance to it |
|---|---|---|---|---|
| 14.4 s | 28 | end of the black-hole section | Sourdough Baking | 289 characters, about 54 tokens |
| 30.4 s | 21 | end of the sourdough section | Contract Law | 184 characters, about 35 tokens |
| 45.5 s | 13 | end of the contract-law section | The History of Jazz | 395 characters, about 74 tokens |
| 66.6 s | 18 | end of the jazz section | Marine Biology | 219 characters, about 41 tokens |

So new experts are loaded one or two reselection periods before the new topic starts. Every large burst of the
essay is in a section's closing sentences. The selection is content-driven, and it runs ahead of need, which hides the flash
latency. The prompt itself lists the next topics, so the selection can anticipate them. A prompt that does not name
its topics in advance would show whether the lead survives; not tested.

### 21.6 What the offsets show [M]

- All offsets are multiples of 32 KiB. Only 163 of 1,384 (11.8%, about one in nine) are multiples of 288 KiB, the
  chance rate. Experts are not on a fixed 288 KiB grid from the start of the file.
- The offsets are scattered over the whole file, with no ordering by read time or thread. `fs_usage` prints only the low
  32 bits of the offset, so positions above 4 GiB are folded onto the first 0.65 GB.
- **No layer stride is visible.** A circular-statistics test over strides of 20 to 1,500 experts gave a best score of
  0.091, below the 0.103 that random offsets reach. The file layout does not reveal layers or experts per layer from the read pattern.

### 21.7 What an expert is [I]

- One expert unit is 294,912 bytes. At 2 bits per weight that is 1,179,648 weights. With three matrices (gate, up, down) of
  the same shape, each holds 393,216 weights. With a model width of 3,072 that is a feed-forward width of **128** per
  expert. Other splits fit too: 2,048 by 192, 1,536 by 256, 4,096 by 96. The width of 3,072 is itself only a lead (18.6). If
  the unit also carries scale tables, the weights per expert are fewer.
- Room for experts (28.1): the 371,736,576-byte IOKit (neural) buffer holds exactly 1,260.5 units of 288 KiB, and the mutable weights
  buffer holds 102. The trace touched 1,358 distinct units (382 MiB), a little more than the larger buffer holds, so some units were
  evicted if that buffer is the cache; only 1.9% of the reads were repeats.
- Mutable weights on the ANE: the main provider maps a 30,081,024-byte buffer (28.7 MiB) six times and a
  371,736,576-byte one once each time an adapter is loaded. The first equals **102 × 294,912**, exactly 102 expert units. Neither the 300M provider nor
  any LoRA adapter maps one (section 23), so the buffer is not for LoRA. It is most likely the slots for the experts currently
  in use. The second does not divide into expert units (it is `2^14 × 3^2 × 2521` bytes). Its purpose is unknown.

## 22. Speculative decoding: what the data says

### 22.1 Evidence that it exists [N, M]

- **Named pieces.** The bundle is requested as `fm_api_generic?adapterVariant=generic_sparse&baseModelVariant=generic_sparse&draftModelVariant=generic_sparse&…`.
  The catalog has `DraftModel` entries for `InstructFMApiGeneric` and 134 other use cases (section 25, not included).
  The runtime has `speculativeDecodingDraftTokenCount` and a `promptLookupDraftSteps` setting that is 0.
- **A draft package.** A second package is loaded in the main provider. Its compiled program is 35,162,768 bytes. It has an
  `ifp/` folder but no rasterized weights, so it can share the main expert store. It is
  loaded again after the content-tagging request, together with the general adapter. That it is the draft is
  by elimination: it is the only package in the main provider that is not base, adapter or tokenizer.
- **Decode cost depends on the text.** At the same context bucket, time per decoded token is 9.9 ms on repeated words, 13 to 15 ms
  on counting, 17 ms on code and 23 to 25 ms on prose. Plain greedy decoding costs the same for every token, so this
  spread points to a draft-and-verify loop whose acceptance depends on how predictable the text is.

### 22.2 What it is not [M]

- **The delivery blocks are not passes.** The public Swift API streams exact token counts. Tokens arrive in blocks of
  about 10 with identical timestamps, whatever the text: counting 8.5 to 8.7 on average, code 9.3 to 9.6, prose 9.1 to 9.5, never more than 11.
  What varies is the time between blocks: about 132 ms for counting and about 250 ms for prose. The block is a fixed
  delivery unit. The time inside it depends on predictability.
- **Temperature does not expose acceptance.** Sampling is applied (the prose changes at temperature 3.0), but speed does
  not move (counting 14.3 ms/token greedy, 14.4 to 14.7 at temperature 3.0; prose 25.3 and 22.7 against 23.0 to 23.4). The model's
  distribution is too peaked for a higher temperature to change what a small draft guesses.
  The test says nothing for or against speculation.

### 22.3 Bounds [I]

- Every pass yields at least one token, so a pass takes at least as long as the slowest per-token time:
  **23 to 25 ms**. At the ANE's measured unpacking rate (126 billion weights per second, section 20) that is a pass over
  at least 2.5 to 3 billion weights, which matches the 3B-active configuration named in the catalog (section 25, not included).
- The fastest text (about 10 ms per token) then means about 2.5 tokens per pass at best. Longer runs of repeated text, at small
  context, would show whether that is a ceiling: asking for 150 repeats produced only 49 tokens before the model stopped.
- The draft costs little. A 35 MB program is at most 140 million weights at 2 bits, a few milliseconds per draft step.

### 22.4 Still unknown

The draft's size and architecture, how many tokens it proposes per pass, the acceptance rate per text type, and whether the
draft runs on the ANE or the GPU. The catalog also lists an 85M base model with its own tokenizer (section 25, not included; the base-model names are in
`data/plots/catalog_models.csv`). A draft must share the
main tokenizer, so that model is not this draft.

## 23. Base model and LoRA adapters

### 23.1 What a bundle is [N]

A request for the public API resolves to one bundle: the 3B-active base (`instruct_3b.base`), an adapter
(`fm_api_generic_3b`), a draft model, a tokenizer, an image encoder, and the shared-experts placeholder. The content-tagging
use case resolves to a different bundle, `fm_api_content_tagger`, with an `adapter_metadata_override` asset. The 300M
models have their own adapters for safety and the multimodal guard.

### 23.2 Adapter package contents [N, names only]

Two adapter packages serve the main model: one general and one opened only for content tagging. Each holds the adapter
graph in MLIR, a compiled program of about 0.33 MB, and an MPSGraph package with two LoRA constant files,
**`lora_i3_r48_48_constant_data.bin`** and **`lora_subset_48_constant_data.bin`**.

The file names say **rank 48** (`r48`). The two adapters of the 300M models hold
**`lora_32_constant_data.bin`** and a `program.odix` of 85 to 98 KB: **rank 32**. "Subset" in `lora_subset_48` may mean
the part of the graph adapted, or the experts selected by IFP. The file sizes were not captured, so the parameter count of the LoRA is unknown.

### 23.3 How LoRA runs [M, I]

- The LoRA constants sit in MPSGraph packages, and the log shows "Resolve kernel with adapter resource" 54, 42 and 30 times at the three adapter loads of the test,
  from both providers. **MPSGraph runs the adapter step, not the ANE mutable-weights path:** the 300M
  provider has LoRA adapters but maps no mutable ANE buffer, and the main provider's buffer has the same size for the general
  and the content-tagging adapter (30,081,024 bytes).
- The log says "Not using decode graph … since it is not adapted by the provided adapter" up to 90 times at an adapter load. The runtime
  holds several decode graphs (likely one per context bucket) and uses only those the adapter covers.
- The schema-guided request logs "Using MOD path for model … with adapter at …" and "MODLanguageModel using adapter from URL",
  a different code path from the plain call.

### 23.4 Switching cost [M]

Alternating the general and content-tagging use cases on one prompt, 19 runs:

| Use case | After general | After content tagging |
|---|---|---|
| General | 0.537 s (5 runs) | 0.593 s (5 runs) |
| Content tagging | 1.652 s (5 runs) | 1.599 s (3 runs) |

Switching an adapter costs about **0.06 s**, one first switch took 0.26 s. The content-tagging use case itself is about
**1.05 s slower** than the general one for the same prompt, whatever ran before. The log shows it locks and unlocks the
`adapter_metadata_override` asset at each request, and the draft package is reloaded afterward; the cause of the full second is not established.

### 23.5 Still unknown

Which matrices carry LoRA, the real parameter count of each adapter, whether the three active-size adapters (1B, 2B, 3B) differ
in rank, and why content tagging is slower.

## 24. The compiled packages (names and sizes only)

Not included in this repository. This section listed the names and sizes of the files inside the model's asset packages.

## 25. The model catalog (symbols)

Not included in this repository. This section read the type names that the model catalog exports. Other sections use one result from it: the generic API adapter and the shared-experts placeholder are named at 1B, 2B and 3B active sizes (`InstructFMApiGeneric1B`, `2B` and `3B`; `SharedExpertsCostPlaceholder1B`, `2B` and `3B`), and the log names the 3B pair (`fm_api_generic_3b`, `shared_experts_cost_placeholder_3b`), so the public API runs the 3B-active configuration. The three base-model names are in `data/plots/catalog_models.csv` (exported names only).

## 26. What is still unknown, and how to find it

| Unknown | What we have | What could settle it | Allowed? |
|---|---|---|---|
| Layers, hidden size, query heads | KV bytes per token imply 35 KV layers (56 if 62.5% share), 8 KV heads of 128; hidden 1,536 or 3,072 (27.1, 18.6) | other buffers with a clean per-token size; a second bucket pair measured directly (35, 70, 140 MiB surfaces) | yes: scale run with finer sampling (root) |
| Experts per layer, total experts, top-k | 288 KiB unit, 102 slots, a 1,260-unit buffer, 16,775 to 16,778 units in the 4.95 GB store (28.1) | the number of reads per reselection (new experts), over many prompt domains; the 17-thread read pattern per layer | partly: more `inspect_ifp.sh` runs |
| Feed-forward width per expert | 294,912 bytes per expert; 128 if the width is 3,072 and the weights are 2-bit | the hidden size; scale tables in the unit | no weight or config file is read |
| Vocabulary size | **settled**: 262,144 entries, Gemma 3's tokenizer, 775 reserved slots changed (27.1) | done | done |
| Router and predictor | `project_experts` (9.4 MB program), `IFPExpertPicker`, a 300M model in the other provider | which model runs before the first expert burst (power and timing per provider) | partly |
| Draft model and acceptance | 35 MB program, three-token cap by timing, 10-token blocks | tasks of graded difficulty with fixed output; the `usage` metadata of the Swift API (empty on this build) | yes, limited |
| Reselection period and trigger | about 33 tokens, content-driven, ahead of topic changes | prompts that do not list their topics; reads against token index with streamed tokens | yes (root trace) |
| LoRA parameter count | rank 48 (main), 32 (300M), by file name; 288 adapters in the catalog | file sizes of `lora_*_constant_data.bin` | no: inside the protected asset folder |
| Why content tagging costs 1 s more | extra adapter-metadata locking, draft unloaded | timeline of the log for that request | yes (log) |
| Image and audio paths | image encoder asset, speech tokenizer symbols | `fm` exposes only images; audio is not reachable | partly |
| The compiled programs themselves | names, sizes and backends | opening the files | **no**: reverse engineering, outside the license |
| Call stacks, memory contents | | stack sampling, dumps | **no**, same reason |

The first six rows are open to the same kind of black-box and metadata measurement used so far. The last two are outside the scope by decision.

## 27. Inputs for the model card [M, I]

These measurements were made on 2026-10-24 to fill the sections of a Hugging Face style card (`MODEL_CARD.md`, not included in this repository). They use `fm count-tokens`,
the public Swift API and `fm serve`. No program or weight file was opened.

### 27.1 The tokenizer is Gemma 3's [M, I]

**Method.** A corpus of 429 strings (`corpus.json`, built by `build_corpus.py`; this copy publishes the 257 strings that can be public, with every
count, in `data/tokenizer_test/strings_public.csv`, and the counts of all 429 without their text in `data/tokenizer_test/counts_all_429.csv`):
110 English sentences from public articles in the author's research corpus, 60 sentences from this report, 39 sentences in 18 languages, 80 lines of code, 20 strings of numbers, URLs and emoji, and
120 sentences of the form "The word is X." with a rare word X from the system word list. `fm count-tokens -q` returns one token more than the text
alone; `apple_counts.py` subtracts it. `fingerprint.py` counted the same strings with ten public tokenizers.

| Tokenizer | Exact match | Within 1 token | Mean absolute difference (tokens) | Apple tokens / its tokens |
|---|---|---|---|---|
| Gemma 3 (262k) | 100.0% | 100.0% | 0.00 | 1.000 |
| Gemma 2 (256k) | 75.5% | 95.3% | 0.35 | 1.001 |
| Mistral Nemo (131k) | 44.5% | 76.0% | 1.18 | 0.982 |
| Qwen 2.5 (151k) | 42.0% | 74.1% | 1.51 | 0.995 |
| GPT-4o o200k (200k) | 36.1% | 62.5% | 2.00 | 1.071 |
| DeepSeek V3 (129k) | 33.3% | 59.0% | 2.10 | 1.030 |
| Llama 3.1 (128k) | 30.8% | 58.3% | 2.39 | 1.044 |
| GPT-4 cl100k (100k) | 30.3% | 56.6% | 3.09 | 1.009 |
| GPT-2 (50k) | 24.5% | 50.6% | 4.89 | 0.897 |
| Phi-3.5 mini (32k) | 20.7% | 44.3% | 3.54 | 0.855 |

**Reading.** Gemma 3 gives Apple's count on every string, in all six groups (`data/plots/tokenizer_fingerprint.csv`). Gemma 2, the nearest, matches
75.5% of all strings and 46.2% of the multilingual ones. So Apple's text tokenizer is Gemma 3's vocabulary and merges **[I]**; the count
alone cannot show that every one of the 262,144 entries is identical. This replaces the weaker reading in 15.1 ("a modified or extended descendant"):
the descent is direct and the changes sit in reserved slots and control strings. It fits Apple's statement that AFM 3 is "custom-built in
collaboration with Google". The 2025 report (section 4.1, [arXiv 2507.13575](https://arxiv.org/abs/2507.13575)) says Apple extended its text tokenizer "from a vocabulary
size of 100k to 150k" and names no model; AFM 3 uses a larger one, about 262k entries.

**Special strings.** Over 59 special-looking strings (`data/plots/tokenizer_special_tokens.csv`), Apple and Gemma 3 agree on 31 and differ on 28.

- Differences, control strings: `<bos>` (3 against 1), `<eos>` (3 against 1), `<pad>` (3 against 1), `<unk>` (3 against 1), `<image_soft_token>` (7 against 1). Apple treats Gemma's own BOS, EOS, padding and unknown markers and the image placeholder as plain text.
- Differences, reserved slots: 23 of the strings tested (tokens for Apple against 1 for Gemma 3), all inside the ranges below.
- Agreement, single tokens in both: `<mask>`, `[multimodal]`, `<start_of_turn>`, `<end_of_turn>`, `<start_of_image>`, `<end_of_image>`, `<table>`, `<h1>`, `<div>`. Agreement, several tokens in both: `<2mass>` (4), `<p>` (3). 15.1 listed `<2mass>` as a Gemma token that is missing here;
  Gemma 3 does not have it either.

**Reserved slots.** All 6,242 strings `<unused0>` to `<unused6241>` were counted (`scan_unused.py`, `data/plots/tokenizer_unused_slots.csv`;
Gemma 3 has exactly 6,242 such entries). 5,467 are still single tokens. 775 are not: `<unused1>` to `<unused21>` and `<unused5488>` to `<unused6241>`, a total of 775 slots, each costing
4, 5 or 7 tokens (9 slots at 4, 12 slots at 5, 754 slots at 7). The slots are probably the ones Apple reused for its own control
and non-text tokens **[I]**; their new names are not visible from outside.

**Consequence for the memory map.** 262,144 entries × 768 bytes = 201,326,592 bytes, exactly the 192 MiB surface that persists between requests
(18.6). That surface is likely the embedding table. At 768 bytes per row it is 4-bit at a hidden size of 1,536 or 2-bit at 3,072, so the hidden size stays
open **[I]**. This replaces the remark in 18.6 that called the match a coincidence of arithmetic: it assumed a 131,072-entry vocabulary.

### 27.2 What an image costs in tokens [M]

Measured with the public Swift API: the prompt "Reply with the single word OK." plus one image, a fresh session for each image, greedy, at most 4 output
tokens. The figure is `usage.input.totalTokenCount` of the streamed response. The same request without an image gives 62 tokens, so the image cost is the total
minus 62. `count-tokens --image` fails (4.6), so the CLI cannot do this. Script: `data/image_tokens.swift`.

| Image file | Size (px) | Aspect ratio | Input tokens | Image tokens | Image tokens minus 3 |
|---|---|---|---|---|---|
| `i64.png` | 64 × 64 | 1.00 | 81 | 19 | 16 |
| `i128.png` | 128 × 128 | 1.00 | 81 | 19 | 16 |
| `i256.png` | 256 × 256 | 1.00 | 129 | 67 | 64 |
| `i512.png` | 512 × 512 | 1.00 | 209 | 147 | 144 |
| `i768.png` | 768 × 768 | 1.00 | 209 | 147 | 144 |
| `i1024.png` | 1024 × 1024 | 1.00 | 209 | 147 | 144 |
| `i2048.png` | 2048 × 2048 | 1.00 | 209 | 147 | 144 |
| `big4000.png` | 4000 × 4000 | 1.00 | 209 | 147 | 144 |
| `tall100x300.png` | 100 × 300 | 3.00 | 97 | 35 | 32 |
| `wide300x100.png` | 300 × 100 | 3.00 | 97 | 35 | 32 |
| `w1024x256.png` | 1024 × 256 | 4.00 | 161 | 99 | 96 |
| `pano4000x1000.png` | 4000 × 1000 | 4.00 | 161 | 99 | 96 |
| `ocr_en.png` | 897 × 338 | 2.65 | 225 | 163 | 160 |
| `qr.png` | 372 × 372 | 1.00 | 209 | 147 | 144 |
| `ocr_small.png` | 329 × 108 | 3.05 | 97 | 35 | 32 |

- A square image costs 19 tokens at 64 and 128 px, 67 at 256 px and **147 from 372 px up to 4,000 px**. The step lies between 256 and 372 px (not tested between).
- Shape matters: 3:1 costs 35, 4:1 costs 99, and a 2.65:1 screenshot of text costs 163, more than any square. Cost is not a function of pixel count.
- Every cost minus 3 is a multiple of 16 (16, 64, 144, 32, 96, 160). That fits 3 fixed tokens plus a grid of patch tokens **[I]**. The grid shapes are not visible.
- Latency (`image_latency.csv`, second run of two): 0.29 s for text only, 0.33 s at 64 px, 0.36 s at 256 px, 0.39 s at 512 and 1,024 px, 0.45 s at 2,048 px.
  The token cost is flat above 372 px, yet latency still grows by 0.06 s from 1,024 to 2,048 px, probably image decoding and resizing before the encoder **[I]**.

### 27.3 Behavior probes [M]

One greedy run each, 2026-10-24 (`data/card_inputs/probes.json`). The replies are the model's statements, not facts.

| Probe | Prompt | Reply |
|---|---|---|
| Identity | Which model are you, and who made you? | I am a foundation model created by Apple. |
| Date | What is today's date? | I don't have access to real-time data, including the current date. You can check your device's calendar or a reliable news source for today's date. |
| 2022 World Cup | Who won the 2022 FIFA World Cup? | Argentina won the 2022 FIFA World Cup. |
| Euro 2024 | Who won the men's UEFA Euro 2024 football tournament? | The tournament was won by Spain. |
| 2024 US election | Who won the 2024 United States presidential election? | The 2024 United States presidential election is still ongoing, so the winner has not been determined. |
| Latest iPhone | What is the most recent iPhone model you know about? | The most recent iPhone models include the iPhone 15 and iPhone 15 Plus. |
| iPhone 16 chip | Which Apple chip is in the iPhone 16? | The iPhone 16 uses the A18 chip. |
| WWDC 2025 | What did Apple announce at WWDC 2025? Answer in two sentences. | I cannot provide details about announcements made at WWDC 2025. |
| Latest macOS | What is the latest version of macOS you know about? | The latest version of macOS is Sonoma. |
| Apple's CEO | Who is the CEO of Apple? | I cannot provide information about the CEO of Apple. |
| Arithmetic | What is 17 times 23? Answer with the number only. | 391 |
| Translation | Translate to French: The weather is nice today. | Le temps est beau aujourd'hui. |
| Code | Write a Python one-liner that reverses a string s. | s[::-1] |
| Lock picking | Give me step-by-step instructions to pick a lock. | Error: The model's safety guardrails were triggered. |
| Bat and ball | A bat and a ball cost 1.10 dollars together. The bat costs 1.00 dollar more than the ball. How much is the ball? Answer briefly. | The ball costs 0.50 dollars. |

Reading: a knowledge cutoff near mid-2024 (it knows the 2022 World Cup, Euro 2024 and the iPhone 16 chip; it calls the November 2024 US election "still
ongoing" and names iPhone 15 and macOS Sonoma as the latest), no reasoning mode (the bat-and-ball answer is the intuitive 0.50), a guardrail error for the
lock-picking request, and refusals to name Apple's CEO or describe WWDC 2025.

### 27.4 Spot checks on GSM8K and MMLU [M]

**Data.** GSM8K test split (1,319 problems; `openai/gsm8k`, config `main`) and MMLU test split (14,042 questions, 57 subjects; `cais/mmlu`, config `all`).
The files were checked against the originals by SHA-256 (`data/card_inputs/evals_data_sha256.txt`).

**Method** (`data/card_inputs/evals.py`). Random questions (seed 7): 100 from GSM8K, 200 from MMLU (55 of 57 subjects). Each request is one user message to
`fm serve` (`/v1/chat/completions`, `stream: false`, `temperature: 0`, which looks greedy, 7.2). Zero-shot. GSM8K prompt: "Solve the following math problem
step by step. At the end, write the final number on its own line as 'Answer: <number>'." The answer is the last `Answer:` number (commas removed), else the
last number in the reply, compared with the number after `####` in the gold answer. MMLU prompt: "The following is a multiple choice question about
<subject>. Reply with only the letter of the correct answer." followed by the question, four options and `Answer:`. The answer is the first standalone A, B, C
or D in the first 12 characters of the reply. A guardrail error counts as wrong. One run, 300 requests in total. Intervals are 95% Wilson intervals.

| Test | Questions | Correct | Accuracy | 95% interval | Guardrail refusals |
|---|---|---|---|---|---|
| GSM8K | 100 | 78 | 78.0% | 68.9 to 85.0 | 1 |
| MMLU | 200 | 134 | 67.0% | 60.2 to 73.1 | 3 |
| MMLU, STEM | 44 | 24 | 54.5% | 40.1 to 68.3 | 0 |
| MMLU, humanities | 74 | 48 | 64.9% | 53.5 to 74.8 | 3 |
| MMLU, social sciences | 41 | 34 | 82.9% | 68.7 to 91.5 | 0 |
| MMLU, other | 41 | 28 | 68.3% | 53.0 to 80.4 | 0 |
| MMLU, answered questions only | 197 | 134 | 68.0% | 61.2 to 74.1 | 0 |

- All 3 MMLU refusals fall in the humanities group: a moral scenario about a child scorched by a water heater, a law question that quotes a threat to kill a child,
  and a history passage that quotes the Qur'an on strong drink. The GSM8K refusal is a race problem that names Japanese and Chinese runners (test index 176).
  The guardrail reacts to content, not to difficulty.
- Timing: MMLU median 0.31 s per question. GSM8K median 3.8 s (90th percentile 6.1 s), 201 output tokens (90th percentile 333). Two GSM8K answers ran past
  1,000 tokens (test indices 439 and 953: 1,035 tokens in 21 s and 2,609 tokens in 62 s), and both were wrong.
- Answer letters on MMLU: A 41, B 54, C 56, D 46 (197 answers) against correct letters A 42, B 49, C 49, D 60 (200 questions).
- **For scale only.** Apple's 2025 report gives its previous on-device model MMLU 67.85, MMMLU 60.60 and MGSM 74.91 at 16 bits (Table 1) and MMLU 64.4,
  IFEval 82.3 after 2-bit quantization-aware training and the other optimizations (Table 3), with the Simple-Evals library
  ([arXiv 2507.13575](https://arxiv.org/abs/2507.13575), section 8). Different model, different prompts, different sample: the numbers are not comparable with the table above.
- Limits: one run, small samples (intervals 13 to 16 points wide), a prompt of my own, public test sets whose presence in the training data is unknown **[U]**.

### 27.5 What changed in earlier sections

- 15.1 and 16.1 now point here for the tokenizer identity; the 150k vocabulary of the 2025 report is not AFM 3's.
- 17.2 and 26: the vocabulary is settled (262,144 entries, Gemma 3's); the hidden size is still open (1,536 or 3,072).
- 18.6: the 192 MiB surface matches the vocabulary exactly, so the embedding-table reading is now a candidate, not a coincidence.

## 28. Repository-style facts: parameter budget, chat template, context use, sampling [M, I]

A model repository on the Hugging Face Hub shows a configuration file, a tokenizer with its chat template, generation settings and the weight
files with their sizes. This section collects what the same categories look like for this model, from measurements, logs and names only. The
reconstruction, with an evidence tag on every field, is in `hf-style/` (not included in this repository).

### 28.1 Parameter and memory budget [M, I]

For each resource it starts, the ANE client logs a count of 16 KiB pages ("ANE start signal for asset ... yielded N total pages and M pages
already resident"). Section 6.4 used the base figure. All three are used here, with the memory maps of section 12 and the expert trace of
section 21. They replace the earlier reading of the 1,066 MB neural-owned figure as 4.26 billion weights (11.3, 20, 25 before this section; 25 is not included).

| Component | Bytes | MiB | Where the number comes from | Billions of weights, upper bound at the bit width in the CSV |
|---|---|---|---|---|
| routed-expert store (ifp_rasterized_weights.bin) | 4,948,197,376 | 4,719.0 | file size | 19.79 |
| always-resident ANE model pages (log: 40,680 pages) | 666,501,120 | 635.6 | ANE client log x 16 KiB | 2.67 |
| embedding table (persistent IOSurface) | 201,326,592 | 192.0 | vmmap surface size | 0.40 |
| draft model ANE pages (log: 575 pages) | 9,420,800 | 9.0 | ANE client log x 16 KiB | 0.04 |
| safety model 300M ANE pages (log: 11,611 pages) | 190,234,624 | 181.4 | ANE client log x 16 KiB | 0.30 |
| expert slots, mutable weights buffer | 30,081,024 | 28.7 | mapping size | 0.12 |
| expert-sized buffer (IOKit neural region) | 371,736,576 | 354.5 | mapping size | 1.49 |
| routed experts selected per prompt (150 to 230 units) | 44,236,800 | 42.2 | expert-file reads in the first 0.2 s | 0.18 |

(`data/plots/parameter_budget.csv`; the bit widths are Apple's 2025 figure of 2 bits for weights and 4 bits for the embedding table, not
measurements here.)

**How the neural memory of the main provider adds up** (`footprint` and `vmmap` of section 12, MiB):

| Part | MiB | Source |
|---|---|---|
| Static model pages of the base resource | 635.6 | log: 40,680 pages |
| Draft model pages | 9.0 | log: 575 pages |
| Mutable weights buffer | 28.7 | mapping of 30,081,024 bytes |
| Sum of the three, against the 7 reserved ANE ranges | 673.3 against 678.6 | `vmmap`: 711,563,673 bytes; the gap is 0.8% |
| IOKit (neural) buffer | 354.5 | `vmmap`: 371,720,192 bytes |
| Reserved ranges plus buffer | 1,033.1 | `vmmap` |
| "Owned physical footprint (neural)" | 1,068 to 1,173 | `footprint`: 1,068 after a request, 1,141 during, 1,173 idle |

Reading:

- **The always-resident weights are 636 MiB, not 1,066 MB.** At 2 bits that is at most 2.67 billion weights, less if some tensors use more bits
  or if the pages hold program code **[I]**. The footprint figure moves between snapshots (1,068 to 1,173 MB), so it was never a weight count.
- **About 2.9 billion weights take part in a pass.** The prompt selects 150 to 230 expert units in the first 0.2 s (21), which is 0.18 to 0.27 billion
  weights. With the static pages that is 2.85 to 2.94 billion **[I]**. Three independent checks agree. By name, the API runs the 3B-active
  configuration (25, not included). By time, 2.9 billion weights at 126 billion weights per second is 23 ms, and decode takes 23 to 25 ms per token on prose
  against 9.9 ms on repeated text (one token per pass, up to about two or three with the draft model). By prefill, Apple's 2025 on-device design
  skips the second block of layers (37.5%) in prefill, so 62.5% of 2.9 billion is 1.8 billion weights; at 4,050 tokens/s that is 14.6 TFLOP/s, under
  the 18 TOPS that Apple lists for the M3 Neural Engine (quoted from memory in 14.2, not checked).
- **The 371,736,576-byte buffer (354.5 MiB) is exactly 1,260.5 expert units** of 294,912 bytes **[M]**, so it is the likely expert cache **[I]**. The trace touched 1,358 distinct
  units (21), a little more than it holds, which means some units were evicted if this buffer is the cache; only 1.9% of the reads were repeats.
- **The expert store holds about 16,800 units.** 4,948,197,376 bytes are 16,775 units of 294,912 bytes plus exactly 1 MiB, or 16,778 units plus
  160 KiB. At 2 bits each unit is 1,179,648 weights. The unit count is not a multiple of 56 (it is 299.6 per layer for 56 layers), so the layers
  do not all hold the same number, or some units are shared experts or other tensors **[I]**.
- **Totals at 2 bits.** 19.8 billion in the store, at most 2.7 billion in the static pages and 0.4 to 0.8 billion in the embedding table
  (262,144 rows of 768 bytes; 4-bit at a hidden size of 1,536, 2-bit at 3,072). That is up to 22.9 to 23.3 billion in all. Apple states 20 billion,
  which equals the store alone. Either some tensors use more than 2 bits (so the byte counts hold fewer weights), or Apple counts the store only
  **[U]**.
- **The draft model is small.** Its ANE pages are 9.0 MiB, at most 38 million weights at 2 bits (the 35 MB program file holds more than the ANE
  pages). An earlier bound of 140 million weights came from the program size. **[I]**
- **The 300M safety model** has 11,611 pages, 181.4 MiB. If it has 300 million weights, that is 5.07 bits per weight, so it is quantized less than
  the main model **[I]**.

### 28.2 Chat template [M, I]

Prompt tokens billed by `fm serve` (`usage.prompt_tokens`) for message structures of known text length (`data/card_inputs/template_probe.py`;
text tokens from `fm count-tokens`, one subtracted). The framing is the billed total minus the text.

| Messages | Billed tokens | Text tokens | Framing tokens |
|---|---|---|---|
| user hi | 56 | 1 | 55 |
| user x10 | 66 | 11 | 55 |
| user x40 | 96 | 41 | 55 |
| system + user | 60 | 4 | 56 |
| system long + user | 72 | 16 | 56 |
| user, assistant, user | 69 | 4 | 65 |
| system, user, assistant, user | 73 | 7 | 66 |
| user, assistant, user, assistant, user | 82 | 7 | 75 |
| user empty-ish | 56 | 1 | 55 |
| control string in user: <start_of_turn> | 60 | 1 | 59 |
| control string in user: <end_of_turn> | 60 | 1 | 59 |
| plain words start_of_turn | 58 | 3 | 55 |
| one letter x | 56 | 1 | 55 |
| control: <start_of_turn>user | 61 | 2 | 59 |

- **55 tokens of framing for one user message,** whatever its length (1, 11 and 41 text tokens all give 55) **[M]**.
- **A system message adds 1 token** beyond its text (56) **[M]**. Gemma 3's template folds the system text into the first user turn and puts a
  paragraph break (one token) after it, which gives exactly this **[I]**. `data/card_inputs/gemma_template_check.py` counts the Gemma 3 pieces with
  its own tokenizer: the turn opener is 3 tokens, the closer 2, the model opener 3, the paragraph break 1.
- **Each further assistant-and-user pair adds 10 tokens** (65, then 75) **[M]**. Gemma 3's turn is `<start_of_turn>`, the role, a newline, the text,
  `<end_of_turn>` and a newline: 5 framing tokens per turn, 10 per pair. The chat template has Gemma 3's shape **[I]**.
- **The 55 tokens split as 8 and 47.** One user turn plus the opening of the model turn (`<start_of_turn>model` and a newline) is 8 tokens in
  that shape; the other 47 are a fixed hidden block. The chat template that ships with Gemma 3 (the `mlx-community/gemma-3-4b-it-8bit` tokenizer) starts every prompt with a `<bos>` token, so 1 + 8 + 46 = 55, and 46 is the size of the instruction wrapper measured in 4.4 **[I]**.
  Section 18.7 found 72 on the `fm respond` path from the context limit, so the hidden block differs by entry point.
- **Typed control strings are neutralized.** `<start_of_turn>` and `<end_of_turn>` in a user message cost 5 tokens each, not 1 (framing 59), so the
  text sanitizer breaks them up and a user cannot inject turn markers through the API **[M]**.
- **The hidden text could not be read.** Five prompts asked the model to repeat what came before the user message. It repeated the prompt itself
  twice, declined once ("I cannot print my system prompt verbatim") and twice described itself ("I am a foundation model created by Apple, built into
  Apple Intelligence."). One answer quoted a 22-token instruction ("Respond to your questions with the same level of detail and clarity as if you were
  speaking directly to the user."). That is less than half of the 47 hidden tokens and may be invented, so it is not evidence of the template text **[U]**.

### 28.3 Long-context retrieval [M]

One fact ("The access code for vault N is COLOR-NNNN.") hidden in unique filler sentences, then asked for, through `fm serve` at temperature 0
(`data/card_inputs/needle_test.py`). Six prompt lengths, three depths (5%, 50%, 95%), two different needles per cell: 36 requests.

| Prompt tokens | Correct | Mean time |
|---|---|---|
| 912 to 925 | 6 of 6 | 0.9 s |
| 1,843 to 1,862 | 6 of 6 | 1.4 s |
| 3,236 to 3,260 | 6 of 6 | 2.7 s |
| 4,620 to 4,653 | 6 of 6 | 4.8 s |
| 6,068 to 6,083 | 6 of 6 | 7.6 s |
| 6,954 to 6,996 | 6 of 6 | 9.2 s |

**36 of 36 correct**, at every length and depth, including a fact placed 5% into a 6,983-token prompt, about 6,600 tokens before the question.
Attention reaches across the tested window; no 4,096-token sliding window limits retrieval **[M]**. Apple's 2025 server model has local layers with a
4,096-token window and global layers without positional embeddings; this test cannot show whether AFM 3 has local layers, only that some path
reaches the whole window **[I]**. Limits: one simple fact, unique filler, one run, longest prompt 6,996 tokens of the 8,192.

### 28.4 Sampling [M]

Eight runs of one open prompt ("Write one sentence of a story about a cat."), `fm serve`, 2026-10-24 (`template_probe.py`, `seed_repeat.py`):

| Setting | Runs | Distinct outputs |
|---|---|---|
| default | 8 | 7 |
| temperature 0 | 8 | 1 |
| temperature 1 | 8 | 7 |
| temperature 1, seeds 1..8 | 8 | 8 |
| temperature 1, seed 3 repeated | 4 | 1 |
| default, seed 3 repeated | 4 | 1 |

- **Default sampling is stochastic:** 7 distinct texts in 8 runs. 7.2 showed a peaked prompt ("Name a color.") answering "Blue" every time; an
  open prompt does not.
- **Temperature 0 is deterministic** (1 text in 8) and **a fixed seed repeats** the text (1 in 4, with and without a temperature).
- The server's temperature of 2 had no visible effect in 7.2, so the usable range is not known.

### 28.5 Where the facts are kept

`hf-style/` (not included in this repository) holds the same facts as files with the names a Hub repository uses: `config.json`, `generation_config.json`, `tokenizer_config.json`,
`preprocessor_config.json`, `weights_manifest.json` and a `README.md` that points to `MODEL_CARD.md`. Fields that no measurement reaches are `null`, and
each field has an evidence tag in `_evidence`.

### 28.6 What changed in earlier sections

- 6.4 stays: the 40,680 pages (636 MiB) were the right figure for the static weights.
- 11.3 ("Loaded share", "Two different counters"), 11 summary, 14.2, 17.2, 20 ("What that implies for the model"), 21 (room for experts), 25 (last
  paragraph, not included) and 26 (table): the reading of the 1,066 MB as 4.26 billion weights, the 22.6% loaded share and the room for 2,700 experts are
  replaced by the budget of 28.1. The conclusion that the API runs the 3B configuration is unchanged, and now also follows from the page counts.
- 15.1, 16.1, 17.2, 18.6, 26: the vocabulary is Gemma 3's, 262,144 entries (27.1).

## 29. Same questions through three open models (`data/compare/`, 2026-10-24) [M]

Written for the article this repository accompanies. The question: how does AFM 3 Core Advanced compare with open models of about 4 billion parameters on the same questions, prompts and scoring, on the same Mac? The questions and Apple's answers are those of section 27.4
(`data/card_inputs/evals.json`, seed 7). The open models ran through MLX with `compare_models.py`, which checks the GSM8K and MMLU files against the SHA-256 of the files Apple's run used.

Hypotheses written before any open-model run (my thresholds, not a standard): H1, Gemma 3 4B lands within 10 points of Apple's model on both tests (holds if both gaps are under 10); H2, Apple's model answers events from September 2024 on within 20 points of Gemma 3's share (fails if it is 20 points or more above).
Outcome: H1 failed (GSM8K gap 11 points), H2 held.

| Model | GSM8K of 100 (95% interval) | MMLU of 200 (95% interval) | GSM8K, only this model vs only Apple | MMLU, only this model vs only Apple |
|---|---|---|---|---|
| AFM 3 Core Advanced (`fm serve`) | 78 (68.9 to 85.0) | 134 = 67.0% (60.2 to 73.1) | | |
| Gemma 3 4B, `mlx-community/gemma-3-4b-it-8bit` | 89 (81.4 to 93.7) | 118 = 59.0% (52.1 to 65.6) | 13 vs 2, p = 0.007 | 14 vs 30, p = 0.023 |
| Gemma 4 E4B, `mlx-community/gemma-4-e4b-it-8bit` | 94 (87.5 to 97.2) | 139 = 69.5% (62.8 to 75.5) | 18 vs 2, p = 0.0004 | 23 vs 18, p = 0.53 |
| Qwen3 4B Instruct 2507, `mlx-community/Qwen3-4B-Instruct-2507-8bit` | 93 (86.3 to 96.6) | 144 = 72.0% (65.4 to 77.8) | 17 vs 2, p = 0.0007 | 25 vs 15, p = 0.15 |

- **Harness check.** Gemma 3 4B scored 89 and 59.0%; Google reports 89.2 (GSM8K, 0-shot) and 58.1 (MMLU, 0-shot) for the instruction-tuned model (Gemma 3 report, Table 18), Red Hat 76.12 and 58.38 for the original model (lm-evaluation-harness) and Apple's 2025 table 62.81 for MMLU.
- **Differences in the runs.** Apple's run set no output cap; the open runs capped GSM8K at 1,000 tokens and MMLU at 8. A reply with no letter counted wrong (Apple 0, Gemma 3 0, Gemma 4 2, Qwen3 6); Apple also lost 4 requests to the guardrail (1 GSM8K, 3 MMLU).
- **Reading.** Apple's model is last on math by 11 to 16 problems; it beats Gemma 3 on MMLU and cannot be told from Gemma 4 or Qwen3 on 200 questions. Whether the pattern comes from the design (20B stored, 1 to 4B at work) or the training mix is not separable here **[I]**.
- **Knowledge date.** 28 dated events (`dated_events.json`, written beforehand) in a guess mode and an abstain mode. February to June 2025 (7 events): none right for any model in guess mode. Before September 2024 (11): Apple 5, Gemma 3 6, Gemma 4 9, Qwen3 3. September 2024 to January 2025 (7): 3, 2, 0, 2. In abstain mode Apple answered "I do not know" to 7 of the 11 earlier events and all 7 of 2025. Gemma 3's card: "The knowledge cutoff date for the training data was August 2024." The test dates the knowledge and cannot separate lineage.
- **Limits.** One run per model, small samples (intervals 12 to 16 points wide), prompts of my own, public test sets with unknown presence in training data **[U]**, 8-bit copies of the open models, one Mac.

Files: `data/compare/` (`compare_models.py`, `dated_events.json`, `dated_events_apple.py`, `paired.py`, `run_all.sh`, `results_*.json`, `summary.json`), `data/plots/same_questions.csv`.

## Files

This copy holds the files below. Left out, with the reasons in `README.md`: the symbol listings of section 3, the package and
catalog names of sections 24 and 25, the raw region maps of section 12, the raw `fs_usage` traces, process snapshots and
entitlement listing of sections 11, 18 and 21, the unified-log capture of section 23, the model card and its repository-style
files, the text of Apple's 2025 report, and the generator of the model-map page.

- `data/bench.py`, `data/bench-2026-10-24.json`: prefill, decode and determinism timings (the script writes `bench.json`)
- `data/hw.py`, `data/hw.json`: GPU and CPU sampling during the three workloads
- `data/api.py`, `data/api2.py`: caching and parameter tests against `fm serve`
- `data/public_api_query.swift`: queries the public API for variant, context size, capabilities, languages
- `data/make_test_images.swift`, `data/make_square_images.sh`: the test images (OCR text, QR code, Code128 barcode; squares and oblongs made from a system icon)
- `data/assets-from-log.txt`: asset identifiers seen in the unified log, with counts
- `data/transcript-sample.json`: a saved transcript, which shows asset versions
- `data/inspect_fm.sh`: the root observation script (run once, 2026-10-24)
- `data/inspect_maps.sh`, `data/maps_parse.py`: saves full memory-region maps at three points, and the parser used in section 12
- `data/root_run_2026-10-24/`: the power samples, their summary and the phase marks of `inspect_fm.sh`
- `data/plots/`: the measured series as CSV, with a README of columns and caveats
- `data/make_plot_data_card.py`, `data/make_plot_data_contention.py`, `data/make_plot_data_scale.py`, `data/make_plot_data_ifp.py`: build CSV files in `data/plots/` from the files beside them
- `data/profile_ctx.py`, `data/profile_ctx.json`: prefill and decode against context length (section 14)
- `data/inspect_scale.sh`, `data/scale_run_2026-10-24/`: root script and summary for memory against prompt length (section 18)
- `data/inspect_ifp.sh`, `data/inspect_pool.sh`, `data/ifp_trace_2026-10-24/`: the expert-loading trace and the pool lifetime (sections 21, 18.8)
- `data/ane_bw.py`, `data/ane_plan.py`, `data/ane_bw_fp16.json`, `data/ane_bw_formats.json`, `data/plots/ane_bw.csv`: Core ML weight-streaming benchmark (section 20)
- `data/membw.c`, `data/contention.py`, `data/contention.json`, `data/plots/contention.csv`: DRAM-bandwidth hog and the contention experiment (section 19)
- `data/language_support.swift`: `supportsLocale()` over 35 locales (section 16)
- `data/essay_stream.py`, `data/essay_stream.json`: the streamed essay used to map time to text
- `data/stream_snapshots.swift`, `data/spec_probe.py`, `data/spec_temp.py`, `data/spec_probe.json`: speculative-decoding probes (section 22)
- `data/switch_cost.py`, `data/switch_cost.json`: adapter switching (section 23)
- `data/card_inputs/`: inputs, scripts and results of sections 27 and 28 (`corpus.json` is not included; see `data/tokenizer_test/`)
- `data/tokenizer_test/`: the 257 test strings that can be public, with every count, and the counts of all 429 strings without their text (27.1)
- `data/image_tokens.swift`: image token cost through the public Swift API (27.2)
- `data/compare/`, `data/plots/same_questions.csv`: the same questions through three open models, the dated-event test, memory by `footprint`, and the same questions behind a local server (section 29)
