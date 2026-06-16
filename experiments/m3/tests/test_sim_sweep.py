"""The sim-sweep CSV parser (the orchestration runs on myDevbox; only parsing is unit-tested here)."""

import textwrap

import sim_sweep as ss


def test_parse_ttft_ns_reads_last_request_row(tmp_path):
    csv = tmp_path / "run.csv"
    csv.write_text(textwrap.dedent("""\
        instance id,request id,model,input,output,arrival,end_time,latency,queuing_delay,TTFT,TPOT,ITL
        0,0,meta-llama/Llama-3.1-8B,2048,2,0,750994238,750994238,0,750994238,11481995,"[1,2]"
    """))
    assert ss.parse_ttft_ns(str(csv)) == 750994238


def test_make_trace_record_shapes_long_prompt():
    rec = ss.make_trace_record(input_toks=2048, output_toks=2)
    assert rec["input_toks"] == 2048
    assert rec["output_toks"] == 2
    assert len(rec["input_tok_ids"]) == 2048
    assert len(rec["output_tok_ids"]) == 2
    assert rec["arrival_time_ns"] == 0
