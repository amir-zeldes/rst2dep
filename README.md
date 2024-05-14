# RST constituent and dependency conversion

Scripts to convert Rhetorical Structure Theory trees from .rs3 and .rs4 formats to a
dependency representation and back. 

## Installation

Use one of these methods to install the library:

Using pip: 

1. Simply run `> pip install rst2dep`

Alternatively, using python:

1. Download or clone the repo using `git clone https://github.com/amir-zeldes/rst2dep.git`
2. Run `> python setup.py install`

You can also download the scripts and manually run scripts (rst2dep.py, dep2rst.py, etc.), but you won't be able to run it as a module or import easily as shown below.

## Usage

```
usage: python -m rst2dep [-h] [-c ROOT] [-p] [-s] [-a {li,chain,hirao}] [-f {rsd,conllu,rs3,rs4}] [-d {ltr,rtl,dist}] [-r] infiles

positional arguments:
  infiles               file name or glob pattern, e.g. *.rs3

optional arguments:
  -h, --help            show this help message and exit
  -c ROOT, --corpus_root ROOT
                        optional: path to corpus root folder containing a directory dep/ and a directory xml/ containing additional corpus formats
  -p, --print           print output instead of serializing to a file
  -f {rsd,conllu,rs3,rs4}, --format {rsd,conllu,rs3,rs4}
                        input format
  -d {ltr,rtl,dist}, --depth {ltr,rtl,dist}
                        how to order depth
  -r, --rels            use DEFAULT_RELATIONS for the .rs3 header instead of rels in input data
  -a {li,chain,hirao}, --algorithm {li,chain,hirao}
                        dependency head algorithm (default: li)
  -s, --same_unit       retain same-unit multinucs in hirao algorithm / attach them as in li algorithm for chain
  -n, --node_ids        output constituent node IDs in rsd dependency format
```

If you have installed the library you can run the converter directly on the commandline with the options you want like this:

```
python -m rst2dep -p -f rs3 example.rs3
```

You can also import the library in your python scripts:

```Python
from rst2dep import make_rsd, dep2rst, conllu2rsd

conllu = open("example.conllu").read()
rsd =  open("example.rsd").read()
rs3 =  open("example.rs3").read()

rsd_from_conllu = conllu2rsd(conllu)
rs3_from_rsd = rsd2rs3(rsd)
rsd_from_rs3 = make_rsd(rs3,"",as_text=True)
```

More details on the conversions and options are given below.

## Details

### rst2dep

The default conversion follows Li et al.'s (2013) convention of taking the left-most child of multinuclear relations as the head child governed by the relation applied to the whole multinuc, and attaching each subsequent multinuclear child to the first child using the multinuclear relation; thus if a contrast multinuc with units [2-3] is an elaboration on unit [1], the child [2] will become an elaboration dependent of [1], and [3] will become a contrast dependent of child [2]. An alternative algorithm implementing a chain conversion where multinuc children become dependents of their most recent sibling, instead of the leftmost sibling, is also available (use `--algorithm=chain`), as is the Hirao et al. (2014) algorithm (`--algorithm=hirao`), which attaches all multinuc children to the parent of the multinuc, using the relation of the multinuc as a whole. 

For the Hirao et al. algorithm note that no multinuclear relations will be retained in the output, since they will be recursively replaced with whatever satellite relation governs their parent; also note that this means that there could be multiple ROOT nodes (all multinuc children of the document root), and  "same-unit" relations will be destroyed in the same manner. To exceptionally keep same-unit multinucs in the Hirao et al. conversion, use the option `--same_unit`. The same option can be used in the Chain algorithm to exceptionally convert "same-unit" relations according to the Li et al. algorithm (i.e. same-unit children all attach to the leftmost child of the same-unit multinuclear node, but satellites of all other multinuclear node types attach in a chain to the most recent multinuclear child).

By convention, multinuclear relations are converted with relation names ending in `_m`, while satellite RST relations are converted with names ending in `_r`. The original nesting depth is ignored in the conversion, but attachment point height for each dependent is retained in the third column of the output file, allowing deterministic reconstruction of the constituent tree using dep2rst, assuming a projective, hierarchically ordered tree with the Li et al. algorithm (other algorithms are not guaranteed to be reversible). Conversion of non-projective .rs3 constituent trees to dependencies is also supported, but cannot be reversed currently.

Optionally, users can also specify an additional folder containing subfolders `dep/` and `xml/` with .conllu parses and [GUM](https://gucorpling.org/gum/) style XML to add features to the output file. 


### dep2rst

Discourse dependency to RST constituent conversion. The converter assumes target trees are projective and hierarchically ordered. The default strategy for determining constituent nesting order is to look for explicit attachment height encoding as created by rst2dep, otherwise competing nodes are attached as siblings. Alternatively, users can specify `-d rtl` or `-d ltr` to always attach right children below left children, or vice versa.

## Formats 

Supported input formats include .rs3, .rs4 (as used by [rstWeb](https://gucorpling.org/rstweb/info/)), .rsd and .conllu:

### Input format - .rsd

```
1	Greek court rules	0	_	_	_	2	attribution_r	_	_
2	worship of ancient Greek deities is legal	5	_	_	_	5	preparation_r	_	_
3	Monday , March 27 , 2006	4	_	_	_	5	circumstance_r	_	_
4	Greek court has ruled	0	_	_	_	5	attribution_r	_	_
5	that worshippers of the ancient Greek religion may now formally associate and worship at archeological sites .	0	_	_	_	0	ROOT	_	_
6	Prior to the ruling , the religion was banned from conducting public worship at archeological sites by the Greek Ministry of Culture .	1	_	_	_	5	background_r	_	_
7	Due to that , the religion was relatively secretive .	0	_	_	_	6	result_r	_	_
8	The Greek Orthodox Church , a Christian denomination , is extremely critical of worshippers of the ancient deities .	1	_	_	_	6	background_r	_	_
9	Today , about 100,000 Greeks worship the ancient gods , such as Zeus , Hera , Poseidon , Aphrodite , and Athena .	2	_	_	_	5	background_r	_	_
10	The Greek Orthodox Church estimates	0	_	_	_	11	attribution_r	_	_
11	that number is closer to 40,000 .	0	_	_	_	9	concession_r	_	_
12	Many neo - pagan religions , such as Wicca , use aspects of ancient Greek religions in their practice ;	3	_	_	_	5	background_r	_	_
13	Hellenic polytheism instead focuses exclusively on the ancient religions ,	0	_	_	_	12	contrast_m	_	_
14	as far as the fragmentary nature of the surviving source material allows .	0	_	_	_	13	concession_r	_	_
```
### Input format - .conllu
```
# text = Greek court rules worship of ancient Greek deities is legal
1	Greek	Greek	ADJ	JJ	Degree=Pos	2	amod	_	Discourse=attribution:1->2:0
2	court	court	NOUN	NN	Number=Sing	3	nsubj	_	_
3	rules	rule	VERB	VBZ	Mood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin	0	root	_	_
4	worship	worship	NOUN	NN	Number=Sing	10	nsubj	_	Discourse=preparation:2->5:5
5	of	of	ADP	IN	_	8	case	_	_
6	ancient	ancient	ADJ	JJ	Degree=Pos	8	amod	_	_
7	Greek	Greek	ADJ	JJ	Degree=Pos	8	amod	_	_
8	deities	deity	NOUN	NNS	Number=Plur	4	nmod	_	_
9	is	be	AUX	VBZ	Mood=Ind|Number=Sing|Person=3|Tense=Pres|VerbForm=Fin	10	cop	_	_
10	legal	legal	ADJ	JJ	Degree=Pos	3	ccomp	_	_

# text = Monday, March 27, 2006
1	Monday	Monday	PROPN	NNP	Number=Sing	0	root	_	Discourse=circumstance:3->5:4
2	,	,	PUNCT	,	_	4	punct	_	_
3	March	March	PROPN	NNP	Number=Sing	4	compound	_	_
...

```