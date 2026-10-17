"""Iz web/page.html (vir strani, ista datoteka kot na claude.ai) naredi docs/index.html za GitHub Pages."""
src = open("web/page.html", encoding="utf-8").read()
head = ('<!doctype html>\n<html lang="sl">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
        '<meta name="description" content="Podjetja v krogu 1000 km od Jesenic, ki potrebujejo modele, kalupe in rezkanje – Proform3D.">\n'
        '<style>:root{color-scheme:light;padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
        'body{margin:0;font:14px system-ui,-apple-system,"Segoe UI",sans-serif}img{max-width:100%}[hidden]{display:none!important}</style>\n')
i = src.index("</style>") + len("</style>")
open("docs/index.html", "w", encoding="utf-8").write(head + src[:i] + "\n</head>\n<body>\n" + src[i:] + "\n</body>\n</html>\n")
print("docs/index.html posodobljen")
