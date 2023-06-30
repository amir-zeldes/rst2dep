from rst2dep import make_rsd
from dep2rst import rsd2rs3, conllu2rsd
import io

rsd = io.open("example.rsd",encoding="utf8").read()
conllu = io.open("example.conllu",encoding="utf8").read()
rsd_b = conllu2rsd(conllu)
rs3 = rsd2rs3(rsd)
rsd_c = make_rsd(rs3,"",as_text=True)
rs3_b = io.open("example.rs3",encoding="utf8").read()

assert(rs3 == rs3_b)
print("o rs3 conversion success")
assert(rsd == rsd_b)
print("o conllu conversion success")
assert(rsd == rsd_c)
print("o rsd conversion success")
