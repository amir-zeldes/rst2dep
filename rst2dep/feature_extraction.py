"""
Script to extract depdendency and XML markup information from data
in the conll10/conllu and CWB XML formats.

"""
import os, re, io
import ntpath
try:
    from .classes import ParsedToken, get_tense
except:
    from classes import ParsedToken, get_tense

def get_tok_info(docname,corpus_root):

    if corpus_root[-1]!=os.sep:
        corpus_root += os.sep

    xml_file = corpus_root + "xml" + os.sep + docname + ".xml"
    conll_file = corpus_root + "dep" + os.sep + docname + ".conll10"
    tokens = []

    try:
        lines = io.open(conll_file).read().replace("\r","").split("\n")
    except:
        lines = io.open(conll_file.replace(".conll10",".conllu")).read().replace("\r","").split("\n")
    offset = sent_toks = 0
    toks_by_abs_id = {}
    sid = 1
    for line in lines:
        if "\t" in line:
            cols = line.split("\t")
            if "-" in cols[0] or "." in cols[0]:
                continue
            tok = ParsedToken(cols[0],cols[1],cols[2],cols[3],cols[5],cols[6],cols[7])
            tok.abs_id = int(cols[0]) + offset
            tok.abs_head = int(cols[6]) + offset if cols[6] != "0" else 0
            tok.sent_id = sid
            toks_by_abs_id[tok.abs_id] = tok
            tokens.append(tok)
            sent_toks += 1
        elif len(line.strip())==0:
            offset += sent_toks
            sent_toks = 0
            sid += 1

    for tid, tok in enumerate(tokens):
        if tok.head != "0":
            tok.parent = toks_by_abs_id[tok.abs_head]
            if tok.abs_head-1 > tid:  # Only collect premodifiers, for tense classification
                tokens[tok.abs_head-1].children.append(tok)
        else:
            tok.parent = None

    counter = 0
    heading = "_"
    caption = "_"
    date = "_"
    list = "_"
    s_type = "_"
    para = "_"
    item = "_"
    for line in io.open(xml_file).read().replace("\r", "").split("\n"):
        if "<s type=" in line:
            m = re.search(r'<s type="([^"]+)"',line)
            s_type = m.group(1)
        if "<head" in line:
            heading = "head"
        elif "<caption" in line:
            caption = "caption"
        elif "</head" in line:
            heading = "_"
        elif "</caption" in line:
            caption = "_"
        elif '<list type="ordered' in line:
            list = "ordered"
        elif '<list type="unordered' in line:
            list = "unordered"
        elif "</list" in line:
            list = "_"
        elif '<date' in line:
            date = "date"
        elif "</date" in line:
            date = "_"
        elif '<p>' in line:
            para = "open_para"
        elif '<item>' in line:
            item = "open_item"
        if "\t" in line:
            fields = line.split("\t")
            tokens[counter].heading = heading
            tokens[counter].caption = caption
            tokens[counter].list = list
            tokens[counter].s_type = s_type
            tokens[counter].date = date
            tokens[counter].para = para
            tokens[counter].item = item
            tokens[counter].pos = fields[1]
            tokens[counter].lemma = fields[2]
            para = "_"
            item = "_"

            counter += 1

    return tokens

