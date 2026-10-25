# Findings

One folder per finding, numbered in the order of the article. Items 01 to 09 are in the article; 10 to 16 are in this repository only.
Each README has four parts: Hypothesis (written before the test where one was; otherwise the question, marked as such), Experiment (method, commands, files), Results, and Conclusion (with what the finding does not show).

| Item | Finding | In the article | Basis |
|---|---|---|---|
| [01](01-model-card/README.md) | The model card | yes | Mixed; each line of the card carries its own label |
| [02](02-expert-reads/README.md) | Expert reads from flash | yes | Measured (timing, sizes); inferred (that the blocks are experts) |
| [03](03-loaded-pages-and-bit-width/README.md) | Loaded pages and the bit-width arithmetic | yes | Measured (page counts); inferred (bits per weight) |
| [04](04-memory/README.md) | Memory at the same moments | yes | Measured |
| [05](05-power-and-energy/README.md) | Power and energy per problem | yes | Measured |
| [06](06-safety-process/README.md) | The safety models' process | yes | Measured (memory, refusals); Apple says (the guardrails) |
| [07](07-tokenizer-and-google-endpoint/README.md) | Tokenizer, Google's endpoint and the six descriptions | yes | Measured |
| [08](08-chat-framing-and-special-tokens/README.md) | Chat framing and special tokens | yes | Measured |
| [09](09-same-questions/README.md) | Same questions, same Mac | yes | Measured |
| [10](10-speed-and-time-to-first-token/README.md) | Speed and time to first token | no | Measured |
| [11](11-fm-serve/README.md) | How `fm serve` behaves | no | Measured |
| [12](12-context-window/README.md) | The context window | no | Measured; Apple says (8,192) |
| [13](13-dated-events/README.md) | Dated events | no | Measured |
| [14](14-memory-contention/README.md) | Memory-bandwidth contention | no | Measured |
| [15](15-retrieval/README.md) | Finding one fact in a long prompt | no | Measured |
| [16](16-attention-cache-shape/README.md) | The attention cache shape | no | Measured (sizes); inferred (shape) |
