from .rst2dep import make_rsd
from .dep2rst import rsd2rs3, conllu2rsd
from argparse import ArgumentParser
import sys, os, io

def run_conversion():
    parser = ArgumentParser(usage="python -m rst2dep [-h] [-c ROOT] [-p] [-s] [-a {li,hirao,chain}] [-f {rsd,conllu,rs3,rs4}] [-d {ltr,rtl,dist}] [-r] infiles")
    parser.add_argument("infiles", action="store", help="file name or glob pattern, e.g. *.rs3")
    parser.add_argument("-c", "--corpus_root", action="store", dest="root", default="",
                        help="optional: path to corpus root folder containing a directory dep/ and \n" +
                             "a directory xml/ containing additional corpus formats")
    parser.add_argument("-p", "--print", dest="prnt", action="store_true", help="print output instead of serializing to a file")
    parser.add_argument("-f", "--format", choices=["rsd", "conllu", "rs3", "rs4"], default="rs3", help="input format")
    parser.add_argument("-d", "--depth", choices=["ltr", "rtl", "dist"], default="dist", help="how to order depth")
    parser.add_argument("-r", "--rels", action="store_true", help="use DEFAULT_RELATIONS for the .rs3 header instead of rels in input data")
    parser.add_argument("-a","--algorithm",choices=["li","chain","hirao"],help="dependency head algorithm (default: li)",default="li")
    parser.add_argument("-s","--same_unit",action="store_true",help="retain same-unit multinucs in hirao algorithm / attach them as in li algorithm for chain")
    parser.add_argument("-n","--node_ids",action="store_true",help="output constituent node IDs in rsd dependency format")

    options = parser.parse_args()

    inpath = options.infiles

    if "*" in inpath:
        from glob import glob

        files = glob(inpath)
    else:
        files = [inpath]

    if options.format in ["rs3","rs4"]:
        sys.stderr.write("o Converting from " + options.format + " to rsd format\n")
        for file_ in files:
            sys.stderr.write("Processing " + os.path.basename(file_) + "\n")

            output = make_rsd(file_, options.root, algorithm=options.algorithm, keep_same_unit=options.same_unit, output_const_nid=options.node_ids)
            if options.prnt:
                print(output)
            else:
                newname = file_.replace("rs3", "rsd").replace("rs4", "rsd")
                if newname == file_:
                    newname = file_ + ".rsd"
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
                with open("output" + os.sep + os.path.basename(file_).replace(".rsd",".rs3").replace(".conllu",".rs3"),'w',encoding="utf8",newline="\n") as f:
                    f.write(output)


if __name__ == "__main__":
    run_conversion()
