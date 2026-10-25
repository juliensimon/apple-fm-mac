# Gemma 3's chat-template pieces counted with its own tokenizer, to set beside the framing that `fm serve` bills (REPORT 28.2).
# Run: uv run --with tokenizers python data/card_inputs/gemma_template_check.py
from tokenizers import Tokenizer
t = Tokenizer.from_pretrained("unsloth/gemma-3-4b-it")
n = lambda s: len(t.encode(s, add_special_tokens=False).ids)
parts = {"<start_of_turn>user\\n": "<start_of_turn>user\n", "<end_of_turn>\\n": "<end_of_turn>\n", "<start_of_turn>model\\n": "<start_of_turn>model\n", "paragraph break \\n\\n": "\n\n", "<bos>": "<bos>"}
for k, v in parts.items(): print(f"{k:26s} {n(v)} tokens")
single_user = "<start_of_turn>user\nhi<end_of_turn>\n<start_of_turn>model\n"
print("one user turn + model opening, text 'hi':", n(single_user), "tokens, of which text 1 -> framing", n(single_user) - 1)
pair = "<start_of_turn>model\nHello.<end_of_turn>\n<start_of_turn>user\nhi<end_of_turn>\n"
print("assistant+user pair framing:", n(pair) - 3)   # Hello. = 2 tokens, hi = 1
print("with system prefix 'Be brief.\\n\\n':", n("<start_of_turn>user\nBe brief.\n\nhi<end_of_turn>\n<start_of_turn>model\n") - 1 - 3, "= framing beyond text (text 3 + 1)")
