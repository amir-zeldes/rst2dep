try:
	from .rst2dep import make_rsd
except:
	from rst2dep import make_rsd
from stanza.utils.conll import CoNLL
from collections import defaultdict
from argparse import ArgumentParser
import stanza
import re

stanza_tokenizer = None
nlp = None
stanza_tokenizer_no_ssplit = None

rel_mapping = defaultdict(dict)
rel_mapping["eng.rst.rstdt"] = {"attribution":"attribution","attribution-e":"attribution","attribution-n":"attribution","attribution-negative":"attribution","background":"background","background-e":"background","circumstance":"background","circumstance-e":"background","cause":"cause","cause-result":"cause","result":"cause","result-e":"cause","consequence":"cause","consequence-n-e":"cause","consequence-n":"cause","consequence-s-e":"cause","consequence-s":"cause","comparison":"comparison","comparison-e":"comparison","preference":"comparison","preference-e":"comparison","analogy":"comparison","analogy-e":"comparison","proportion":"comparison","condition":"condition","condition-e":"condition","hypothetical":"condition","contingency":"condition","otherwise":"condition","contrast":"contrast","concession":"contrast","concession-e":"contrast","antithesis":"contrast","antithesis-e":"contrast","elaboration-additional":"elaboration","elaboration-additional-e":"elaboration","elaboration-general-specific-e":"elaboration","elaboration-general-specific":"elaboration","elaboration-part-whole":"elaboration","elaboration-part-whole-e":"elaboration","elaboration-process-step":"elaboration","elaboration-process-step-e":"elaboration","elaboration-object-attribute-e":"elaboration","elaboration-object-attribute":"elaboration","elaboration-set-member":"elaboration","elaboration-set-member-e":"elaboration","example":"elaboration","example-e":"elaboration","definition":"elaboration","definition-e":"elaboration","purpose":"enablement","purpose-e":"enablement","enablement":"enablement","enablement-e":"enablement","evaluation":"evaluation","evaluation-n":"evaluation","evaluation-s-e":"evaluation","evaluation-s":"evaluation","interpretation-n":"evaluation","interpretation-s-e":"evaluation","interpretation-s":"evaluation","interpretation":"evaluation","conclusion":"evaluation","comment":"evaluation","comment-e":"evaluation","evidence":"explanation","evidence-e":"explanation","explanation-argumentative":"explanation","explanation-argumentative-e":"explanation","reason":"explanation","reason-e":"explanation","list":"joint","disjunction":"joint","manner":"manner-means","manner-e":"manner-means","means":"manner-means","means-e":"manner-means","problem-solution":"topic-comment","problem-solution-n":"topic-comment","problem-solution-s":"topic-comment","question-answer":"topic-comment","question-answer-n":"topic-comment","question-answer-s":"topic-comment","statement-response":"topic-comment","statement-response-n":"topic-comment","statement-response-s":"topic-comment","topic-comment":"topic-comment","comment-topic":"topic-comment","rhetorical-question":"topic-comment","summary":"summary","summary-n":"summary","summary-s":"summary","restatement":"summary","restatement-e":"summary","temporal-before":"temporal","temporal-before-e":"temporal","temporal-after":"temporal","temporal-after-e":"temporal","temporal-same-time":"temporal","temporal-same-time-e":"temporal","sequence":"temporal","inverted-sequence":"temporal","topic-shift":"topic-change","topic-drift":"topic-change","textualorganization":"textual-organization"}
ellipsis_marker = "<*>"

def format_range(tok_ids):
	# Takes a list of IDs and returns formatted string:
	# contiguous subranges of numbers are separated by '-', e.g. 5-24
	# discontinuous subranges are separated by ',', e.g. 2,5-24
	def format_subrange(subrange):
		if len(subrange) == 1:
			return str(subrange[0]+1)
		else:
			return str(min(subrange)+1) + "-" + str(max(subrange)+1)

	subranges = [[]]
	last = None
	for tid in sorted(tok_ids):
		if last is None:
			subranges[-1].append(tid)
		elif tid == last +1:
			subranges[-1].append(tid)
		else:
			subranges.append([tid])
		last = tid

	formatted = []
	for subrange in subranges:
		formatted.append(format_subrange(subrange))

	return ",".join(formatted)


def format_text(arg1_toks, toks, mwts=None):
	last = arg1_toks[0] - 1
	output = []
	for tid in sorted(arg1_toks):
		if tid != last + 1:
			output.append(ellipsis_marker)
		output.append(toks[tid])
		last = tid
	output = " ".join(output)
	if mwts is not None:  # remove space after MWT internal tokens
		tok_strings = output.split()
		output = ""
		idx = 0
		for tok in tok_strings:
			if tok == "<*>":
				output += "<*> "
			else:
				output += tok
				argtok = arg1_toks[idx]
				is_in_mwt = False
				if argtok in mwts:
					is_in_mwt = mwts[argtok]
				if not is_in_mwt:
					output += " "
				idx += 1
	return output.strip()


def format_sent(arg1_sid, sents):
	sent = sents[arg1_sid]
	lines = sent.split("\n")
	output = []
	for line in lines:
		if "\t" in line:
			fields = line.split("\t")
			if "." in fields[0] or "-" in fields[0]:  # supertok or ellipsis token
				continue
			output.append(fields[1])
	return " ".join(output)


def make_rels(rsd_str, conll_str, docname, corpus="eng.erst.gum", include_secedges=True, outmode="standoff",
			  coarse_rels=False, dedup=True):
	if outmode == "standoff":
		header = ["doc", "unit1_toks", "unit2_toks", "unit1_txt", "unit2_txt", "s1_toks", "s2_toks", "unit1_sent",
				  "unit2_sent", "dir", "orig_label", "label"]
	elif outmode == "standoff_reltype":
		header = ["doc", "unit1_toks", "unit2_toks", "unit1_txt", "unit2_txt", "u1_raw", "u2_raw", "s1_toks", "s2_toks", "unit1_sent",
					"unit2_sent", "dir", "rel_type", "orig_label", "label"]
	elif outmode == "standoff_key":
		header = ["doc", "unit1_toks", "unit2_toks", "unit1_txt", "unit2_txt", "s1_toks", "s2_toks", "unit1_sent",
				  "unit2_sent", "dir", "rel_key", "label"]
	else:
		header = ["doc", "start_toks", "pre", "arg1", "mid", "arg2", "post", "dir", "label"]

	seen_keys = set([])

	sent_map = {}
	toks = {}
	sents = conll_str.split("\n\n")

	snum = 0
	toknum = 0
	s_starts = {}
	s_ends = {}
	mwts = {}  # Track MWT internal tokens (excluding last)

	for sent in sents:
		lines = sent.split("\n")
		for line in lines:
			if "\t" in line:
				fields = line.split("\t")
				if toknum not in mwts:
					mwts[toknum] = False
				if "-" in fields[0] or "." in fields[0]:
					if "-" in fields[0]:
						start, end = fields[0].split("-")
						length = int(end) - int(start)
						for i in range(length):
							mwts[toknum+i] = True
					continue
				if fields[0] == "1":
					s_starts[snum] = toknum
				sent_map[toknum] = snum
				toks[toknum] = fields[1]
				toknum += 1
		s_ends[snum] = toknum - 1
		snum += 1

	rsd_lines = rsd_str.split("\n")

	parents = defaultdict(list)
	texts = {}
	tok_map = {}
	offset = 0
	rels = defaultdict(list)
	rel_sigtypes = defaultdict(list)
	for line in rsd_lines:
		if "\t" in line:
			fields = line.split("\t")
			edu_id = fields[0]
			edu_parent = fields[6]
			relname = fields[7].replace("_m","").replace("_r","")
			text = fields[1].strip()
			texts[edu_id] = text
			tok_map[edu_id] = (offset, offset + len(text.split())-1)
			offset += len(text.split())
			if edu_parent == "0":  # Ignore root
				continue
			parents[edu_id].append(edu_parent)
			rels[edu_id].append(relname)
			if 'dm-' in fields[-1]:
				rel_sigtypes[edu_id].append("explicit")
			else:
				rel_sigtypes[edu_id].append("implicit")
			if fields[8] != "_" and include_secedges:
				secedges = fields[8].split("|")
				for edge in secedges:
					sec_parent, sec_rel = edge.split(":")[:2]
					parents[edu_id].append(sec_parent)
					rels[edu_id].append(sec_rel)
					if "orphan-" in edge:
						rel_sigtypes[edu_id].append("explicit")  # orphan DM secedge
					else:
						rel_sigtypes[edu_id].append("implicit")  # e.g. syntactic secedge

	# reattach all children of a parent which is itself same-unit to that parent's primary parent
	for edu_id in parents:
		for i, parent in enumerate(parents[edu_id]):
			if parent in parents:
				if any([r.lower().startswith("same") for r in rels[parent]]):
					parents[edu_id][i] = parents[parent][0]

	same_unit_components = defaultdict(set)
	same_unit_data = {}
	# set up same-unit storage
	for edu_id in parents:
		if rels[edu_id][0].lower().startswith("same"):
			# collect all intervening text inside same-unit children
			parent = parents[edu_id][0]
			start = int(parent)
			end = int(edu_id)
			unit_ids = [str(x) for x in range(start,end+1)]
			same_unit_components[parent].add(edu_id)
			if parent not in same_unit_data:
				same_unit_data[parent] = (start,end," ".join([texts[t].strip() for t in unit_ids]))
			else:
				start, end, text = same_unit_data[parent]
				if int(edu_id) > start:  # This is a subsequent same-unit member on the right
					unit_ids = [str(x) for x in range(end+1,int(edu_id)+1)]
					more_text = " ".join([texts[t].strip() for t in unit_ids])
					same_unit_data[parent] = (start,int(edu_id)," ".join([text,more_text]))
				else:
					raise IOError("LTR same unit!\n")

	output = ["\t".join(header)]
	for edu_id in parents:
		for i, parent_id in enumerate(parents[edu_id]):
			rel = rels[edu_id][i]
			rel_type = rel_sigtypes[edu_id][i]
			rel_key = edu_id + "-" + parent_id + "-" + rel
			if rel.lower().startswith("same"):
				continue  # Skip the actual same-unit relation
			child_text = texts[edu_id]
			if int(edu_id) < int(parent_id):
				direction = "1>2"
				arg1_start, arg1_end = tok_map[edu_id]
				arg2_start, arg2_end = tok_map[parent_id]
			else:
				direction = "1<2"
				arg1_start, arg1_end = tok_map[parent_id]
				arg2_start, arg2_end = tok_map[edu_id]

			parent_text = texts[parent_id]
			if parent_id in same_unit_data:
				start, end, text = same_unit_data[parent_id]
				if int(edu_id) < start or int(edu_id)> end:
					parent_text = text
					if int(edu_id) < int(parent_id):
						arg2_start, _ = tok_map[str(start)]
						_, arg2_end = tok_map[str(end)]
					else:
						arg1_start, _ = tok_map[str(start)]
						_, arg1_end = tok_map[str(end)]

			if edu_id in same_unit_data:
				start, end, text = same_unit_data[edu_id]
				if int(parent_id) < start or int(parent_id)> end:
					child_text = text
					if int(edu_id) < int(parent_id):
						arg1_start, _ = tok_map[str(start)]
						_, arg1_end = tok_map[str(end)]
					else:
						arg2_start, _ = tok_map[str(start)]
						_, arg2_end = tok_map[str(end)]

			arg1_sid = sent_map[arg1_start]
			arg2_sid = sent_map[arg2_start]

			s1_start = s_starts[arg1_sid]
			s1_end = s_ends[arg1_sid]
			s2_start = s_starts[arg2_sid]
			s2_end = s_ends[arg2_sid]

			pre = []
			pre_toks = []
			arg1 = []
			arg1_toks = []
			mid = []
			mid_toks = []
			arg2 = []
			arg2_toks = []
			post = []
			post_toks = []
			for i in sorted(list(set(list(range(s1_start,s1_end+1)) + list(range(s2_start, s2_end+1))))):
				tok = toks[i]
				if i < arg1_start:
					pre.append(tok)
					pre_toks.append(i)
				elif i >= arg2_start and i <= arg2_end:
					arg2.append(tok)
					arg2_toks.append(i)
				elif i >= arg1_start and i <= arg1_end:
					arg1.append(tok)
					arg1_toks.append(i)
				elif i > arg1_end and i < arg2_start:
					mid.append(tok)
					mid_toks.append(i)
				else:
					post.append(tok)
					post_toks.append(i)

			if outmode.startswith("standoff"):
				comp1 = edu_id if int(edu_id) < int(parent_id) else parent_id
				comp2 = parent_id if int(edu_id) < int(parent_id) else edu_id
				# Reduce EDUs to minimal span in standoff mode
				arg1_toks = list(range(tok_map[comp1][0], tok_map[comp1][1]+1))
				arg2_toks = list(range(tok_map[comp2][0], tok_map[comp2][1]+1))
				# Add explicit discontinuous spans
				if comp1 in same_unit_components:
					for component in same_unit_components[comp1]:
						component_toks = list(range(tok_map[component][0], tok_map[component][1]+1))
						arg1_toks += component_toks
				if comp2 in same_unit_components:
					for component in same_unit_components[comp2]:
						component_toks = list(range(tok_map[component][0], tok_map[component][1]+1))
						arg2_toks += component_toks
				arg1_txt = format_text(arg1_toks,toks)
				arg1_raw_txt = format_text(arg1_toks,toks,mwts)
				arg1_sent = format_sent(arg1_sid,sents)
				arg2_txt = format_text(arg2_toks,toks)
				arg2_raw_txt = format_text(arg2_toks,toks,mwts)
				arg2_sent = format_sent(arg2_sid,sents)
				arg1_toks = format_range(arg1_toks)
				arg2_toks = format_range(arg2_toks)
				s1_toks = format_range(list(range(s1_start,s1_end+1)))
				s2_toks = format_range(list(range(s2_start,s2_end+1)))

				mapped_rel = rel
				if corpus in rel_mapping:
					if mapped_rel in rel_mapping[corpus]:
						mapped_rel = rel_mapping[corpus][mapped_rel]
					elif mapped_rel.lower() in rel_mapping[corpus]:
						mapped_rel = rel_mapping[corpus][mapped_rel.lower()]
					else:
						if mapped_rel!="ROOT":
							raise IOError("no rel map "+mapped_rel)
						elif mapped_rel == "ROOT":
							raise IOError("found ROOT entry in " +corpus + ": "+docname)
				elif "-" in mapped_rel and "same-unit" not in mapped_rel.lower():
					mapped_rel = mapped_rel.split("-")[0]
				if corpus.startswith("fas."):
					mapped_rel = mapped_rel.lower()
				if not coarse_rels:
					mapped_rel = rel
				disrpt_key = docname + "-" + arg1_toks + "-" + arg2_toks
				if dedup and disrpt_key in seen_keys:
					continue
				else:
					seen_keys.add(disrpt_key)
				if outmode == "standoff_key":
					output.append("\t".join([docname, arg1_toks, arg2_toks, arg1_txt, arg2_txt, s1_toks, s2_toks, arg1_sent, arg2_sent, direction, rel_key, mapped_rel]))
				elif outmode == "standoff_reltype":
					output.append("\t".join([docname, arg1_toks, arg2_toks, arg1_txt, arg2_txt, arg1_raw_txt, arg2_raw_txt, s1_toks, s2_toks, arg1_sent, arg2_sent, direction, rel_type, rel, mapped_rel]))
				else:
					output.append("\t".join([docname,arg1_toks,arg2_toks,arg1_txt,arg2_txt,s1_toks,s2_toks,arg1_sent,arg2_sent,direction,rel,mapped_rel]))
			else:
				pre = " ".join(pre) if len(pre) > 0 else "NULL"
				pre_toks = str(min(pre_toks)) if len(pre_toks) > 0 else "NA"
				arg1 = " ".join(arg1)
				arg1_toks = str(min(arg1_toks))
				mid = " ".join(mid) if len(mid) > 0 else "NULL"
				mid_toks = str(min(mid_toks)) if len(mid_toks) > 0 else "NA"
				arg2 = " ".join(arg2)
				arg2_toks = str(min(arg2_toks))
				post = " ".join(post) if len(post) > 0 else "NULL"
				post_toks = str(min(post_toks)) if len(post_toks) > 0 else "NA"

				indices = ";".join([pre_toks, arg1_toks, mid_toks, arg2_toks, post_toks])
				output.append("\t".join([docname,indices,pre,arg1,mid,arg2,post,direction,rel]))

	return output


def get_ssplit(rsd, lang_code="en"):

	# Creates edu list and document string
	edu_list = []
	document_string = ""
	rsd_lines = rsd.split("\n")
	for rsd_line in rsd_lines:
		if "\t" in rsd_line:
			fields = rsd_line.split("\t")
			current_edu = fields[1]
			edu_list.append(current_edu)
			document_string += current_edu + " "
	document_string = document_string[:-1]

	# Use stanza to make the conllu from rs3/rsd
	global stanza_tokenizer
	if stanza_tokenizer is None:
		try:
			stanza_tokenizer = stanza.Pipeline(lang_code, processors='tokenize')
		except:
			stanza.download(lang_code)  # download model
			stanza_tokenizer = stanza.Pipeline(lang_code, processors='tokenize')

	tokenized_document = stanza_tokenizer(document_string)

	# Check that sentence splits do not split any edus
	merged_sentences = []
	i = 0
	while i < len(tokenized_document.sentences):
		sentence = tokenized_document.sentences[i].text
		
		# Check if this sentence and the next one split a clause
		if i + 1 < len(tokenized_document.sentences):
			combined = sentence + " " + tokenized_document.sentences[i + 1].text
			for edu in edu_list:
				if (edu in combined) and (edu not in sentence) and (edu not in tokenized_document.sentences[i + 1].text):
					# Merge sentences
					sentence = combined
					i += 1  # Skip the next sentence
					break
		
		merged_sentences.append(sentence)
		i += 1

	return merged_sentences, edu_list


def rst2conllu(rst, lang_code="en"):

	rsd_from_rst = make_rsd(rst,"", as_text=True, algorithm="chain")

	merged_sentences, edu_list = get_ssplit(rsd_from_rst, lang_code=lang_code)

	global nlp
	if nlp is None:
		nlp = stanza.Pipeline(lang_code, processors='tokenize,mwt,pos,lemma,depparse', tokenize_no_ssplit=True)

	proccessed_document = nlp(merged_sentences)

	# returnable object
	dicts = proccessed_document.to_dict()
	for sent in dicts:
		for token_dict in sent:
			del token_dict["start_char"]
			del token_dict["end_char"]
	conll = CoNLL.convert_dict(dicts)

	# make conll into string
	sentence_strings = []
	seg_begin = True
	current_edu_index = 0
	current_edu = ""
	for sentence in conll:
		token_lines = []
		for token in sentence:
			if "-" not in token[0]:
				if seg_begin:
					if token[9] == "_":
						token[9] = "BeginSeg=Yes"
					else:
						# add BeginSeg=Yes alphabetically
						misc_segments = token[9].split("|")
						misc_segments.append("BeginSeg=Yes")
						misc_segments.sort()
						token[9] = "|".join(misc_segments)
					current_edu = re.sub(r'\s', "", edu_list[current_edu_index])
					current_edu = current_edu[len(token[1]):]
					seg_begin = False
				else:
					current_edu = current_edu[len(token[1]):]
					if current_edu == "":
						# if we've reached the end of the edu
						seg_begin = True
						current_edu_index += 1
			token_line = "\t".join(token)
			token_lines.append(token_line)
		sentence_string = "\n".join(token_lines)
		sentence_strings.append(sentence_string)
	conll_str = "\n\n".join(sentence_strings) # conll format string
	conll_str += "\n\n"
	return conll_str


def rst2tok(rst, lang_code="en"):

	rsd_from_rst = make_rsd(rst,"", as_text=True, algorithm="chain")

	merged_sentences, edu_list = get_ssplit(rsd_from_rst, lang_code=lang_code)

	global stanza_tokenizer_no_ssplit
	if stanza_tokenizer_no_ssplit is None:
		stanza_tokenizer_no_ssplit = stanza.Pipeline(lang_code, processors='tokenize,mwt',
													 tokenize_no_ssplit=True)
	proccessed_document = stanza_tokenizer_no_ssplit(merged_sentences)

	# make the tok format
	tok_format = []
	seg_begin = True
	current_edu_index = 0
	current_edu = ""
	token_index_count = 1
	for sentence in proccessed_document.sentences:
		for token in sentence.tokens:
			for word in token.words:
				if type(word.id) is list:
					# skip supertokens
					continue
				if seg_begin:
					tok_format.append(str(token_index_count) + "\t" + word.text +"\t_\t_\t_\t_\t_\t_\t_\tBeginSeg=Yes")
					current_edu = re.sub(r'\s', "", edu_list[current_edu_index])
					current_edu = current_edu[len(word.text):]
					seg_begin = False
				else:
					tok_format.append(str(token_index_count) + "\t" + word.text +"\t_\t_\t_\t_\t_\t_\t_\t_")
					current_edu = current_edu[len(word.text):]
					if current_edu == "":
					# if we've reached the end of the edu
						seg_begin = True
						current_edu_index += 1
				token_index_count += 1
	tok_str = "\n".join(tok_format) # tok format string
	return tok_str


def rst2rels(rst, docname="document", lang_code="en"):

	rsd_from_rst = make_rsd(rst,"", as_text=True, algorithm="chain")
	conll_str = rst2conllu(rst, lang_code=lang_code)
	rels_format = make_rels(rsd_from_rst, conll_str, docname, outmode="standoff_reltype")
	rels_str = "\n".join(rels_format) # rels format string

	return rels_str

if __name__ == "__main__":
	desc = "Script to convert Rhetorical Structure Theory trees \n in the .rs3 format to the disrpt .rels format, .tok format, and .conllu format.\nExample usage:\n\n" + "python rst2rels.py <INFILES>"
	parser = ArgumentParser(description=desc)
	parser.add_argument("infiles",action="store",help="file name or glob pattern, e.g. *.rs3")
	parser.add_argument("-l", "--language_code", action="store", default="en", help="stanza language code for language of data being processed")
	parser.add_argument("-p","--print",dest="prnt",action="store_true",help="print output instead of serializing to a file")
	parser.add_argument("-r","--rels",action="store_true",help="generate disrpt .rels format")
	parser.add_argument("-t","--tok",action="store_true",help="generate .tok format")
	parser.add_argument("-c","--conllu",action="store_true",help="generate .conllu format")
	options = parser.parse_args()
	inpath = options.infiles

	if "*" in inpath:
		from glob import glob
		files = glob(inpath)
	else:
		files = [inpath]

	for file_ in files:
		input_docname = file_.split("/")[-1].split(".")[0]
		print("Processing: " + input_docname)
		rst = open(file_).read()
		rels, tok, conllu = "", "", ""
		if options.rels:
			rels = rst2rels(rst, docname=input_docname, lang_code=options.language_code)
		if options.tok:
			tok = rst2tok(rst, lang_code=options.language_code)
		if options.conllu:
			conllu = rst2conllu(rst, lang_code=options.language_code)
		
		if options.prnt:
			if options.rels:
				print(rels)
			if options.tok:
				print(tok)
			if options.conllu:
				print(conllu)
		else:
			if options.rels:
				rels_name = file_.replace("rs3", "rels").replace("rs4", "rels")
				with open(rels_name, 'w', encoding="utf8", newline="\n") as f:
					f.write(rels)
			if options.tok:
				tok_name = file_.replace("rs3", "tok").replace("rs4", "tok")
				with open(tok_name, 'w', encoding="utf8", newline="\n") as f:
					f.write(tok)
			if options.conllu:
				conllu_name = file_.replace("rs3", "conllu").replace("rs4", "conllu")
				with open(conllu_name, 'w', encoding="utf8", newline="\n") as f:
					f.write(conllu)
