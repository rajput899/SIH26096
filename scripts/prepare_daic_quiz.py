"""Local-only ten-question DAIC dataset candidate; no publication or DB writes."""
import hashlib
import json
from pathlib import Path
import pypdfium2 as pdfium

source = Path("Dataset/Volume_01.pdf")
pages = {}
with pdfium.PdfDocument(source) as pdf:
    for number in (12, 18):
        page = pdf[number - 1]
        text = page.get_textpage()
        pages[number] = " ".join(text.get_text_range().split())
        text.close()
        page.close()
rows = [
    (18, "What is the paper title on this page?", ["Castes in India", "Annihilation of Caste"], 0,
     "CASTES IN INDIA", "The heading names the paper Castes in India."),
    (18, "Which seminar is named as the setting for the paper?", ["An economics seminar", "The Anthropology Seminar"], 1,
     "the Anthropology Seminar", "The title page specifies the Anthropology Seminar."),
    (18, "Which university is named on the paper's title page?", ["The Columbia University", "A university not identified on this page"], 0,
     "The Columbia University, New York, U.S.A.", "The page names Columbia University in New York."),
    (18, "Which date does the page give for reading the paper?", ["May 1917", "9th May 1916"], 1,
     "on 9th May 1916", "The reading date is 9 May 1916; the later journal reference is a different date."),
    (12, "How should an ideal society respond to change in one of its parts?", ["Convey it through channels to other parts", "Keep each part isolated"], 0,
     "channels for conveying a change taking place in one part to other parts", "The excerpt describes channels connecting changes across society."),
    (12, "How does the excerpt describe interests in an ideal society?", ["Kept entirely private and separate", "Consciously communicated and shared"], 1,
     "many interests consciously communicated and shared", "Communication and sharing are explicitly stated."),
    (12, "Which kind of contact does the passage favour?", ["Varied and free contact with other modes of association", "No contact with other modes of association"], 0,
     "varied and free points of contact with other modes of association", "The passage favours varied and free points of contact."),
    (12, "Which term does the passage call another name for democracy?", ["Isolation", "Fraternity"], 1,
     "This is fraternity, which is only another name for democracy", "The passage explicitly connects fraternity and democracy."),
    (12, "Does this passage limit democracy to a form of government?", ["No; it describes associated living and communicated experience", "Yes; it describes only government structure"], 0,
     "Democracy is not merely a form of Government. It is primarily a mode of associated living, of conjoint communicated experience", "Democracy is described more broadly than a form of government."),
    (12, "Which attitude towards fellow people does the passage associate with democracy?", ["Indifference", "Respect and reverence"], 1,
     "an attitude of respect and reverence towards fellowmen", "The final sentence identifies respect and reverence."),
]
questions = []
for number, prompt, options, correct, quote, explanation in rows:
    assert quote in pages[number], prompt
    questions.append(dict(prompt=prompt, options=options, correct=correct,
                          explanation=explanation, source_index=0,
                          support=dict(pdf_page=number, exact_normalized_quote=quote)))
result = dict(title="Reading Volume 1: caste and democratic association",
              status="LOCAL DRAFT ONLY — extracted-text support checked; original-page and curator review pending",
              item_id="179956fd-df91-4b4e-99b1-63d21dc174a4", verified_revision=None,
              source_path=str(source), original_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
              page_locator_basis="1-based PDF physical page, not printed page number",
              permission="DAIC prototype use per owner statement; broader release not established",
              questions=questions, extracted_page_evidence=pages)
Path("outputs/daic-quiz-draft.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
print("10 dataset questions drafted; 10 support passages matched. Not created in DB or published: verified revision unavailable.")
