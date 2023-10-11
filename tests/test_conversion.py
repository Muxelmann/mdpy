import mdpy

with open('test.md', 'r') as f:
    md = mdpy.Markdown()
    md.convert(f.read())
    print(md.html)
