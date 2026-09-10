from __future__ import annotations
import re
from dataclasses import dataclass, asdict
from typing import Iterable

@dataclass(frozen=True)
class ChecklistItem:
    text: str
    category: str
    pattern: str

@dataclass(frozen=True)
class CompressionResult:
    original: str
    compressed: str
    outcome: str
    original_tokens: int
    compressed_tokens: int
    checklist: tuple[ChecklistItem, ...]

ERROR_RE = re.compile(r'\b(?:HTTP\s*)?(?:[45]\d\d|[A-Z][A-Z0-9_-]*(?:Error|Exception|Failure))\b', re.I)
SECURITY_RE = re.compile(r'\b(?:security|authentication|authorization|authn|authz|permission|privilege|secret|token|credential|injection|xss|csrf|encryption|pii|sql injection)\b', re.I)
EDGE_RE = re.compile(r'\b(?:edge case|boundary|corner case|empty|missing|null|timeout|retry|fallback|race condition|concurrency|idempot(?:ent|ency)|rate limit)\b', re.I)
CODE_FENCE_RE = re.compile(r'(```.*?```|`[^`\n]+`)', re.S)


def tokens(text: str) -> int:
    return len(re.findall(r'\S+', text))


def checklist(text: str) -> list[ChecklistItem]:
    found: list[ChecklistItem] = []
    for line in text.splitlines():
        for rx, cat in ((ERROR_RE,'error'), (SECURITY_RE,'security'), (EDGE_RE,'edge_case')):
            m = rx.search(line)
            if m:
                found.append(ChecklistItem(line.strip(), cat, m.group(0)))
                break
    # Preserve explicit bullets because they often carry load-bearing caveats.
    for line in text.splitlines():
        if re.search(r'\b(?:must|never|always|warning|caveat|important|do not)\b', line, re.I):
            item=ChecklistItem(line.strip(),'caveat','load-bearing')
            if item not in found: found.append(item)
    return found


def _compress_segment(segment: str) -> str:
    lines = [x.strip() for x in segment.splitlines() if x.strip()]
    if not lines: return ''
    out=[]
    for line in lines:
        line=re.sub(r'^(?:In summary,|To summarize,|It is important to note that|Please note that)\s*','',line,flags=re.I)
        line=re.sub(r'\s+',' ',line)
        out.append(line)
    # Remove duplicate consecutive sentences while retaining order.
    text=' '.join(out)
    sentences=re.split(r'(?<=[.!?])\s+',text)
    seen=set(); kept=[]
    for s in sentences:
        key=re.sub(r'\W+','',s.lower())
        if key and key not in seen: kept.append(s); seen.add(key)
    return ' '.join(kept)


def compress(text: str, *, aggressiveness: str='balanced', telemetry_root=None) -> CompressionResult:
    items=checklist(text)
    chunks=CODE_FENCE_RE.split(text)
    out=[]
    for i,ch in enumerate(chunks):
        if i%2==1 or ch.strip().startswith('`'):
            out.append(ch.strip())
        else:
            out.append(_compress_segment(ch))
    compressed='\n\n'.join(x for x in out if x)
    if aggressiveness == 'conservative':
        compressed=text if tokens(compressed) >= tokens(text)*0.92 else compressed
    elif aggressiveness == 'aggressive':
        compressed=re.sub(r'\b(?:basically|generally|typically|essentially|actually)\b\s*','',compressed,flags=re.I)
    # Verification: every checklist pattern must still be represented.
    missing=[i for i in items if i.pattern.lower() not in compressed.lower() and i.text.lower() not in compressed.lower()]
    if missing:
        result = CompressionResult(text,text,'fallback',tokens(text),tokens(text),tuple(items))
    else:
        result = CompressionResult(text,compressed,'pass',tokens(text),tokens(compressed),tuple(items))
    if telemetry_root is not None:
        from .telemetry import CompressionTelemetry
        CompressionTelemetry(telemetry_root).record(outcome=result.outcome, original_tokens=result.original_tokens, compressed_tokens=result.compressed_tokens, checklist_items=len(result.checklist))
    return result


def result_dict(result: CompressionResult) -> dict:
    d=asdict(result); d['checklist']=[asdict(x) for x in result.checklist]; return d
