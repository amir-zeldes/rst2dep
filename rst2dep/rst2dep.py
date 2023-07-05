#!/usr/bin/python
# -*- coding: utf-8 -*-

"""
Script to convert Rhetorical Structure Theory trees from .rs3 or .rs4 format
to a CoNLL-style dependency representation, a.k.a. .rsd.
"""


import re, io, ntpath, collections, sys
from argparse import ArgumentParser
try:
    from .classes import NODE, SIGNAL, SECEDGE, ParsedToken, read_rst, get_tense
except:
    from classes import NODE, SIGNAL, SECEDGE, ParsedToken, read_rst, get_tense

# Add hardwired genre identifiers which appear as substring in filenames here
GENRES = {"_news_":"news","_whow_":"whow","_voyage_":"voyage","_interview_":"interview",
          "_bio_":"bio","_fiction_":"fiction","_academic_":"academic","_reddit_":"reddit",
          "_speech_":"speech","_textbook_":"textbook","_vlog_":"vlog","_conversation_":"conversation",}


def find_dep_head(nodes, source, exclude, block):
    parent = nodes[source].parent
    if parent != "0":
        if nodes[parent].kind == "multinuc":
            for child in nodes[parent].children:
                # Check whether exclude and child are under the same multinuc and exclude is further to the left
                if nodes[child].left > int(exclude) and nodes[child].left >= nodes[parent].left and int(exclude) >= nodes[parent].left:
                    block.append(child)
    else:
        # Prevent EDU children of root from being dep head - only multinuc children possible at this point
        for child in nodes[source].children:
            if nodes[child].kind == "edu":
                block.append(child)
    candidate = seek_other_edu_child(nodes, nodes[source].parent, exclude, block)
    if candidate is not None:
        return candidate
    else:
        if parent == "0":
            return None
        else:
            if parent not in nodes:
                raise IOError("Node with id " + source + " has parent id " + parent + " which is not listed\n")
            return find_dep_head(nodes, parent, exclude, block)


def seek_other_edu_child(nodes, source, exclude, block):
    """
    Recursive function to find some child of a node which is an EDU and does not have the excluded ID

    :param nodes: dictionary of IDs to NODE objects
    :param source: the source node from which to traverse
    :param exclude: node ID to exclude as target child
    :param block: list of IDs for which children should not be traversed (multinuc right children)
    :return: the found child ID or None if none match
    """

    if source == "0":
        return None
    else:
        # Check if this is already an EDU
        if nodes[source].kind == "edu" and source != exclude and source not in block:
            return source
        # Loop through children of this node
        children_to_search = [child for child in nodes[source].children if child not in nodes[exclude].children and child not in block]
        if len(children_to_search)>0:
            if int(exclude) < int(children_to_search[0]):
                children_to_search.sort(key=lambda x: int(x))
            else:
                children_to_search.sort(key=lambda x: int(x), reverse=True)
        for child_id in children_to_search:
            # Found an EDU child which is not the original caller
            if nodes[child_id].kind == "edu" and child_id != exclude and (nodes[source].kind != "span" or nodes[child_id].relname == "span") and \
                    not (nodes[source].kind == "multinuc" and nodes[source].leftmost_child == exclude) and \
                    (nodes[nodes[child_id].parent].kind not in ["span","multinuc"]):
                    #not (nodes[child_id].parent == nodes[exclude].parent and nodes[source].kind == "multinuc" and int(child_id) > int(exclude)):  # preclude right pointing rel between multinuc siblings
                return child_id
            # Found a non-terminal child
            elif child_id != exclude:
                # If it's a span, check below it, following only span relation paths
                if nodes[source].kind == "span":
                    if nodes[child_id].relname == "span":
                        candidate = seek_other_edu_child(nodes, child_id, exclude, block)
                        if candidate is not None:
                            return candidate
                # If it's a multinuc, only consider the left most child as representing it topographically
                elif nodes[source].kind == "multinuc" and child_id == nodes[source].leftmost_child:
                    candidate = seek_other_edu_child(nodes, child_id, exclude, block)
                    if candidate is not None:
                        return candidate
    return None


def get_distance(node, parent, nodes):
    head = node.parent
    dist = 1
    encountered = {}
    while head != parent.id:
        encountered[head] = dist
        head = nodes[head].parent
        dist += 1
        if head == "0":
            break
    if head == "0":
        # common ancestor
        dist2 = 1
        head = parent.parent
        while head != "0":
            if head in encountered:
                if nodes[head].kind == "multinuc" and node.dep_rel.endswith("_m"):  # multinucs should have priority against tying incoming RST rels
                    dist2 -= 1
                return dist2 #+ encountered[head]
            else:
                dist2 += 1
                head = nodes[head].parent
        return dist2 #+ encountered[head]
    else:
        # direct ancestry
        return 0  # dist


def get_nonspan_rel(nodes,node):
    if node.parent == "0":  # Reached the root
        return "ROOT"
    elif nodes[node.parent].kind == "multinuc" and nodes[node.parent].leftmost_child == node.id:
        return get_nonspan_rel(nodes, nodes[node.parent])
    elif nodes[node.parent].kind == "multinuc" and nodes[node.parent].leftmost_child != node.id:
        return node#.relname
    elif nodes[node.parent].relname != "span":
        grandparent = nodes[node.parent].parent
        if grandparent == "0":
            return "ROOT"
        elif not (nodes[grandparent].kind == "multinuc" and nodes[node.parent].left == nodes[grandparent].left):
            return nodes[node.parent]#.relname
        else:
            return get_nonspan_rel(nodes,nodes[node.parent])
    else:
        if node.relname.endswith("_r"):
            return node#.relname
        else:
            return get_nonspan_rel(nodes,nodes[node.parent])


def make_rsd(rstfile, xml_dep_root,as_text=False, docname=None, out_mode="conll"):
    nodes = read_rst(rstfile,{},as_text=as_text)

    # Store any secedge info and remove from nodes
    secedges = []
    keys = [nid for nid in nodes]
    for nid in keys:
        if "-" in nid:
            secedges.append(nodes[nid])
            del nodes[nid]

    out_graph = []
    if rstfile.endswith("rs3"):
        out_file = rstfile.replace(".rs3",".rsd")
    else:
        out_file = rstfile + ".rsd"
    if docname is not None:
        out_file = docname + ".rsd"

    dep_root=xml_dep_root
    if dep_root != "":
        try:
            from .feature_extraction import get_tok_info
        except ImportError:
            from feature_extraction import get_tok_info
        conll_tokens = get_tok_info(ntpath.basename(out_file).replace(".rsd",""),xml_dep_root)
        feats = True
    else:
        feats = False

    # Add tokens to terminal nodes
    if isinstance(nodes,str):
        pass
    edus = list(nodes[nid] for nid in nodes if nodes[nid].kind=="edu")
    edus.sort(key=lambda x: int(x.id))
    token_reached = 0
    for edu in edus:
        if dep_root != "":
            edu.tokens = conll_tokens[token_reached:token_reached+edu.token_count]
            edu.s_type = edu.tokens[0].s_type
            edu.para = edu.tokens[0].para
            edu.item = edu.tokens[0].item
            edu.caption = edu.tokens[0].caption
            edu.heading = edu.tokens[0].heading
            edu.list = edu.tokens[0].list
            if any(tok.date != "_" for tok in edu.tokens):
                edu.date = "date"
            else:
                edu.date = "_"
            start_tok = int(edu.tokens[0].id)
            end_tok = int(edu.tokens[-1].id)
            subord = "_"

            for tok in edu.tokens:
                if int(tok.head) < start_tok and tok.head != "0":
                    subord = "LEFT"
                    tok.head = "0"
                elif int(tok.head) > end_tok and tok.head != "0":
                    subord = "RIGHT"
                    tok.head = "0"

            edu.subord = subord

            edu.genre = "genre"
            for genre_id in GENRES:
                if genre_id in out_file:
                    edu.genre = GENRES[genre_id]
                    break

            token_reached += edu.token_count

    # Get each node with 'span' relation its nearest non-span relname
    for nid in nodes:
        node = nodes[nid]
        new_rel = node.relname
        sigs = []
        if node.parent == "0":
            new_rel = "ROOT"
        elif node.relname == "span" or (nodes[node.parent].kind == "multinuc" and nodes[node.parent].leftmost_child == nid):
            new_rel = get_nonspan_rel(nodes,node)
            if new_rel != "ROOT":
                sigs = new_rel.signals
                new_rel = new_rel.relname
        node.dep_rel = new_rel
        if len(sigs) > 0:
            node.signals = sigs

    for nid in nodes:
        node = nodes[nid]
        dep_parent = find_dep_head(nodes, nid, nid, [])
        if dep_parent is None:
            # This is the root
            dep_parent = "0"
        if node.kind == "edu":
            if dep_parent == "0":
                node.dep_rel = "ROOT"
            node.dep_parent = dep_parent
            out_graph.append(node)

    # Get head EDU and height per node
    node2head_edu = {}
    node2height = {}
    for edu in edus:
        edu.height = 0
        node = edu
        edu_id = edu.id
        node2head_edu[node.id] = edu_id
        while node.parent != "0":
            this_height = node.height + 1
            node = nodes[node.parent]
            if node.kind == "edu":
                edu_id = node.id
            if node.id not in node2head_edu:
                node2head_edu[node.id] = edu_id
                node.height = this_height
            else:
                if int(edu_id) < int(node2head_edu[node.id]):  # Prefer left most child as head
                    node2head_edu[node.id] = edu_id
                    node.height = this_height

    # Get height distance from dependency parent to child's attachment point in the phrase structure (number of spans)
    for nid in nodes:
        node = nodes[nid]
        if node.dep_rel == "ROOT":
            node.dist = "0"
            continue
        if node.kind == "edu":
            parent = nodes[node.dep_parent]
            node.dist = get_distance(node, parent, nodes)

    out_graph.sort(key=lambda x: int(x.id))

    output = []

    for node in out_graph:
        if out_mode == "conll":
            output.append(node.out_conll(feats=feats))
        else:
            output.append(node.out_malt())

    # Insert secedges if any
    src2secedges = collections.defaultdict(set)
    for secedge in secedges:
        dep_src = node2head_edu[nodes[secedge.source].id]
        dep_trg = node2head_edu[nodes[secedge.target].id]
        src_dist = str(nodes[secedge.source].height)
        trg_dist = str(nodes[secedge.target].height)
        signals = []
        for sig in secedge.signals:
            signals.append("-".join([sig.type,sig.subtype,sig.tokens]))
        signals = ";".join(sorted(signals)) if len(signals)>0 else "_"
        src2secedges[dep_src].add(":".join([dep_trg,secedge.relname,src_dist,trg_dist,signals]))

    temp = []
    for i, line in enumerate(output):
        if str(i+1) in src2secedges:
            fields = line.split("\t")
            secstr = "|".join(src2secedges[str(i+1)])
            fields[8] = secstr
            line = "\t".join(fields)
        temp.append(line)

    output = "\n".join(temp) + "\n"

    return output


if __name__ == "__main__":
    desc = "Script to convert Rhetorical Structure Theory trees \n from .rs3 format to a dependency representation.\nExample usage:\n\n" + \
            "python rst2dep.py <INFILES>"
    parser = ArgumentParser(description=desc)
    parser.add_argument("infiles",action="store",help="file name or glob pattern, e.g. *.rs3")
    parser.add_argument("-c","--corpus_root",action="store",dest="root",default="",help="optional: path to corpus root folder containing a directory dep/ and \n"+
                                                           "a directory xml/ containing additional corpus formats")
    parser.add_argument("-p","--print",dest="prnt",action="store_true",help="print output instead of serializing to a file")

    options = parser.parse_args()

    inpath = options.infiles

    if "*" in inpath:
        from glob import glob
        files = glob(inpath)
    else:
        files = [inpath]

    for file_ in files:
        output = make_rsd(file_, options.root)
        if options.prnt:
            print(output)
        else:
            newname = file_.replace("rs3", "rsd").replace("rs4", "rsd")
            if newname == file_:
                newname = file_ + ".rsd"
            with io.open(newname, 'w', encoding="utf8", newline="\n") as f:
                f.write(output)
