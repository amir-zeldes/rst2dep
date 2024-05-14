from xml.dom import minidom
from xml.parsers.expat import ExpatError
import re, collections, sys, io


def rangify(token_string):
    # Reformat comma separated token ID into comma separated ranges with hyphens where needed
    # e.g. 1,2,3,4,5,6,7,8,9,10,13,14,15 -> 1-10,13-15
    if len(token_string) == 0:
        return ""
    tokens = token_string.split(",")
    tokens = [int(tok) for tok in tokens]
    tokens.sort()
    ranges = []
    start = tokens[0]
    end = tokens[0]
    for tok in tokens[1:]:
        if tok == end + 1:
            end = tok
        else:
            ranges.append(str(start) + "-" + str(end)) if end > start else ranges.append(str(start))
            start = tok
            end = tok
    ranges.append(str(start) + "-" + str(end)) if end > start else ranges.append(str(start))
    return ",".join(ranges)


class SIGNAL:
    def __init__(self, sigtype, sigsubtype, tokens):
        self.type = sigtype
        self.subtype = sigsubtype
        self.tokens = tokens

    def pretty_print(self, tokens=None):
        subtype = self.subtype
        if self.subtype in ["dm","orphan"] and tokens is not None:
            sorted_tokens = sorted([int(t) for t in self.tokens.split(",")])
            subtype = " ".join(tokens[int(t)-1].lower() for t in sorted_tokens)
        return "-".join([self.type, subtype, rangify(self.tokens)])

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

    def out_conll(self,feats=False,document_tokens=None, output_const_nid=False):
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
        top_nid = self.top_nid if output_const_nid else "_"
        signals = ";".join([sig.pretty_print(document_tokens) for sig in self.signals]) if len(self.signals) > 0 else "_"

        return "\t".join([self.id, self.text, str(self.dist), top_nid , "_", feats, self.dep_parent, self.dep_rel, "_", signals])

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


def read_rst(data, rel_hash, as_text=False):
    if not as_text:
        data = io.open(data, encoding="utf8").read()
    try:
        xmldoc = minidom.parseString(data)
    except ExpatError:
        message = "Invalid .rs3 file"
        sys.stderr.write(message)
        return message

    nodes = []
    ordered_id = {}
    schemas = []
    default_rst = ""

    # Get relation names and their types, append type suffix to disambiguate
    # relation names that can be both RST and multinuc
    item_list = xmldoc.getElementsByTagName("rel")
    for rel in item_list:
        relname = re.sub(r"[:;,]", "", rel.attributes["name"].value)
        if rel.hasAttribute("type"):
            rel_hash[relname + "_" + rel.attributes["type"].value[0:1]] = rel.attributes["type"].value
            if rel.attributes["type"].value == "rst" and default_rst == "":
                default_rst = relname + "_" + rel.attributes["type"].value[0:1]
        else:  # This is a schema relation
            schemas.append(relname)

    item_list = xmldoc.getElementsByTagName("segment")
    if len(item_list) < 1:
        return '<div class="warn">No segment elements found in .rs3 file</div>'

    id_counter = 0

    # Get hash to reorder EDUs and spans according to the order of appearance in .rs3 file
    for segment in item_list:
        id_counter += 1
        ordered_id[segment.attributes["id"].value] = id_counter
    item_list = xmldoc.getElementsByTagName("group")
    for group in item_list:
        id_counter += 1
        ordered_id[group.attributes["id"].value] = id_counter
    ordered_id["0"] = 0

    element_types = {}
    node_elements = xmldoc.getElementsByTagName("segment")
    for element in node_elements:
        element_types[element.attributes["id"].value] = "edu"
    node_elements = xmldoc.getElementsByTagName("group")
    for element in node_elements:
        element_types[element.attributes["id"].value] = element.attributes["type"].value


    # Collect all children of multinuc parents to prioritize which potentially multinuc relation they have
    item_list = xmldoc.getElementsByTagName("segment") + xmldoc.getElementsByTagName("group")
    multinuc_children = collections.defaultdict(lambda : collections.defaultdict(int))
    for elem in item_list:
        if elem.attributes.length >= 3:
            parent = elem.attributes["parent"].value
            relname = elem.attributes["relname"].value
            # Tolerate schemas by treating as spans
            if relname in schemas:
                relname = "span"
            relname = re.sub(r"[:;,]", "", relname)  # Remove characters used for undo logging, not allowed in rel names
            if parent in element_types:
                if element_types[parent] == "multinuc" and relname+"_m" in rel_hash:
                    multinuc_children[parent][relname] += 1

    id_counter = 0
    item_list = xmldoc.getElementsByTagName("segment")
    for segment in item_list:
        id_counter += 1
        if segment.hasAttribute("parent"):
            parent = segment.attributes["parent"].value
        else:
            parent = "0"
        if segment.hasAttribute("relname"):
            relname = segment.attributes["relname"].value
        else:
            relname = default_rst

        # Tolerate schemas, but no real support yet:
        if relname in schemas:
            relname = "span"
            relname = re.sub(r"[:;,]", "", relname)  # remove characters used for undo logging, not allowed in rel names

        # Note that in RSTTool, a multinuc child with a multinuc compatible relation is always interpreted as multinuc
        if parent in multinuc_children:
            if len(multinuc_children[parent]) > 0:
                key_list = list(multinuc_children[parent])[:]
                for key in key_list:
                    if multinuc_children[parent][key] < 2:
                        del multinuc_children[parent][key]

        if parent in element_types:
            if element_types[parent] == "multinuc" and relname + "_m" in rel_hash and (
                    relname in multinuc_children[parent] or len(multinuc_children[parent]) == 0):
                relname = relname + "_m"
            elif relname != "span":
                relname = relname + "_r"
        else:
            if not relname.endswith("_r") and len(relname) > 0:
                relname = relname + "_r"
        edu_id = segment.attributes["id"].value
        contents = segment.childNodes[0].data.strip()
        nodes.append(
            [str(ordered_id[edu_id]), id_counter, id_counter, str(ordered_id[parent]), 0, "edu", contents, relname])

    item_list = xmldoc.getElementsByTagName("group")
    for group in item_list:
        if group.attributes.length == 4:
            parent = group.attributes["parent"].value
        else:
            parent = "0"
        if group.attributes.length == 4:
            relname = group.attributes["relname"].value
            # Tolerate schemas by treating as spans
            if relname in schemas:
                relname = "span"

            relname = re.sub(r"[:;,]", "", relname)  # remove characters used for undo logging, not allowed in rel names
            # Note that in RSTTool, a multinuc child with a multinuc compatible relation is always interpreted as multinuc

            if parent in multinuc_children:
                if len(multinuc_children[parent])>0:
                    key_list = list(multinuc_children[parent])[:]
                    for key in key_list:
                        if multinuc_children[parent][key] < 2:
                            del multinuc_children[parent][key]

            if parent in element_types:
                if element_types[parent] == "multinuc" and relname + "_m" in rel_hash and (relname in multinuc_children[parent] or len(multinuc_children[parent]) == 0):
                    relname = relname + "_m"
                elif relname != "span":
                    relname = relname + "_r"
            else:
                relname = ""
        else:
            relname = ""
        group_id = group.attributes["id"].value
        group_type = group.attributes["type"].value
        contents = ""
        nodes.append([str(ordered_id[group_id]), 0, 0, str(ordered_id[parent]), 0, group_type, contents, relname])

    elements = {}
    for row in nodes:
        elements[row[0]] = NODE(row[0], row[1], row[2], row[3], row[4], row[5], row[6], row[7], "")

    for element in elements:
        if elements[element].kind == "edu":
            get_left_right(element, elements, 0, 0, rel_hash)

    for element in elements:
        node = elements[element]
        get_depth(node,node,elements)

    for nid in elements:
        node = elements[nid]
        if node.parent != "0":
            elements[node.parent].children.append(nid)
            if node.left == elements[node.parent].left:
                elements[node.parent].leftmost_child = nid

    # Ensure left most multinuc children are recognized even if there is an rst dependent further to the left
    for nid in elements:
        node = elements[nid]
        if node.kind == "multinuc" and node.leftmost_child == "":
            min_left = node.right
            leftmost = ""
            for child_id in node.children:
                child = elements[child_id]
                if child.relname.endswith("_m"):  # Using _m suffix to recognize multinuc relations
                    if child.left < min_left:
                        min_left = child.left
                        leftmost = child_id
            node.leftmost_child = leftmost

    secedge_list = xmldoc.getElementsByTagName("secedge")
    secedges = {}
    # Handle secedges, which look like this:
    # <secedge id="127-28" source="127" target="28" relname="causal-cause"/>
    for sec in secedge_list:
        source = str(sec.attributes["source"].value)
        target = str(sec.attributes["target"].value)
        relname = sec.attributes["relname"].value
        secedges[source + "-" + target] = SECEDGE(source,target,relname)

    signal_list = xmldoc.getElementsByTagName("signal")
    for sig in signal_list:
        nid = str(sig.attributes["source"].value)
        if nid not in elements:
            if "-" in nid:
                if nid not in secedges:
                    raise IOError("A signal element refers to source " + nid + " which is not found in the document\n")
                else:
                    secedges[nid].signals.append(SIGNAL(sig.attributes["type"].value,sig.attributes["subtype"].value,sig.attributes["tokens"].value))
                    continue
            else:
                raise IOError("A signal element refers to source " + nid + " which is not found in the document\n")
        elements[nid].signals.append(SIGNAL(sig.attributes["type"].value,sig.attributes["subtype"].value,sig.attributes["tokens"].value))

    for secedge in secedges:
        elements[secedge] = secedges[secedge]
        elements[secedge].kind = "secedge"

    return elements


def get_left_right(node_id, nodes, min_left, max_right, rel_hash):
    """
    Calculate leftmost and rightmost EDU covered by a NODE object. For EDUs this is the number of the EDU
    itself. For spans and multinucs, the leftmost and rightmost child dominated by the NODE is found recursively.
    """
    if nodes[node_id].parent != "0" and node_id != "0":
        parent = nodes[nodes[node_id].parent]
        if min_left > nodes[node_id].left or min_left == 0:
            if nodes[node_id].left != 0:
                min_left = nodes[node_id].left
        if max_right < nodes[node_id].right or max_right == 0:
            max_right = nodes[node_id].right
        if nodes[node_id].relname == "span":
            if parent.left > min_left or parent.left == 0:
                parent.left = min_left
            if parent.right < max_right:
                parent.right = max_right
        elif nodes[node_id].relname in rel_hash:
            if parent.kind == "multinuc" and rel_hash[nodes[node_id].relname] =="multinuc":
                if parent.left > min_left or parent.left == 0:
                    parent.left = min_left
                if parent.right < max_right:
                    parent.right = max_right
        get_left_right(parent.id, nodes, min_left, max_right, rel_hash)


def get_depth(orig_node, probe_node, nodes):
    """
    Calculate graphical nesting depth of a node based on the node list graph.
    Note that RST parentage without span/multinuc does NOT increase depth.
    """
    if probe_node.parent != "0":
        parent = nodes[probe_node.parent]
        if parent.kind != "edu" and (probe_node.relname == "span" or parent.kind == "multinuc" and probe_node.relkind =="multinuc"):
            orig_node.depth += 1
            orig_node.sortdepth +=1
        elif parent.kind == "edu":
            orig_node.sortdepth += 1
        get_depth(orig_node, parent, nodes)


def determinstic_groups(nodes):
    """
    Create an ID map with a deterministic ordering of group IDs based on a depth first climb of the ordered EDUs
    """
    edus = {e.id:e for e in nodes.values() if e.kind == "edu"}
    id_map = {str(e.id):str(e.id) for e in edus.values()}
    max_id = sorted([int(e.id) for e in edus.values()])[-1]
    for edu_id in sorted(edus,key=lambda x: int(edus[x].id)):
        parent = edus[edu_id].parent
        while int(parent) != 0:
            if parent not in id_map:
                max_id += 1
                id_map[str(parent)] = str(max_id)
            parent = nodes[parent].parent
    return id_map


def sequential_ids(rst_xml, id_map=None):
    # Ensure no gaps in node IDs and corresponding adjustments to signals and secedges.
    # Assume input xml IDs are already sorted, but with possible gaps
    output = []
    temp = []
    if id_map is None:
        current_id = 1
        id_map = {}
        for line in rst_xml.split("\n"):
            if ' id="' in line:
                xml_id = re.search(r' id="([^"]+)"', line).group(1)
                if ('<segment ' in line or '<group ' in line):
                    id_map[xml_id] = str(current_id)
                    line = line.replace(' id="' + xml_id + '"', ' id="' + str(current_id) + '"')
                    current_id += 1
            temp.append(line)
    else:
        for line in rst_xml.split("\n"):
            if ' id="' in line:
                xml_id = re.search(r' id="([^"]+)"', line).group(1)
                if ('<segment ' in line or '<group ' in line):
                    line = line.replace(' id="' + xml_id + '"', ' id="' + id_map[xml_id] + '"')
            temp.append(line)

    for line in temp:
        if ' id="' in line:
            if ' parent=' in line and ('<segment ' in line or '<group ' in line):
                parent_id = re.search(r' parent="([^"]+)"', line).group(1)
                new_parent = id_map[parent_id]
                line = line.replace(' parent="' + parent_id + '"', ' parent="' + str(new_parent) + '"')
            elif "<secedge " in line:
                xml_id = re.search(r' id="([^"]+)"', line).group(1)
                src, trg = xml_id.split("-")
                line = line.replace(' source="' + src + '"', ' source="' + id_map[src] + '"')
                line = line.replace(' target="' + trg + '"', ' target="' + id_map[trg] + '"')
                line = line.replace(' id="' + xml_id + '"', ' id="' + id_map[src] + '-' + id_map[trg] + '"')
        elif "<signal " in line:
            source = re.search(r' source="([^"]+)"', line).group(1)
            if "-" in source:
                src, trg = source.split("-")
                line = line.replace(' source="' + source + '"', ' source="' + id_map[src] + '-' + id_map[trg] + '"')
            else:
                line = line.replace(' source="' + source + '"', ' source="' + id_map[source] + '"')
        output.append(line)

    output = "\n".join(output)
    output = order_groups(output)

    return output

def order_groups(rst_xml):
    start = []
    groups = []
    end = []
    in_start = True
    for line in rst_xml.split("\n"):
        if "<group " in line:
            in_start = False
            groups.append(line)
        elif in_start:
            start.append(line)
        else:
            end.append(line)
    groups.sort(key=lambda x: int(re.search(r'<group id=.([0-9]+)',x).group(1)))

    output = start + groups + end

    return "\n".join(output)


def make_deterministic_nodes(rst_xml):
    ordered_xml = order_groups(rst_xml)
    no_gaps_xml = sequential_ids(ordered_xml,id_map=None)
    nodes = read_rst(no_gaps_xml, {}, as_text=True)
    id_map = determinstic_groups(nodes)
    fixed = sequential_ids(no_gaps_xml,id_map=id_map)
    return fixed


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
