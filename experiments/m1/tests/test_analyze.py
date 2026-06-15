"""M1 go/no-go decision rule (M1_CHECKLIST §3.4, EVALUATION_CONTRACT)."""

import pytest

import analyze

MB = 1 << 20


def rec(codec, is_bf3, chunk, p50):
    return {"codec": codec, "is_bf3": is_bf3, "chunk_size_bytes": chunk, "ratio_p50": p50}


def test_green_when_bf3_codec_hits_075_at_small_chunk():
    recs = [rec("deflate", True, 1 * MB, 0.70), rec("zstd", False, 1 * MB, 0.60)]
    assert analyze.decide(recs)[0] == "GREEN"


def test_red_when_all_above_085():
    recs = [rec("deflate", True, 1 * MB, 0.90), rec("lz4", True, 1 * MB, 0.95), rec("zstd", False, 1 * MB, 0.88)]
    assert analyze.decide(recs)[0] == "RED"


def test_yellow_when_only_large_chunk_bf3_hits():
    recs = [rec("deflate", True, 16 * MB, 0.70), rec("deflate", True, 1 * MB, 0.82)]
    assert analyze.decide(recs)[0] == "YELLOW"


def test_yellow_when_only_nonbf3_zstd_hits():
    recs = [rec("zstd", False, 1 * MB, 0.70), rec("deflate", True, 1 * MB, 0.82)]
    assert analyze.decide(recs)[0] == "YELLOW"


def test_yellow_marginal_between_thresholds():
    recs = [rec("deflate", True, 1 * MB, 0.80), rec("lz4", True, 1 * MB, 0.83)]
    assert analyze.decide(recs)[0] == "YELLOW"


def test_empty_raises():
    with pytest.raises(ValueError):
        analyze.decide([])


def test_is_bf3_helper():
    assert analyze.is_bf3_codec("deflate") and analyze.is_bf3_codec("lz4")
    assert not analyze.is_bf3_codec("zstd") and not analyze.is_bf3_codec("none")
