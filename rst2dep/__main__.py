try:
    from .rst2dep import make_rsd
    from .dep2rst import rsd2rs3, conllu2rsd
    from .rst2rels import rst2conllu, rst2tok, rst2rels
except ImportError:  # Running as a script
    from rst2dep import make_rsd
    from dep2rst import rsd2rs3, conllu2rsd
    from rst2rels import rst2conllu, rst2tok, rst2rels

from argparse import ArgumentParser
import sys, os, io, re

def run_conversion():
    parser = ArgumentParser(usage="python -m rst2dep [-h] [-l] [-c ROOT] [-p] [-s] [-a {li,hirao,chain}] [-f {rsd,conllu,rs3,rs4}] [-o {rsd,conllu,tok,rels}] [-d {ltr,rtl,dist}] [-r] infiles")
    parser.add_argument("infiles", action="store", help="file name or glob pattern, e.g. *.rs3")
    parser.add_argument("-l", "--language_code", action="store", default="en",
                        help="stanza language code for language of data being processed")
    parser.add_argument("-c", "--corpus_root", action="store", dest="root", default="",
                        help="optional: path to corpus root folder containing a directory dep/ and \n" +
                             "a directory xml/ containing additional corpus formats")
    parser.add_argument("-p", "--print", dest="prnt", action="store_true", help="print output instead of serializing to a file")
    parser.add_argument("-f", "--format", choices=["rsd", "conllu", "rs3", "rs4"], default="rs3", help="input format")
    parser.add_argument("-o", "--output_format", choices=["rsd", "conllu", "tok", "rels"], default="rsd", help="output format (applies for rs3 or rs4 input)")
    parser.add_argument("-d", "--depth", choices=["ltr", "rtl", "dist"], default="dist", help="how to order depth")
    parser.add_argument("-r", "--rels", action="store_true", help="use DEFAULT_RELATIONS for the .rs3 header instead of rels in input data")
    parser.add_argument("-a","--algorithm",choices=["li","chain","hirao"],help="dependency head algorithm (default: li)",default="li")
    parser.add_argument("-s","--same_unit",action="store_true",help="retain same-unit multinucs in hirao algorithm / attach them as in li algorithm for chain")
    parser.add_argument("-n","--node_ids",action="store_true",help="output constituent node IDs in rsd dependency format")
    parser.add_argument("-w","--whitespace_tokenize",action="store_true",help="use whitespace tokenization in conllu (default: False - use stanza tokenizer)")
    parser.add_argument("--outdir", action="store", default=None, help="output directory for serialized files (default: input file directory)")

    options = parser.parse_args()

    inpath = options.infiles

    if "*" in inpath:
        from glob import glob

        files = glob(inpath)
    else:
        files = [inpath]

    if options.format in ["rs3","rs4"]:
        sys.stderr.write("o Converting from " + options.format + " to " + options.output_format + " format\n")
        for file_ in files:
            sys.stderr.write("Processing " + os.path.basename(file_) + "\n")

            rst = open(file_).read()
            plain_docname = re.sub(r'[\s/\\]','', os.path.basename(file_).rsplit(".",1)[0].replace("rs3", "").replace("rs4", ""))

            if options.output_format == "rels":
                output = rst2rels(rst, docname=plain_docname, lang_code=options.language_code, whitespace_tokenize=options.whitespace_tokenize)
            elif options.output_format == "tok":
                output = rst2tok(rst, docname=plain_docname, lang_code=options.language_code, whitespace_tokenize=options.whitespace_tokenize)
            elif options.output_format == "conllu":
                output = rst2conllu(rst, docname=plain_docname, lang_code=options.language_code, whitespace_tokenize=options.whitespace_tokenize)
            else:
                output = make_rsd(file_, options.root, algorithm=options.algorithm, keep_same_unit=options.same_unit, output_const_nid=options.node_ids)
            if options.prnt:
                print(output)
            else:
                if options.outdir:
                    outdir = options.outdir
                    newname = os.path.join(outdir, os.path.basename(file_).replace("rs3", options.output_format).replace("rs4", options.output_format))
                else:
                   newname = file_.replace("rs3", options.output_format).replace("rs4", options.output_format)
                if newname == file_:
                    newname = file_ + "." + options.output_format
                with io.open(newname, 'w', encoding="utf8", newline="\n") as f:
                    f.write(output)
    else:
        sys.stderr.write("o Converting from " + options.format + " to XML format\n")
        for file_ in files:
            sys.stderr.write("Processing " + os.path.basename(file_) + "\n")

            data = io.open(file_,encoding="utf8").read()

            if options.format == "conllu":
                data = conllu2rsd(data)

            output = rsd2rs3(data, ordering=options.depth)

            if options.prnt:
                print(output)
            else:
                if options.outdir:
                    outdir = options.outdir
                else:
                    outdir = os.path.dirname(file_)
                with open(outdir + os.sep + os.path.basename(file_).replace(".rsd",".rs3").replace(".conllu",".rs3"),'w',encoding="utf8",newline="\n") as f:
                    f.write(output)


if __name__ == "__main__":
    run_conversion()
