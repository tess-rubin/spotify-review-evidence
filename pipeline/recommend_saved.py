"""Explicit local-only memo stage over saved partial aggregates; no enrichment."""
import json,time
from core import ROOT,dbopen,cached_role,dump,export
if __name__=='__main__':
 d=dbopen(ROOT/'data/full.sqlite');packs=json.loads((ROOT/'evidence/full-partial-aggregates.json').read_text());memo={'scope':'Partial full-corpus coverage; not representative of all reviews','recommendations':[]};start=time.monotonic()
 for pack in packs:memo['recommendations'].extend(cached_role(d,'memo',[],'full-partial-memo','resume',4.90,{'issues':[pack]})['recommendations'])
 dump(ROOT/'evidence/full-partial-recommendations.json',memo);dump(ROOT/'evidence/full-partial-memo-timing.json',{'seconds':time.monotonic()-start,'scope':'partial','api_cost_usd':0});d.close();export(ROOT/'data/full.sqlite',ROOT/'grading',ROOT/'supplied/spotify_reviews_18months.csv')
