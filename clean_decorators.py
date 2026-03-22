import os
import re

DIR = '/Users/vasu/Downloads/murm'

# Match lines that consist of a comment symbol (#, //, or *) followed by repeated symbols like -, =, *, ~ 
decorative_pattern = re.compile(r'^\s*(#|//|\*|/\*)\s*[-=_~]+(\s*[-=_~]+\s*)*(\*/)?\s*$')

def clean_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 1. Remove emojis. A broad range matching most emojis but keeping normal text.
        # This regex targets emoji ranges.
        emoji_pattern = re.compile(r'[\U00010000-\U0010ffff]', flags=re.UNICODE)
        content_no_emoji = emoji_pattern.sub('', content)

        # 2. Remove decorative lines
        lines = content_no_emoji.split('\n')
        cleaned_lines = []
        for line in lines:
            if not decorative_pattern.match(line):
                cleaned_lines.append(line)

        new_content = '\n'.join(cleaned_lines)
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Cleaned: {filepath}")
    except Exception as e:
        pass

for root, dirs, files in os.walk(DIR):
    if '.git' in root or 'node_modules' in root or '__pycache__' in root or 'dist' in root or 'data' in root or '.venv' in root:
        continue
    for file in files:
        if file.endswith(('.py', '.jsx', '.js', '.md', '.txt', '.css')):
            clean_file(os.path.join(root, file))
