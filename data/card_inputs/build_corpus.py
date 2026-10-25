# The seeded script that built the 429-string corpus of the tokenizer test (REPORT 27.1), REDACTED for this repository.
#
# Removed: (1) the two private sources it sampled first, the author's research corpus (110 English sentences, "english prose")
# and the author's report (60 sentences, "english report text"); (2) two strings of the "numbers urls emoji" list that
# contained the author's name, a URL on the author's site and a Windows path with the author's user name. Everything else is
# as run on 2026-10-24.
#
# This copy cannot rebuild the corpus: the private sampling steps it began with moved the seeded random generator, so the
# code lines and rare words it would pick now differ. The strings actually used are in data/tokenizer_test/strings_public.csv
# (the 257 public ones, with every count) and data/tokenizer_test/counts_all_429.csv (all 429, counts only).
import glob, json, random, re
from pathlib import Path

HERE = Path(__file__).resolve().parent
rnd = random.Random(7)
def sentences(path, n):
    txt = open(path, errors="ignore").read()
    txt = re.sub(r"```.*?```", " ", txt, flags=re.S); txt = re.sub(r"[#*`|>_\[\]()]", " ", txt)
    ss = [s.strip() for s in re.split(r"(?<=[.!?])\s+", txt) if 40 <= len(s.strip()) <= 220]
    return rnd.sample(ss, min(n, len(ss)))
cats = {}
# REDACTED: 40 files sampled from the author's research corpus, 3 sentences from each, the first 110 kept:
#   cats["english prose"] = eng[:110]
# REDACTED: 60 sentences sampled from the author's report:
#   cats["english report text"] = sentences(<the report>, 60)
ml = {"fr": ["Il fait beau aujourd'hui, alors nous allons nous promener dans le parc avec nos amis.", "Le gouvernement a annoncé de nouvelles mesures pour soutenir les petites entreprises face à l'inflation.", "L'intelligence artificielle transforme la manière dont nous travaillons, apprenons et communiquons."],
 "de": ["Das Wetter ist heute schön, deshalb gehen wir mit unseren Freunden im Park spazieren.", "Die Bundesregierung hat neue Maßnahmen zur Unterstützung kleiner Unternehmen beschlossen.", "Künstliche Intelligenz verändert die Art, wie wir arbeiten und lernen."],
 "es": ["Hoy hace buen tiempo, así que vamos a pasear por el parque con nuestros amigos.", "El gobierno anunció nuevas medidas para apoyar a las pequeñas empresas frente a la inflación.", "La inteligencia artificial está cambiando la forma en que trabajamos y aprendemos."],
 "it": ["Oggi il tempo è bello, quindi andiamo a passeggiare nel parco con i nostri amici.", "Il governo ha annunciato nuove misure per sostenere le piccole imprese.", "L'intelligenza artificiale sta cambiando il modo in cui lavoriamo e impariamo."],
 "pt": ["Hoje o tempo está bom, então vamos passear no parque com os nossos amigos.", "O governo anunciou novas medidas para apoiar as pequenas empresas.", "A inteligência artificial está mudando a maneira como trabalhamos e aprendemos."],
 "nl": ["Het weer is vandaag mooi, dus we gaan met onze vrienden in het park wandelen.", "De regering heeft nieuwe maatregelen aangekondigd om kleine bedrijven te steunen."],
 "ja": ["今日は天気がいいので、友達と一緒に公園を散歩します。", "政府は中小企業を支援するための新しい対策を発表しました。", "人工知能は私たちの働き方や学び方を変えています。"],
 "ko": ["오늘은 날씨가 좋아서 친구들과 함께 공원에서 산책할 거예요.", "정부는 중소기업을 지원하기 위한 새로운 대책을 발표했습니다."],
 "zh": ["今天天气很好,所以我们要和朋友们一起去公园散步。", "政府宣布了支持中小企业的新措施。", "人工智能正在改变我们工作和学习的方式。"],
 "ar": ["الطقس جميل اليوم، لذلك سنذهب للتنزه في الحديقة مع أصدقائنا.", "أعلنت الحكومة عن إجراءات جديدة لدعم الشركات الصغيرة."],
 "hi": ["आज मौसम अच्छा है, इसलिए हम अपने दोस्तों के साथ पार्क में टहलने जाएंगे।", "सरकार ने छोटे व्यवसायों का समर्थन करने के लिए नए उपायों की घोषणा की।"],
 "ru": ["Сегодня хорошая погода, поэтому мы пойдём гулять в парк с друзьями.", "Правительство объявило о новых мерах поддержки малого бизнеса."],
 "tr": ["Bugün hava güzel, bu yüzden arkadaşlarımızla parkta yürüyüşe çıkacağız.", "Hükümet küçük işletmeleri desteklemek için yeni önlemler açıkladı."],
 "vi": ["Hôm nay thời tiết đẹp, vì vậy chúng tôi sẽ đi dạo trong công viên cùng bạn bè.", "Chính phủ đã công bố các biện pháp mới để hỗ trợ các doanh nghiệp nhỏ."],
 "th": ["วันนี้อากาศดี เราจึงจะไปเดินเล่นในสวนสาธารณะกับเพื่อน ๆ"], "he": ["מזג האוויר יפה היום, אז אנחנו הולכים לטייל בפארק עם החברים שלנו."], "sv": ["Vädret är fint idag, så vi ska promenera i parken med våra vänner."], "pl": ["Dziś jest ładna pogoda, więc idziemy na spacer do parku z przyjaciółmi."]}
cats["multilingual"] = [s for v in ml.values() for s in v]
code = []
for f in glob.glob(str(HERE.parent / "*.py"))[:12]:   # as run: the first 12 .py files of the report's data folder
    for l in open(f, errors="ignore"):
        l = l.rstrip()
        if 25 <= len(l) <= 160 and not l.strip().startswith("#"): code.append(l.strip())
cats["code"] = rnd.sample(code, 80)
cats["numbers urls emoji"] = ["3.14159265358979", "1,284,500.75", "2026-10-24T14:22:13+02:00", "0xDEADBEEFCAFE",
  # REDACTED here: a URL on the author's site
  "user.name+tag@example.co.uk",
  "192.168.100.254", "x = 3 * (y ** 2) - 17 / z", "∑_{i=1}^{n} i^2 = n(n+1)(2n+1)/6", "😀🚀🎉👍🔥", "⚡ fast ✅ done ❌ failed", "1234567890123456789", "SELECT id, name FROM users WHERE age > 30 ORDER BY name;",
  # REDACTED here: a Windows path with the author's user name
  "{\"key\": [1, 2, 3], \"ok\": true, \"name\": \"x\"}", "#include <stdio.h>", "git commit -m \"fix: handle empty input\"", "$ ls -la /usr/local/bin | grep python", "AAAAAAAAAAAAAAAAAAAAAAAA", "a b c d e f g h i j k l m n o p"]
words = [w.strip() for w in open("/usr/share/dict/words", errors="ignore") if w.strip().isalpha()]
cats["rare words"] = [f"The word is {w}." for w in rnd.sample([w for w in words if len(w) >= 9], 120)]
json.dump(cats, open(HERE / "corpus_redacted.json", "w"), ensure_ascii=False, indent=0)
print({k: len(v) for k, v in cats.items()}, "total", sum(len(v) for v in cats.values()))
