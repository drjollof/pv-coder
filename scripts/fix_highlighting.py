import codecs
import re

with codecs.open('client/src/App.jsx', 'r', 'utf-8') as f:
    text = f.read()

# 1. Replace HighlightedText entirely to fix powershell variable interpolation bug
new_highlighted = """function HighlightedText({ text, events, drugs, excluded }) {
  const spans = [];
  (events || []).forEach((e, i) => { if(e.start_char != null) spans.push({ start: e.start_char, end: e.end_char, type: 'event', label: 'Adverse Event', id: `ev_${i}`, color: '#f43f5e', bg: 'rgba(244, 63, 94, 0.15)' }); });
  (drugs || []).forEach((d, i) => { if(d.start_char != null) spans.push({ start: d.start_char, end: d.end_char, type: 'drug', label: 'Suspected Drug', id: `dr_${i}`, color: '#f59e0b', bg: 'rgba(245, 158, 11, 0.15)' }); });
  (excluded || []).forEach((x, i) => { if(x.start_char != null) spans.push({ start: x.start_char, end: x.end_char, type: 'excluded', label: `Excluded: ${x.reason}`, id: `ex_${i}`, color: '#94a3b8', bg: 'rgba(148, 163, 184, 0.15)' }); });
  
  spans.sort((a, b) => a.start - b.start);
  
  // Greedy non-overlapping
  const validSpans = [];
  let lastEnd = 0;
  for (const s of spans) {
    if (s.start >= lastEnd && s.end > s.start) {
      validSpans.push(s);
      lastEnd = s.end;
    }
  }

  const parts = [];
  let cursor = 0;
  validSpans.forEach(s => {
    if (s.start > cursor) {
      parts.push(<span key={`t_${cursor}`}>{text.substring(cursor, s.start)}</span>);
    }
    parts.push(
      <span key={s.id} style={{ backgroundColor: s.bg, color: s.color, padding: '2px 4px', borderRadius: '4px', border: `1px solid ${s.color}`, cursor: 'pointer', position: 'relative' }} title={s.label}>
        {text.substring(s.start, s.end)}
      </span>
    );
    cursor = s.end;
  });
  if (cursor < text.length) {
    parts.push(<span key={`t_${cursor}`}>{text.substring(cursor)}</span>);
  }

  return <div style={{ lineHeight: '1.8', whiteSpace: 'pre-wrap' }}>{parts}</div>;
}"""

# Replace the old HighlightedText
text = re.sub(r'function HighlightedText.*?\n}\n', new_highlighted + '\n\n', text, flags=re.DOTALL)

# 2. Fix the legend colors
text = text.replace("background: 'var(--accent-primary)'", "background: '#f43f5e'")
text = text.replace("background: '#3b82f6'", "background: '#f59e0b'")
text = text.replace("background: '#6b7280'", "background: '#94a3b8'")

# 3. Fix the loading state ? issue
text = text.replace("<p>? Extracting entities</p>", "<p><CheckCircle size={14} style={{verticalAlign: 'middle', marginRight: '4px'}}/> Extracting entities</p>")
text = text.replace("<p>? Resolving clinical context</p>", "<p><CheckCircle size={14} style={{verticalAlign: 'middle', marginRight: '4px'}}/> Resolving clinical context</p>")
text = text.replace("<p>? Mapping MedDRA terms</p>", "<p><CircleDot size={14} style={{verticalAlign: 'middle', marginRight: '4px', color: 'var(--accent-primary)'}}/> Mapping MedDRA terms</p>")
text = text.replace("<p>? Building case</p>", "<p><Circle size={14} style={{verticalAlign: 'middle', marginRight: '4px'}}/> Building case</p>")

with codecs.open('client/src/App.jsx', 'w', 'utf-8') as f:
    f.write(text)

print('Updated App.jsx.')
