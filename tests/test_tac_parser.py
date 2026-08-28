import pytest
from pathlib import Path
from src.data.tac_parser import parse_directory, parse_train, parse_gold, _parse_single_xml

def test_parse_single_xml(tmp_path: Path):
    xml_content = """<?xml version="1.0" encoding="UTF-8"?>
<Document drug="methotrexate">
    <Mentions>
        <Mention id="M1" type="AdverseReaction" str="nausea" start="10" len="6" />
        <Mention id="M2" type="Severity" str="severe" start="0,18" len="6,6" />
    </Mentions>
    <Relations>
        <Relation id="R1" type="HasSeverity" arg1="M1" arg2="M2" />
    </Relations>
    <Reactions>
        <Reaction id="Rx1" str="nausea">
            <Normalization meddra_pt="Nausea" meddra_pt_id="10028813" />
        </Reaction>
    </Reactions>
</Document>
"""
    xml_file = tmp_path / "test.xml"
    xml_file.write_text(xml_content)
    
    mentions, relations, reactions = _parse_single_xml(xml_file, "train")
    
    assert len(mentions) == 2
    assert mentions[0]["mention_str"] == "nausea"
    assert not mentions[0]["is_discontinuous"]
    
    assert mentions[1]["is_discontinuous"]
    assert mentions[1]["n_spans"] == 2
    
    assert len(relations) == 1
    assert relations[0]["relation_type"] == "HasSeverity"
    
    assert len(reactions) == 1
    assert reactions[0]["meddra_pt_id"] == "10028813"

def test_gold_guard(tmp_path: Path):
    gold_dir = tmp_path / "gold_xml"
    gold_dir.mkdir()
    (gold_dir / "test.xml").write_text("<Document drug='test' />")
    
    with pytest.raises(PermissionError):
        parse_directory(gold_dir, split="gold", allow_gold=False)
        
    m, r, rx = parse_gold(tmp_path)
    assert len(m) == 0
    assert len(r) == 0
    assert len(rx) == 0
