"""Explicit live provider check with self-created synthetic evidence only."""
import json
import time
from uuid import uuid4

from app.config import Settings
from app.llm import generate_grounded
from app.research import Answer, validate_answer

config = Settings()
config.ai_provider = 'gemini'
config.gemini_model = 'gemini-3.1-flash-lite'
passage = {'id': uuid4(), 'text': 'SYNTHETIC TEST: The reading room has blue chairs.'}
started = time.monotonic()
try:
    raw = generate_grounded(config, [{'passage_id': str(passage['id']), 'text': passage['text']}],
                            'What color are the chairs? Answer in one short sentence.', [],
                            Answer.model_json_schema())
    answer = validate_answer(raw, [passage])
    print(json.dumps({'provider': 'gemini', 'model': config.gemini_model,
                      'validated_answer': bool(answer.paragraphs),
                      'seconds': round(time.monotonic()-started, 2),
                      'evidence': 'self-created synthetic test; no archive material transmitted',
                      'answer': answer.model_dump(mode='json')}))
except Exception as exc:
    print(json.dumps({'provider': 'gemini', 'model': config.gemini_model,
                      'validated_answer': False, 'error_type': type(exc).__name__, 'message': str(exc) if type(exc).__name__ == 'ProviderFailure' else 'Request failed'}))
