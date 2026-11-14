#!/usr/bin/env python3
"""fetch_external.py - download the external ontologies used as negative controls.

The files are NOT redistributed here: each is fetched from a commit-pinned URL of
its own public repository and checked against a SHA-256 digest recorded below, so
a reader obtains the bytes the audit was run on, under each project's own licence.

Usage: python3 fetch_external.py [target directory, default ../external]
"""
import hashlib, sys, urllib.request
from pathlib import Path

RAW = 'https://raw.githubusercontent.com/'
EXTERNAL = [
    # name, repository@commit/path, namespace of the ontology's own terms, sha256
    ('pizza',  'owlcs/pizza-ontology/4922ecbdf5535a00a6515276324c3aa7f5e4407a/pizza.owl',
     'http://www.co-ode.org/ontologies/pizza/pizza.owl#', '0de2cd4df0bc09dfd9403df46ae7aa9d26ec31c32cc9a59c514f459c312a751c'),
    ('koala',  'owlcs/owlapi/dee53400f3da0fe009bd50af1285b28095fa5178/contract/src/test/resources/koala.owl',
     'http://protege.stanford.edu/plugins/owl/owl-library/koala.owl#', '81add809c95c37045fa91c0f4477851dcd787ab443cabb8c8a10b6f18ef2785b'),
    ('primer', 'owlcs/owlapi/dee53400f3da0fe009bd50af1285b28095fa5178/contract/src/test/resources/primer.rdfxml.xml',
     'http://example.com/owl/families/', 'ecb69210f776f0df343f440137217f10fa66090dea7dda671bf849d432a29d4f'),
    ('sosa',   'w3c/sdw/f3171647f6437b73e1caf871f056d233feb4a9da/ssn/integrated/sosa.ttl',
     'http://www.w3.org/ns/sosa/', 'c70b0d1c843c0047e4c98e0a89392e46a05752ff6365bda7f7f55303905a0392'),
    ('ssn',    'w3c/sdw/f3171647f6437b73e1caf871f056d233feb4a9da/ssn/integrated/ssn.ttl',
     'http://www.w3.org/ns/ssn/', '184d86189191146e314cc52b1bceb96fca11e70aacbc160d71588102a5153eb9'),
    ('bfo',    'BFO-ontology/BFO/857be9f15100531c7202ef0eb73142f95b70f3a7/bfo.owl',
     'http://purl.obolibrary.org/obo/', '20f96780a3459effeb7d441acae2717d89225b002aa52ed6940ccfd781352b1d'),
    ('iao',    'information-artifact-ontology/IAO/3006aedacbf813ffd1d2ac15cda10766ca9ed388/iao.owl',
     'http://purl.obolibrary.org/obo/', 'c27ff2964a2ad8165bc365698b628aae95108411384aa4450e6e1b1e82bf0f41'),
    ('educor', 'tibonto/educor/76a08b44d54ddfab1e7fcd9fb6ec92b0f3174683/educor.ttl',
     'https://github.com/tibonto/educor#', 'd846d19cfb57e5faa5f245406b9be44b56afcc504380765baaf5c351c8cae585'),
    ('doap',   'ewilderj/doap/a0683cbd8b18cfc23963615d3df7f79d9640d7c3/schema/doap.rdf',
     'http://usefulinc.com/ns/doap#', 'ac0ee7a1f393dcd91e3063f75e977d785dd8fb07684ad0042cf5dd5ded14497a'),
    ('ecrm',   'erlangen-crm/ecrm/8f44be0426f60a48fa4a4b39007c43f0ef1eb464/ecrm_current.owl',
     'http://erlangen-crm.org/current/', 'ef6d47e63684929e5a4ae57b6d170d196dbf64ff2a14fca59c6fa9d228184f04'),
]


def path_of(name, target):
    src = next(e for e in EXTERNAL if e[0] == name)[1]
    return Path(target) / (name + Path(src).suffix.replace('.xml', '.owl').replace('.rdf', '.owl'))


def main(target):
    target = Path(target)
    target.mkdir(parents=True, exist_ok=True)
    for name, src, ns, digest in EXTERNAL:
        p = path_of(name, target)
        if not p.exists():
            with urllib.request.urlopen(RAW + src) as r:
                p.write_bytes(r.read())
        got = hashlib.sha256(p.read_bytes()).hexdigest()
        status = 'ok' if digest == got else ('UNPINNED' if digest is None else 'DIGEST MISMATCH')
        print(f'{status:16s} {got}  {name:7s} {RAW + src}')
        if digest is not None and digest != got:
            sys.exit(1)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else Path(__file__).resolve().parent.parent / 'external')
