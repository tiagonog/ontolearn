#!/usr/bin/env python3
"""figures.py - the figures of the audit paper, drawn from results/ (nothing is typed by hand).

  paper/fig_framework.pdf    the report-artifact gap along the claim-to-analytics chain (conceptual)
  paper/fig_lineage.pdf      E8: measured structural trace of the preserved development states
                             (not included in the paper, whose Table 7 gives the same data)
  paper/fig_scalability.pdf  E6: reasoning cost by size and prerequisite topology, per platform
"""
import json, statistics as st, sys
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

ROOT = Path(__file__).resolve().parent.parent
RES, OUT = ROOT / 'results', ROOT / 'paper'
OUT.mkdir(exist_ok=True)
plt.rcParams.update({'font.family': 'serif', 'font.serif': ['Times New Roman', 'Times', 'DejaVu Serif'],
                     'font.size': 8, 'axes.linewidth': 0.6, 'pdf.fonttype': 42, 'mathtext.fontset': 'stix'})
GREY, DARK, MID, LIGHT = '#444444', '#1f3b57', '#4f7ea8', '#dce6ef'
WARN = '#b5472f'


def framework():
    fig, ax = plt.subplots(figsize=(7.1, 2.95))
    ax.set_xlim(0, 100); ax.set_ylim(0, 43); ax.axis('off')

    def box(x, y, w, h, title, body, fc=LIGHT, ls='-'):
        ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle='round,pad=0.2,rounding_size=1.0', fc=fc, ec=DARK, lw=0.8, ls=ls))
        if title:
            ax.text(x + w / 2, y + h - 1.5, title, ha='center', va='top', fontsize=7.0, fontweight='bold', color=DARK)
        ax.text(x + w / 2, y + h - (5.2 if title else h / 2), body, ha='center', va='top' if title else 'center',
                fontsize=5.9, color='black', linespacing=1.25)

    y, h = 17.5, 15.0
    box(0.5, y, 15.5, h, 'Report', 'published claims $C$:\nconstructs, counts,\nprofile, validations')
    box(26.5, y, 20, h, 'Released file $O_{rel}$', 'serialized axioms\nand facts; earlier\nstates $O_1,\\dots,O_{n-1}$')
    box(57, y, 19.5, h, 'Mechanisms', 'DL reasoner, rule engine,\nSPARQL query engine,\nSHACL validator')
    box(86, y, 13.5, h, 'Analytics', 'prerequisites,\nevidence,\nproficiency')
    box(26.5, 36.6, 20, 5.2, '', 'evaluated graph $O_{eval}$', fc='white', ls='--')

    def arrow(x0, x1, yy, label):
        ax.add_patch(FancyArrowPatch((x0, yy), (x1, yy), arrowstyle='-|>', mutation_scale=9, lw=0.9, color=DARK))
        ax.text((x0 + x1) / 2, yy + 0.9, label, ha='center', va='bottom', fontsize=5.9, color=DARK)

    def tag(x, yy, t):
        ax.text(x, yy, t, ha='center', va='center', fontsize=6.6, fontweight='bold', color='white',
                bbox=dict(boxstyle='round,pad=0.2', fc=WARN, ec='none'))
    arrow(16.7, 25.8, 26.6, 'describes')
    tag(19.2, 21.8, 'G1'); tag(23.5, 21.8, 'G2')
    arrow(47.2, 56.3, 26.6, 'consumed by')
    tag(51.7, 21.8, 'G3')
    arrow(77.2, 85.3, 26.6, 'yield')
    ax.add_patch(FancyArrowPatch((36.5, 36.3), (36.5, 33.4), arrowstyle='<|-|>', mutation_scale=7, lw=0.8, color=DARK))
    tag(40.6, 34.9, 'G4')

    ax.plot([0, 100], [13.6, 13.6], color=GREY, lw=0.5)
    cols = [(0.5, 'G1', 'unrealized claim', 'a claim does not hold\nof the released file', 'claim check against the\nserialization (Algorithm 1)'),
            (25.5, 'G2', 'stale claim', 'a claim held only of\nan earlier state', 'longitudinal audit of\nthe preserved states'),
            (50.5, 'G3', 'unexercised axiom', 'a validation passes\nwithout the axiom', 'ablation by family; axiom-\nutilization matrix; tests'),
            (75.5, 'G4', 'evaluation\u2013release mismatch', 'the evaluated graph is\nnot the released file', 'digest-locked inputs;\nrelease-equivalence check')]
    for x, g, name, what, how in cols:
        tag(x + 1.8, 11.2, g)
        ax.text(x + 4.3, 11.2, name, ha='left', va='center', fontsize=6.2, fontweight='bold', color=WARN)
        ax.text(x, 9.0, what, ha='left', va='top', fontsize=5.9, color='black', linespacing=1.2)
        ax.text(x, 4.4, how, ha='left', va='top', fontsize=5.9, color=DARK, linespacing=1.2, style='italic')
    fig.savefig(OUT / 'fig_framework.pdf', bbox_inches='tight', pad_inches=0.02)
    plt.close(fig)


def lineage():
    rows = [r for r in json.loads((RES / 'E8_lineage.json').read_text()) if r['rdf']]
    x = list(range(len(rows)))
    labels = [r['state'].replace('=', '≡') for r in rows]
    fig, ax = plt.subplots(figsize=(3.45, 2.35))
    ax.plot(x, [r['classes'] for r in rows], '-o', ms=3, lw=1.0, color=DARK, label='classes')
    ax.plot(x, [r['object_properties'] + r['data_properties'] for r in rows], '-s', ms=3, lw=1.0, color=MID, label='object + data properties')
    ax.bar(x, [r['disjointness'] for r in rows], width=0.5, color=WARN, alpha=0.75, label='disjointness axioms')
    ax.set_xticks(x); ax.set_xticklabels(labels, rotation=35, ha='right', fontsize=6.5)
    ax.set_ylabel('count')
    ax2 = ax.twinx()
    ax2.plot(x, [r['rho'] for r in rows], '--^', ms=3, lw=0.9, color=GREY, label=r'ratio $\rho$')
    ax2.set_ylabel(r'$\rho$ = properties / classes'); ax2.set_ylim(0, 3.2)
    h1, l1 = ax.get_legend_handles_labels(); h2, l2 = ax2.get_legend_handles_labels()
    ax.legend(h1 + h2, l1 + l2, fontsize=6, loc='lower center', frameon=False, ncol=2, bbox_to_anchor=(0.5, 1.0))
    ax.set_ylim(0, 85)
    fig.savefig(OUT / 'fig_lineage.pdf', bbox_inches='tight', pad_inches=0.02)
    plt.close(fig)


def scalability():
    plats = [p for p in ['A', 'B'] if (RES / f'E6_scalability_{p}.jsonl').exists()]
    if not plats:
        return
    topo_style = {'chain': ('o', DARK), 'tree': ('s', MID), 'dag': ('^', WARN), 'dense': ('D', GREY)}
    fig, axes = plt.subplots(1, 3, figsize=(7.1, 2.3))
    P = plats[-1]                                   # panels (b) and (c) use one platform; (a) shows all
    for pl in plats:
        rows = [json.loads(l) for l in (RES / f'E6_scalability_{pl}.jsonl').read_text().splitlines()]
        for topo, (fmt, col) in topo_style.items():
            xs, ys = [], []
            for si in range(5):
                rs = [r for r in rows if r['topology'] == topo and r['size'] == si]
                if not rs:
                    continue
                xs.append(st.mean(r['individuals'] for r in rs))
                ys.append(st.mean(x['reasoning_ms'] for r in rs for x in r['hermit'] if x['phase'] == 'warm') / 1000)
            axes[0].plot(xs, ys, marker=fmt, ms=2.6, lw=0.8, color=col, mfc=col if pl == P else 'white',
                         ls='-' if pl == P else ':', label=topo if pl == P else None)
        xs, ys = [], []
        for si in range(5):
            rs = [r for r in rows if r['size'] == si]
            xs.append(st.mean(r['individuals'] for r in rs)); ys.append(st.mean(r['process_wall_s'] for r in rs))
        axes[0].plot(xs, ys, marker='x', ms=3, lw=0.8, color='black', ls='--' if pl == P else ':',
                     label='whole process' if pl == P else None)
    axes[0].set_xscale('log'); axes[0].set_yscale('log')
    axes[0].set_xlabel('individuals'); axes[0].set_ylabel('seconds'); axes[0].set_title('(a) HermiT: consistency, classification,\nrealization (in-JVM, warm)', fontsize=7)
    axes[0].legend(fontsize=5.2, frameon=False, loc='lower right', handlelength=1.6, labelspacing=0.25)
    rows = [json.loads(l) for l in (RES / f'E6_scalability_{P}.jsonl').read_text().splitlines()]
    for topo, (fmt, col) in topo_style.items():
        rs = sorted([r for r in rows if r['topology'] == topo and r.get('hermit_closure')], key=lambda r: r['size'])
        axes[1].plot([r['closure_pairs'] for r in rs], [r['hermit_closure'][-1]['closure_ms'] / 1000 for r in rs], marker=fmt, ls='-', ms=2.6, lw=0.8, color=col, label=topo)
        rs2 = sorted([r for r in rows if r['topology'] == topo and r['seed'] == 1], key=lambda r: r['size'])
        axes[1].plot([r['closure_pairs'] for r in rs2], [max(r['path_query_s'], 1e-3) for r in rs2], marker=fmt, ms=2.6, lw=0.8, color=col, ls=':', mfc='white')
    axes[1].set_xscale('log'); axes[1].set_yscale('log')
    axes[1].set_xlabel('prerequisite closure pairs'); axes[1].set_title('(b) full prerequisite closure: through the\nreasoner (solid) vs SPARQL path (dotted)', fontsize=7)
    for topo, (fmt, col) in topo_style.items():
        xs, ys = [], []
        for si in range(5):
            rs = [r for r in rows if r['topology'] == topo and r['size'] == si and 'owlrl_s' in r]
            if rs:
                xs.append(st.mean(r['triples'] for r in rs)); ys.append(st.mean(r['owlrl_s'] for r in rs))
        axes[2].plot(xs, ys, marker=fmt, ls='-', ms=2.6, lw=0.8, color=col, label=topo)
    axes[2].set_xscale('log'); axes[2].set_yscale('log')
    axes[2].set_xlabel('asserted triples'); axes[2].set_title('(c) OWL 2 RL rule closure\n(owlrl)', fontsize=7)
    from matplotlib.ticker import LogLocator, NullFormatter
    for a in axes:
        a.tick_params(labelsize=6.5, width=0.5); a.grid(True, which='major', lw=0.3, alpha=0.5)
        a.xaxis.set_major_locator(LogLocator(base=10, numticks=6)); a.xaxis.set_minor_formatter(NullFormatter())
        a.yaxis.set_minor_formatter(NullFormatter())
    axes[2].set_xticks([1000, 2000, 5000]); axes[2].set_xticklabels(['1,000', '2,000', '5,000'])
    fig.tight_layout(w_pad=1.0)
    fig.savefig(OUT / 'fig_scalability.pdf', bbox_inches='tight', pad_inches=0.02)
    plt.close(fig)


if __name__ == '__main__':
    framework(); lineage(); scalability()
    print('figures written to', OUT)
