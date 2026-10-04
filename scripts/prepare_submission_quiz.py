"""Prepare source-checked local quiz draft; no database, authentication or publication."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "outputs/submission-sources"


def prepare():
    texts = [(ROOT / f"{key}-excerpt.txt").read_text(encoding="utf-8").strip()
             for key in ("constitution", "biography")]
    # Each support quote is checked literally against the captured, reviewed excerpt.
    rows = [
        ("Who chaired the Drafting Committee, according to paragraph 42?",
         ["Dr. Rajendra Prasad", "Dr. B. R. Ambedkar"], 1,
         "Dr. B.R. Ambedkar as the Chairman of the Drafting Committee", 0,
         "Paragraph 42 identifies Ambedkar as Chairman of the Drafting Committee."),
        ("Who was President of the Constituent Assembly in the excerpt?",
         ["Dr. Rajendra Prasad", "Dr. B. R. Ambedkar"], 0,
         "Dr. Rajendra Prasad as its President", 0,
         "Paragraph 42 assigns the Assembly presidency to Rajendra Prasad."),
        ("On which date was the Constitution adopted?",
         ["26 January 1950", "24 January 1950", "26 November 1949"], 2,
         "the Constitution was adopted by We, the People of India, on 26 November 1949", 0,
         "Paragraph 42 dates adoption to 26 November 1949."),
        ("When did members append their signatures to the Constitution?",
         ["24 January 1950", "26 November 1949", "26 January 1950"], 0,
         "appended their signatures to it on 24 January 1950", 0,
         "Paragraph 42 dates members' signatures to 24 January 1950."),
        ("How many Articles and Schedules did the Constitution have when it came into force, according to the excerpt?",
         ["8 Articles and 395 Schedules", "395 Articles and 8 Schedules"], 1,
         "came into force on 26 January 1950 had 395 Articles and 8 Schedules", 0,
         "This count describes the Constitution at commencement, not its present amended form."),
        ("Where did the Assembly hold the deliberations described in paragraph 42?",
         ["Central Hall of Parliament House", "A location not identified in the excerpt"], 0,
         "held intensive deliberations in the Central Hall of Parliament House", 0,
         "The excerpt explicitly names the Central Hall of Parliament House."),
        ("Which date is recorded as Ambedkar's birth date?",
         ["26 November 1949", "14 April 1891", "26 January 1950"], 1,
         "Baba Saheb Dr. Bhim Rao Ambedkar was born on 14 April 1891", 1,
         "The opening bullet of the 2024 PIB account records 14 April 1891."),
        ("Which sequence agrees with the three constitutional milestones in paragraph 42?",
         ["Signing, commencement, adoption", "Adoption, signing, commencement", "Commencement, adoption, signing"], 1,
         "Thereafter, the Constitution was adopted by We, the People of India, on 26 November 1949 and the members of the Constituent Assembly appended their signatures to it on 24 January 1950. The Constitution which came into force on 26 January 1950", 0,
         "The stated dates put adoption first, signatures second and commencement third."),
        ("What distinction does the excerpt make between adoption and commencement?",
         ["They occurred on different dates", "They occurred on the same date"], 0,
         "on 26 November 1949 and the members of the Constituent Assembly appended their signatures to it on 24 January 1950. The Constitution which came into force on 26 January 1950", 0,
         "Adoption is dated 26 November 1949; commencement is dated 26 January 1950."),
        ("Which description matches the Assembly's role immediately before commencement?",
         ["It ceased all functions immediately", "It became the Provisional Parliament and continued until the first General Elections in 1952"], 1,
         "Immediately before the commencement of the Constitution, the Constituent Assembly became the Provisional Parliament of India and functioned as such until the first General Elections based on adult franchise were held in 1952", 0,
         "Paragraph 42 describes continuity as the Provisional Parliament until the 1952 elections."),
    ]
    questions, checks = [], []
    for prompt, options, correct, quote, source, explanation in rows:
        assert quote in texts[source], prompt
        assert options[correct] and len(options) == len(set(options))
        questions.append(dict(prompt=prompt, options=options, correct=correct,
                              explanation=explanation, source_index=source))
        checks.append(dict(question=prompt, source_index=source, exact_support_quote=quote))
    result = dict(status="local reviewed candidate; not a database draft or publication",
                  source_keys=["constitution", "biography"],
                  source_text_sha256=[hashlib.sha256(t.encode()).hexdigest() for t in texts],
                  questions=questions, validation=checks)
    return result


if __name__ == "__main__":
    result = prepare()
    (ROOT / "quiz-review.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print("10 questions prepared; 10 exact support quotes checked. No records created or published.")
