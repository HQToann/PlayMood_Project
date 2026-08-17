import re

with open('static/js/mood.js', 'r', encoding='utf-8') as f:
    content = f.read()

# Replace 'function name(' with 'window.name = function('
content = re.sub(r'^function\s+([a-zA-Z0-9_]+)\s*\(', r'window.\1 = function(', content, flags=re.MULTILINE)

# Replace 'async function name(' with 'window.name = async function('
content = re.sub(r'^async function\s+([a-zA-Z0-9_]+)\s*\(', r'window.\1 = async function(', content, flags=re.MULTILINE)

with open('static/js/mood.js', 'w', encoding='utf-8') as f:
    f.write(content)
