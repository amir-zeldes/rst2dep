class SIGNAL:
    def __init__(self, sigtype, sigsubtype, tokens):
        self.type = sigtype
        self.subtype = sigsubtype
        self.tokens = tokens

    def __repr__(self):
        return self.type + "/" + self.subtype + " (" + self.tokens + ")"

    def __str__(self):
        return "|".join([self.type,self.subtype,self.tokens])


class SECEDGE:
    def __init__(self, source, target, relname, signals=None):
        """Class to hold secondary edges"""
        if signals is None:
            signals = []
        self.id = source + "-" + target
        self.source = source
        self.target = target
        self.relname = relname
        self.signals = signals

class NODE:
    def __init__(self, id, left, right, parent, depth, kind, text, relname, relkind, signals=None):
        """Basic class to hold all nodes (EDU, span and multinuc) in structure.py and while importing"""

        if signals is None:
            signals = []
        self.id = id
        self.parent = parent
        self.left = left
        self.right = right
        self.depth = depth
        self.dist = 0
        self.domain = 0  # Minimum sorted covering multinuc domain priority
        self.kind = kind #edu, multinuc or span node
        self.text = text #text of an edu node; empty for spans/multinucs
        self.token_count = text.count(" ") + 1
        self.relname = relname
        self.relkind = relkind #rst (a.k.a. satellite), multinuc or span relation
        self.sortdepth = depth
        self.children = []
        self.leftmost_child = ""
        self.dep_parent = ""
        self.dep_rel = relname
        self.tokens = []
        self.parse = ""
        self.signals = signals

    def rebuild_parse(self):
        token_lines = []
        for tok in self.tokens:
            # prevent snipped tokens from pointing outside EDU
            if int(tok.head) < int(self.tokens[0].id):
                tok.head = "0"
            elif int(tok.head) > int(self.tokens[-1].id):
                tok.head = "0"
            token_lines.append("|||".join([tok.id,tok.text,tok.lemma,tok.pos,tok.pos,tok.morph,tok.head,tok.func,"_","_"]))
        self.parse = "///".join(token_lines)

    def out_conll(self,feats=False):
        self.rebuild_parse()
        head_word = "_"
        if len(self.tokens) == 0:  # No token information
            self.tokens.append(ParsedToken("1","_","_","_","_","0","_"))
        head_func = "_"

        if feats:
            first_pos = "pos1=" + self.tokens[0].pos
            sent_id = "sid=" + str(self.tokens[0].sent_id)
            for tok in self.tokens:
                if tok.head == "0" and not tok.func == "punct":
                    head_word = "head_tok="+tok.lemma.replace("=","&eq;")
                    head_func = "head_func="+tok.func
                    head_pos = "head_pos="+tok.pos
                    head_id = "head_id="+str(tok.abs_id)
                    head_parent_pos = "parent_pos" + tok.parent.pos if tok.parent is not None else "parent_pos=_"
                    edu_tense = "edu_tense=" + get_tense(tok)
                if tok.pos in ["PRP", "PP"]:
                    pro = "pro"
                else:
                    pro = "nopro"
                if tok.func == "root":
                    break
            if self.tokens[0].text.istitle():
                caps = "caps"
            else:
                caps = "nocaps"
            last_tok = self.tokens[-1].lemma
            if self.heading == "head":
                self.heading = "heading=heading"
            if self.caption== "caption":
                self.heading = "caption=caption"
            if self.para== "open_para":
                self.para = "para=para"
            if self.item== "open_item":
                self.item = "item=item"
            if self.list== "ordered":
                self.list = "list=ordered"
            if self.list== "unordered":
                self.list = "list=unordered"
            if self.caption== "date":
                self.heading = "date=date"
            if self.subord in ["LEFT","RIGHT"]:
                self.subord = "subord=" + self.subord
            feats = "|".join(feat for feat in [first_pos, head_word, head_pos, head_id, head_parent_pos, sent_id, "stype="+self.s_type, "len="+str(len(self.tokens)), head_func, edu_tense, self.subord, self.heading, self.caption, self.para, self.item, self.date] if feat != "_")
            if len(feats)==0:
                feats = "_"
        else:
            feats = "_"

        signals = ";".join([str(sig) for sig in self.signals]) if len(self.signals) > 0 else "_"
        return "\t".join([self.id, self.text, str(self.dist),"_", "_", feats, self.dep_parent, self.dep_rel, "_", signals])

    def out_malt(self):
        first = self.tokens[0].lemma
        first_pos = self.tokens[0].pos
        self.rebuild_parse()
        head_word = "_"
        for tok in self.tokens:
            if tok.head == "0" and not tok.func == "punct":
                head_word = tok.lemma
                head_func = tok.func
                head_pos = tok.pos
            if tok.pos in ["PRP", "PP"]:
                pro = "pro"
            else:
                pro = "nopro"
        if self.tokens[0].text.istitle():
            caps = "caps"
        else:
            caps = "nocaps"
        last_tok = self.tokens[-1].lemma
        feats = "|".join(feat for feat in [str(len(self.tokens)), head_func, self.subord, self.heading, self.caption, self.para, self.item, self.date] if feat != "_")
        if len(feats)==0:
            feats = "_"

        return "\t".join([self.id, first, head_word, self.s_type, first_pos, feats, self.dep_parent, self.dep_rel, "_", self.parse])

    def __repr__(self):
        return "\t".join([str(self.id),str(self.parent),self.relname,self.text])


class ParsedToken:
    def __init__(self, tok_id, text, lemma, pos, morph, head, func):
        self.id = tok_id
        self.text = text.strip()
        self.text_lower = text.lower()
        self.pos = pos
        self.lemma = lemma if lemma != "_" else text
        self.morph = morph
        self.head = head
        self.func = func
        self.heading = "_"
        self.caption = "_"
        self.list = "_"
        self.date = "_"
        self.s_type = "_"
        self.children = []

    def __repr__(self):
        return str(self.text) + " (" + str(self.pos) + "/" + str(self.lemma) + ") " + "<-" + str(self.func) + "- " + str(self.head_text)

