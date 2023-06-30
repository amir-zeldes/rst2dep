"""
Script to extract depdendency and XML markup information from data
in the conll10/conllu and CWB XML formats.

"""
import os, re, io
import ntpath
try:
    from .classes import ParsedToken
except:
    from classes import ParsedToken

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


def get_tense(tok):
    tense = "None"
    if tok.pos in ["VBD","VHD","VVD"]:
        tense = "PastSimp"
    elif tok.pos in ["VBP","VHP","VVP","VBZ","VHZ","VVZ"]:
        tense = "Pres"
    elif tok.pos in ["VBG","VVG","VHG"]:
        if any([t.lemma == "be" for t in tok.children]):
            if any([t.pos == "VBD" for t in tok.children if t.lemma=="be"]):
                tense = "PastProg"
            elif any([t.lemma == "have" and t.pos in ["VHP","VHZ","VBZ","VBP"] for t in tok.children]):
                tense = "PresPerfProg"
            else:
                tense = "PresProg"
    elif tok.pos in ["VBN","VVN","VHN"]:
        if any([t.lemma == "have" for t in tok.children]):
            if any([t.pos in ["VHD","VBD"] for t in tok.children if t.lemma == "have"]):
                if any([t.lemma == "be" and t.pos == "VBN" for t in tok.children]):
                    tense = "PastPerfProg"
                else:
                    tense = "PastPerf"
            else:
                if any([t.lemma in ["will","shall"] for t in tok.children]):
                    tense = "FutPerf"
                else:
                    tense = "PresPerf"
    elif tok.pos in ["VB","VV","VH"]:
        if any([t.lemma == "will" for t in tok.children]):
            if any([t.lemma == "have" for t in tok.children]):
                tense = "FutPerf"
            else:
                tense = "Fut"
        elif any([t.pos == "MD" for t in tok.children]):
            tense = "Modal"
    else:  # Check for copula
        if any([t.lemma == "be" and t.pos in ["VBZ","VBP"] for t in tok.children]):
            tense = "Pres"
        elif any([t.lemma == "be" and t.pos in ["VBD"] for t in tok.children]):
            tense = "PastSimp"
        elif any([t.lemma == "be" and t.pos in ["VBN"] for t in tok.children]):
            if any([t.pos in ["VHD","VBD"] for t in tok.children if t.lemma == "have"]):
                tense = "PastPerf"
            elif any([t.pos in ["VHZ","VBZ"] for t in tok.children if t.lemma == "have"]):
                tense = "PresPerf"
        elif any([t.lemma == "be" and t.pos in ["VB"] for t in tok.children]):
            if any([t.lemma == "will" for t in tok.children]):
                tense = "Fut"
            elif any([t.pos == "MD" for t in tok.children]):
                tense = "Modal"
    return tense
