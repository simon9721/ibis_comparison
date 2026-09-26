import sys, zipfile, posixpath
from xml.dom import minidom
sys.stdout.reconfigure(encoding="utf-8")
z = zipfile.ZipFile(sys.argv[1])
rd = lambda n: z.read(n).decode("utf-8")
def rels(part):
    d, b = posixpath.split(part)
    rp = f"{d}/_rels/{b}.rels"
    if rp not in z.namelist(): return {}
    out = {}
    for r in minidom.parseString(rd(rp)).getElementsByTagName("Relationship"):
        out[r.getAttribute("Id")] = (r.getAttribute("Type").split("/")[-1], posixpath.normpath(posixpath.join(d, r.getAttribute("Target"))))
    return out
authors = {a.getAttribute("id"): a.getAttribute("name") for a in minidom.parseString(rd("ppt/authors.xml")).getElementsByTagName("p188:author")}
pres = minidom.parseString(rd("ppt/presentation.xml")); prels = rels("ppt/presentation.xml")
order = [prels[s.getAttribute("r:id")][1] for s in pres.getElementsByTagName("p:sldId")]
def text_of(node): return "".join(t.firstChild.data if t.firstChild else "" for t in node.getElementsByTagName("a:t"))
for i, sp in enumerate(order, 1):
    doc = minidom.parseString(rd(sp))
    shapes = {el.getAttribute("id"): el.getAttribute("name") for el in doc.getElementsByTagName("p:cNvPr")}
    r = rels(sp)
    print(f"\n=== slide {i}  ({sp.split('/')[-1]})")
    for spn in doc.getElementsByTagName("p:sp"):
        paras = [p for p in (text_of(p) for p in spn.getElementsByTagName("a:p")) if p.strip()]
        if paras:
            nm = spn.getElementsByTagName("p:cNvPr")[0]
            print(f"   [{nm.getAttribute('id')}:{nm.getAttribute('name')}] " + " | ".join(paras))
    for p in doc.getElementsByTagName("p:pic"):
        nm = p.getElementsByTagName("p:cNvPr")[0]
        emb = p.getElementsByTagName("a:blip")
        tgt = r.get(emb[0].getAttribute("r:embed"), ("", ""))[1] if emb else ""
        print(f"   [pic {nm.getAttribute('id')}:{nm.getAttribute('name')}] {tgt}")
    for rid, (typ, tgt) in r.items():
        if "comment" in typ.lower():
            cd = minidom.parseString(rd(tgt))
            for cm in cd.getElementsByTagName("p188:cm"):
                who = authors.get(cm.getAttribute("authorId"), cm.getAttribute("authorId"))
                body = cm.getElementsByTagName("p188:txBody")
                txt = " / ".join(text_of(p) for p in body[0].getElementsByTagName("a:p")) if body else ""
                anc = [m.getAttribute("id") for m in cm.getElementsByTagName("ac:spMk")] + [m.getAttribute("id") for m in cm.getElementsByTagName("ac:picMk")]
                anc_s = ", ".join(f"{a}:{shapes.get(a, '?')}" for a in anc) or "the slide"
                print(f"   >>> COMMENT ({who}) on {anc_s}: {txt}")
                for rp in cm.getElementsByTagName("p188:reply"):
                    rb = rp.getElementsByTagName("p188:txBody")
                    print(f"       reply ({authors.get(rp.getAttribute('authorId'))}): " + (" / ".join(text_of(p) for p in rb[0].getElementsByTagName('a:p')) if rb else ""))
