#!/usr/bin/env python
import re
import os
import yaml

class Markdown:

    _re_heading = re.compile("^(#+)\s(.+)")
    _re_message = re.compile("^(!+)\s(.+)")
    _re_media = re.compile("^!\[([^\]]+)\]\(([^\)\?]+)\??([^\)]*)\)")
    _re_list_ul_1 = re.compile("^([\s]*)\*\s(.*)")
    _re_list_ul_2 = re.compile("^([\s]*)-\s(.*)")
    _re_list_ol = re.compile("^([\s]*)[0-9]+\.\s(.*)")

    _re_no_paragraph = re.compile("^<(?:h[1-6]|pre|ul|ol|li|img|blockquote|div)")

    _re_code_1 = re.compile("`(.+?)`")
    _re_code_2 = re.compile("``(.+?)``")
    _re_link = re.compile("\[([^\]]+)\]\(([^\)]+)\)")
    _re_italic = re.compile("\*([^\*]+)\*")
    _re_bold = re.compile("\*\*([^\*]+)\*\*")
    _re_deleted = re.compile("~~([^~]+)~~")

    _re_external = re.compile("^https?://")


    def __init__(self, base_url: str = "") -> None:
        self._base_url = base_url

    def convert(self, text: str):
        self._reset()
        
        text = self._make_tidy(text)

        text = self._metadata(text)

        text = self._parse(text)

        self.html = text

    def _reset(self) -> None:
        self._lines = []
        self._extracted = {}
        self._line_empty = False
        self._in_fence = False
        self._in_paragraph = False
        self._in_blockquote = False
        self._list_type = []

    @property
    def _last_line_empty(self) -> bool:
        return len(self._lines) == 0 or len(self._lines[-1]) == 0

    @property
    def _list_depth(self) -> int:
        return len(self._list_type)

    def _make_tidy(self, text: str) -> str:
        """
        Cleans up the text so it can be converted easier
        """

        # Standardize line endings
        text = text.replace("\r\n", "\n")
        text = text.replace("\r", "\n")

        # Convert all tabs to spaces
        text = text.replace("\t", "    ")

        # Add new lines to the end for good measure
        text += "\n\n"

        return text

    def _metadata(self, text: str) -> str:
        if text[:3] == "---":
            _, metadata, text = text.split("---", 2)
            self.metadata = yaml.safe_load(metadata)
        else:
            self.metadata = []

        return text

    def _parse(self, text):
        
        for line in text.split("\n"):

            self._line_empty = len(line) == 0

            line = self._fence(line)

            if not self._in_fence:
                line = self._heading(line)
                line = self._notices(line)
                line = self._media(line)

                line = self._is_more(line)
                line = self._extract_code(line)
                line = self._bold(line)
                line = self._italic(line)
                line = self._deleted(line)
                line = self._link(line)
                line = self._insert_code(line)
                
                line = self._blockquote(line)
                line = self._list(line)
                line = self._paragraph(line)

            self._lines.append(line)

        return "\n".join(self._lines)

    def _is_more(self, line: str) -> str:
        if line.lower() in ["===", "<!-- more --!>"]:
            line = ""
        return line

    def _blockquote(self, line: str) -> str:
        if not self._line_empty and line[:2] == "> ":
            if not self._in_blockquote:
                self._lines.append("<blockquote>")
                self._in_blockquote = True
            line = line[2:]

        if self._line_empty and self._in_blockquote:
            self._lines.append("</blockquote>")
            self._in_blockquote = False

        return line

    def _list(self, line: str) -> str:
        re_list = [
            self._re_list_ol,
            self._re_list_ul_1,
            self._re_list_ul_2
        ]
        while len(re_list) > 0:
            m = re_list.pop().search(line)
            tag = "ul" if len(re_list) > 0 else "ol"
            if m:
                # if self._last_line_empty:
                if len(m.group(1)) // 4 + 1 > self._list_depth:
                    self._list_type.append(tag)
                    self._lines.append("<{}>".format(self._list_type[-1]))

                line = line.replace(m.group(0), "<li>{content}</li>".format(
                    content = m.group(2)
                ))

                if len(m.group(1)) // 4 + 1 < self._list_depth:
                    while len(m.group(1)) // 4 + 1 < self._list_depth:
                        self._lines.append("</{}>".format(self._list_type.pop()))

            if self._line_empty:
                while self._list_depth > 0:
                    self._lines.append("</{}>".format(self._list_type.pop()))

        return line

    def _paragraph(self, line: str) -> str:
        if self._last_line_empty and not self._line_empty and not self._re_no_paragraph.search(line):
            self._lines.append("<p>")
            self._in_paragraph = True

        if self._line_empty and not self._last_line_empty and self._in_paragraph:
            self._lines.append("</p>")
            self._in_paragraph = False
        
        return line

    def _heading(self, line: str) -> str:
        m = self._re_heading.search(line)
        if m:
            line = "<h{depth}>{heading}</h{depth}>".format(
                    depth = min(len(m.group(1)), 6),
                    heading = m.group(2)
                )
        return line

    def _media(self, line: str) -> str:
        m = self._re_media.search(line)
        if m:
            src = m.group(2)
            if self._base_url != "" and not self._re_external.search(src):
                src = self._base_url + "/" + src
            
            attributes = []
            align = "align-center"
            if m.group(3) != "":
                for attribute in [a.split("=") for a in m.group(3).split("&")]:

                    if attribute[0] == "resize":
                        if "," in attribute[1]:
                            width, height = attribute[1].split(",")
                            attributes.append("height=\"{}\"".format(int(height)))
                            attributes.append("width=\"{}\"".format(int(width)))
                        else:
                            attributes.append("height=\"{}\"".format(int(attribute[1])))
                    
                    elif attribute[0] == "align":
                        if attribute[1] in ["l", "L", "left", "Left"]:
                            align = "align-left"
                        elif attribute[1] in ["r", "R", "right", "Right"]:
                            align = "align-right"
                    
                    elif attribute[0] in ["autoplay", "controls", "loop", "muted"]:
                        attributes.append(attribute[0])
                    
                    elif attribute[0] == "preload-poster":
                        attributes.append("preload=\"none\"")
                        if len(attribute) == 2:
                            poster_src = attribute[1]
                            if self._base_url != "" and not self._re_external.search(poster_src):
                                poster_src = self._base_url + "/" + poster_src
                            attributes.append("poster=\"{src}\"".format(
                                src = poster_src
                            ))

            ext = os.path.splitext(src)[1].lower()
            if ext in [".png", ".jpg", ".gif", ".jpeg"]:
                attributes.append("loading=\"lazy\"")
                line = "<figure class=\"{align}\"><img src=\"{src}\" alt=\"{alt}\" {attributes}></figure>".format(
                    src = src,
                    alt = m.group(1),
                    attributes = " ".join(attributes),
                    align = align
                )
            elif ext in [".mp4", ".m4v"]:
                if "autoplay" in attributes:
                    attributes.append("playsinline")
                line = "<figure class=\"{align}\"><video {attributes}><source src=\"{src}\" alt=\"{alt}\" type=\"video/{type}\"></video></figure>".format(
                    src = src,
                    type = ext[1:],
                    alt = m.group(1),
                    attributes = " ".join(attributes),
                    align = align
                )
        return line

    def _notices(self, line: str) -> str:
        m = self._re_message.search(line)
        if m:
            classes = ["notices"]
            match len(m.group(1)):
                case 1:
                    classes.append("yellow")
                case 2:
                    classes.append("red")
                case 3:
                    classes.append("blue")
                case 4:
                    classes.append("green")
            
            line = "<div class=\"{classes}\">{message}</div>".format(
                classes = " ".join(classes),
                message = m.group(2)
            )
        return line

    def _extract_code(self, line: str) -> str:

        re_code = [self._re_code_1, self._re_code_2]
        while len(re_code) > 0:
            m = re_code[-1].search(line)
            while m:
                ex_value = "<code>{content}</code>".format(
                    content = m.group(1).replace("<", "&lt;").replace(">", "&gt;")
                )
                ex_key = "###<EXTRACTED-{id}>###".format(
                    id = len(self._extracted)
                )
                self._extracted[ex_key] = ex_value
                repl = m.group(0)
                line = line.replace(repl, ex_key)
                m = re_code[-1].search(line)
            re_code.pop()
        return line

    def _insert_code(self, line: str) -> str:
        for ex_key, ex_value in self._extracted.items():
            line = line.replace(ex_key, ex_value)

        self._extracted = {}
        return line

    def _bold(self, line: str) -> str:
        m = self._re_bold.search(line)
        while m:
            line = line.replace(m.group(0), "<em>{content}</em>".format(
                content = m.group(1)
            ))
            m = self._re_bold.search(line)

        return line

    def _italic(self, line: str) -> str:
        m = self._re_italic.search(line)
        while m:
            line = line.replace(m.group(0), "<i>{content}</i>".format(
                content = m.group(1)
            ))
            m = self._re_italic.search(line)

        return line

    def _link(self, line: str) -> str:
        m = self._re_link.search(line)
        while m:
            href = m.group(2)
            if self._base_url != "" and not self._re_external.search(href):
                href = self._base_url + "/" + href
            line = line.replace(m.group(0), "<a href=\"{href}\">{content}</a>".format(
                content = m.group(1),
                href = href
            ))
            m = self._re_link.search(line)

        return line

    def _deleted(self, line: str) -> str:
        m = self._re_deleted.search(line)
        while m:
            line = line.replace(m.group(0), "<del>{content}</del>".format(
                content = m.group(1)
            ))
            m = self._re_deleted.search(line)

        return line

    def _fence(self, line: str) -> str:
        if not self._line_empty:
            if line[:3] == "```":
                if not self._in_fence:
                    self._in_fence = True
                    line = "<pre><code class=\"language-{language}\">".format(
                        language = line[3:].strip()
                    )
                else:
                    self._in_fence = False
                    line = "</code></pre>"
            elif self._in_fence:
                line = line.replace("<", "&lt;").replace(">", "&gt;")
        
        return line
