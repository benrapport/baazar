#!/usr/bin/env python3
"""Generate an image gallery HTML from simulation results.

Usage: python demo/generate_gallery.py --output sim_results
"""
import argparse
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))


def build_image_index(output_dir: str, report: dict) -> dict:
    """Map market_ids to their image files."""
    img_dir = os.path.join(output_dir, "images")
    if not os.path.exists(img_dir):
        return {}

    rid_to_mid = {}
    for m in report['markets']:
        rid = m.get('request_id') or m.get('request_id_resolved', '')
        if rid:
            rid_to_mid[rid] = m['market_id']

    index = {}
    for rid in os.listdir(img_dir):
        rpath = os.path.join(img_dir, rid)
        if not os.path.isdir(rpath):
            continue
        mid = rid_to_mid.get(rid, rid)
        files = sorted(os.listdir(rpath))
        images = []
        for f in files:
            if not f.endswith('.png'):
                continue
            parts = f.replace('.png', '').split('_', 1)
            ts = parts[0] if parts else ''
            rest = parts[1] if len(parts) > 1 else f
            if '_r' in rest:
                agent_id = rest[:rest.rfind('_r')]
                rev = int(rest[rest.rfind('_r')+2:])
            else:
                agent_id = rest
                rev = 0
            images.append({
                'filename': f, 'path': f'images/{rid}/{f}',
                'agent_id': agent_id, 'revision': rev, 'timestamp': ts,
            })
        index[mid] = {'request_id': rid, 'images': images}
    return index


def generate_gallery(report: dict, image_index: dict, output_path: Path):
    """Generate gallery HTML."""
    ts = report['metadata']['timestamp']
    nm = report['metadata']['n_markets']

    lines = [f'''<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8">
<title>Bazaar — Market Gallery</title>
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
body{{font-family:'SF Mono','Fira Code',monospace;background:#0a0a0f;color:#e0e0e0;padding:16px}}
h1{{color:#ffd700;font-size:1.5em;margin-bottom:4px}}
.sub{{color:#666;font-size:.8em;margin-bottom:16px}}
a{{color:#00bcd4;text-decoration:none}}a:hover{{text-decoration:underline}}
.market{{background:#111118;border:1px solid #1e1e2e;border-radius:8px;padding:16px;margin-bottom:16px}}
.market-header{{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}}
.market-header h2{{color:#00bcd4;font-size:1.1em;margin:0}}
.market-meta{{color:#666;font-size:.8em}}
.prompt{{color:#aaa;font-style:italic;font-size:.9em;margin:6px 0 10px;line-height:1.4}}
.criteria{{color:#555;font-size:.75em;margin-bottom:10px}}
.criteria li{{margin:2px 0 2px 16px}}
.result{{margin:8px 0;font-size:.9em}}
.winner-tag{{background:#2e7d32;color:#fff;padding:2px 8px;border-radius:10px;font-size:.8em}}
.timeout-tag{{background:#8b0000;color:#fcc;padding:2px 8px;border-radius:10px;font-size:.8em}}
.images-row{{display:flex;gap:12px;overflow-x:auto;padding:8px 0}}
.img-card{{flex-shrink:0;width:280px;background:#0a0a12;border:1px solid #1e1e2e;border-radius:6px;overflow:hidden}}
.img-card.is-winner{{border:2px solid #4caf50}}
.img-card img{{width:280px;height:280px;object-fit:cover;display:block}}
.img-info{{padding:8px;font-size:.75em}}
.img-agent{{font-weight:bold}}.img-score{{font-size:1.1em;font-weight:bold;margin-left:4px}}
.img-score.high{{color:#4caf50}}.img-score.mid{{color:#ffeb3b}}.img-score.low{{color:#f44336}}
.img-feedback{{color:#888;font-size:.9em;margin-top:3px;line-height:1.3}}
.img-meta{{color:#555;font-size:.85em;margin-top:2px}}
.tc{{padding:3px 8px;border-radius:10px;font-size:.7em;font-weight:bold}}
.tc-penny{{background:#1a1a1a;color:#888;border:1px solid #333}}
.tc-budget{{background:#0a1f0a;color:#4caf50;border:1px solid #2e7d32}}
.tc-stress{{background:#1f140a;color:#ff9800;border:1px solid #e65100}}
.tc-mid{{background:#1f1f0a;color:#ffeb3b;border:1px solid #f9a825}}
.tc-premium{{background:#1f0a1f;color:#e040fb;border:1px solid #7b1fa2}}
.tc-creative{{background:#0a1f1f;color:#26c6da;border:1px solid #00838f}}
.nav{{position:sticky;top:0;background:#0a0a0f;padding:8px 0;z-index:10;border-bottom:1px solid #222;margin-bottom:12px}}
.nav-links{{display:flex;gap:6px;flex-wrap:wrap;font-size:.75em}}
.nav-link{{padding:3px 8px;border-radius:4px;background:#1a1a2a;color:#888}}
.nav-link:hover{{background:#2a2a3a;color:#fff}}
.nav-link.settled{{color:#4caf50}}.nav-link.timeout{{color:#f44336}}
</style></head><body>
<h1>BAZAAR EXCHANGE — MARKET GALLERY</h1>
<div class="sub">{ts} — {nm} markets | <a href="report.html">← Dashboard</a></div>
<div class="nav"><div class="nav-links">''']

    for m in report['markets']:
        cls = 'settled' if m['status'] == 'settled' else 'timeout'
        lines.append(f'<a class="nav-link {cls}" href="#{m["market_id"]}">{m["market_id"]}</a>')
    lines.append('</div></div>')

    for m in report['markets']:
        mid = m['market_id']
        tier = m['tier']
        imgs = image_index.get(mid, {}).get('images', [])
        sub_scores = {s['agent_id']: s for s in m.get('submissions', [])}
        winner_ids = {w['agent_id'] for w in m.get('winners', [])}
        if not winner_ids and m.get('winner'):
            winner_ids.add(m['winner'])
        top_n = m.get('top_n', 1)
        top_n_str = f' | top_n={top_n}' if top_n > 1 else ''
        n_p = m.get('n_participants', 0)
        n_q = m.get('n_qualified', 0)
        n_pass = m.get('n_passed', 0)
        meta = f'${m["max_price"]:.3f} | q≥{m["min_quality"]}{top_n_str}'
        if n_p:
            meta += f' | {n_p} submitted, {n_q} qualified, {n_pass} passed'

        lines.append(f'<div class="market" id="{mid}">')
        lines.append(f'<div class="market-header"><h2><span class="tc tc-{tier}">{tier.upper()}</span> {mid}</h2>')
        lines.append(f'<span class="market-meta">{meta}</span></div>')
        lines.append(f'<div class="prompt">"{m["prompt"]}"</div>')
        if m.get('criteria'):
            lines.append('<ul class="criteria">' + ''.join(f'<li>{c}</li>' for c in m['criteria']) + '</ul>')
        lines.append('<div class="result">')
        if m['status'] == 'settled':
            w_str = ', '.join(f'{w["agent_id"]} ({w["score"]}/10)' for w in m.get('winners', []))
            if not w_str:
                w_str = f'{m["winner"]} ({m["score"]}/10)'
            lines.append(f'<span class="winner-tag">★ {w_str}</span> {m["elapsed"]:.0f}s')
        else:
            lines.append('<span class="timeout-tag">TIMEOUT</span>')
        lines.append('</div>')

        if imgs:
            def sk(img):
                aid = img['agent_id']
                sc = sub_scores.get(aid, {})
                return (-int(aid in winner_ids), -(sc.get('final_score', 0) or sc.get('score', 0)), img['timestamp'])
            lines.append('<div class="images-row">')
            for img in sorted(imgs, key=sk):
                aid = img['agent_id']
                sd = sub_scores.get(aid, {})
                score = sd.get('final_score', sd.get('score', 0))
                fb = sd.get('feedback', '')[:120]
                off = sd.get('submit_offset_ms', 0)
                sc = 'high' if score >= 8 else ('mid' if score >= 6 else 'low')
                wc = ' is-winner' if aid in winner_ids else ''
                ws = ' ★' if aid in winner_ids else ''
                lines.append(f'<div class="img-card{wc}"><img src="{img["path"]}" loading="lazy">')
                lines.append(f'<div class="img-info"><span class="img-agent">{aid}{ws}</span><span class="img-score {sc}">{score}/10</span>')
                if fb:
                    lines.append(f'<div class="img-feedback">{fb}</div>')
                if off:
                    lines.append(f'<div class="img-meta">{off/1000:.1f}s | r{img["revision"]}</div>')
                lines.append('</div></div>')
            lines.append('</div>')

        lines.append('</div>')

    lines.append('</body></html>')
    output_path.write_text('\n'.join(lines))


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', default='sim_results')
    args = parser.parse_args()

    out = Path(args.output)
    with open(out / 'simulation.json') as f:
        report = json.load(f)

    index = build_image_index(args.output, report)
    generate_gallery(report, index, out / 'gallery.html')
    print(f'Gallery: {out / "gallery.html"} ({sum(len(v["images"]) for v in index.values())} images)')


if __name__ == '__main__':
    main()
