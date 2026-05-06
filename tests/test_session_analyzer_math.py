import json
from app.session_analyzer import SessionAnalyzer


def w(path, rows):
    with path.open('w', encoding='utf-8') as f:
        for r in rows:
            f.write(json.dumps(r)+'\n')


def test_reclaim_rate_capped_and_unique(tmp_path):
    p=tmp_path/'a.jsonl'
    rows=[{"ts_ms":1000,"phase":"LIQUIDITY_SWEEP","signal_cluster_id":"x","debug":{} }]
    rows += [{"ts_ms":1100+i*100,"phase":"RECLAIM_WAIT","signal_cluster_id":"x","debug":{}} for i in range(6)]
    w(p,rows)
    a=SessionAnalyzer();a.load(p);d=a.analyze();post=d['post_sweep_analysis']
    assert post['unique_sweeps']==1
    assert post['reclaim_wait_ticks']==6
    assert post['reclaim_success_rate_pct']<=100.0


def test_old_jsonl_no_quality_fields(tmp_path):
    p=tmp_path/'b.jsonl';w(p,[{"ts":1,"phase":"NO_SETUP","score":1,"debug":{}}])
    a=SessionAnalyzer();a.load(p);d=a.analyze()
    assert 'post_signal_performance' in d['signal_quality_paper']


def test_post_signal_returns_and_excursions(tmp_path):
    p=tmp_path/'c.jsonl'
    rows=[
        {"ts_ms":1000,"is_new_market_event":True,"detected":True,"signal_quality_grade":"A","trigger_price":100.0,"phase":"SIGNALLED","debug":{}},
        {"ts_ms":2000,"price":101.0,"phase":"NO_SETUP","debug":{}},
        {"ts_ms":4000,"price":103.0,"phase":"NO_SETUP","debug":{}},
        {"ts_ms":6000,"price":99.0,"phase":"NO_SETUP","debug":{}},
        {"ts_ms":11000,"price":102.0,"phase":"NO_SETUP","debug":{}},
    ]
    w(p,rows)
    a=SessionAnalyzer();a.load(p);d=a.analyze();g=d['signal_quality_paper']['post_signal_performance']['A']
    assert g['count']==1
    assert round(g['avg_post_1s_return_pct'],3)==1.0
    assert round(g['avg_post_3s_return_pct'],3)==3.0
    assert round(g['avg_post_5s_return_pct'],3)==-1.0
    assert round(g['avg_post_10s_return_pct'],3)==2.0
    assert round(g['avg_max_favorable_10s_pct'],3)==3.0
    assert round(g['avg_max_adverse_10s_pct'],3)==-1.0


def test_recommendations(tmp_path):
    p=tmp_path/'d.jsonl'
    rows=[]
    for i in range(25):
        rows.append({"ts_ms":1000+i*2000,"signal":"LONG_SIGNAL","signal_group_id":i+1,"is_new_market_event":True,"detected":True,"signal_quality_grade":"A_PLUS" if i<10 else "C","trigger_price":100.0,"phase":"SIGNALLED","debug":{}})
        rows.append({"ts_ms":2000+i*2000,"price":101.0 if i<10 else 99.0,"phase":"NO_SETUP","debug":{}})
        rows.append({"ts_ms":4000+i*2000,"price":102.0 if i<10 else 98.5,"phase":"NO_SETUP","debug":{}})
    w(p,rows)
    a=SessionAnalyzer();a.load(p);d=a.analyze()
    assert d['signal_quality_paper']['recommendation'] in {'READY_FOR_REAL_PAPER_ENGINE','QUALITY_OK'}
