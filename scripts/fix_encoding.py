import codecs

try:
    with codecs.open('client/src/App.jsx', 'r', 'utf-16-le') as f:
        text = f.read()
    if 'SingleIntake' not in text:
        raise Exception('Not utf-16')
except Exception:
    with codecs.open('client/src/App.jsx', 'r', 'utf-8', errors='ignore') as f:
        text = f.read()

# Replace powershell mangled unicode characters
text = text.replace('? Serious', '● Serious')
text = text.replace('? Non-serious', '○ Non-serious')
text = text.replace('? Review Required', '⚠ Review Required')
text = text.replace('? Auto-coded', '✓ Auto-coded')
text = text.replace('? REVIEW REQUIRED', '⚠ REVIEW REQUIRED')

# For the workflow steps (which uses ? as well):
# Original: {idx < currentStep ? '✓' : (idx === currentStep ? '●' : '○')}
text = text.replace("? '?' : (idx === currentStep ? '?' : '?')", "? '✓' : (idx === currentStep ? '●' : '○')")

with codecs.open('client/src/App.jsx', 'w', 'utf-8') as f:
    f.write(text)

print('File rewritten as UTF-8.')
