import pandas as pd
import pytest

from DataElevate import Invalid_Directory, Invalid_File_Support, Load_data


def test_csv(tmp_path):
    p = tmp_path / "train.csv"
    p.write_text("a,b\n1,2\n3,4\n")
    df = Load_data.from_local(p)
    assert list(df.columns) == ["a", "b"] and len(df) == 2


def test_uppercase_extension(tmp_path):
    p = tmp_path / "TRAIN.CSV"
    p.write_text("a,b\n1,2\n")
    assert len(Load_data.from_local(str(p))) == 1


@pytest.mark.parametrize("sep", ["\t", ",", ";", "|"])
def test_text_delimiter_detection(tmp_path, sep):
    p = tmp_path / "data.txt"
    p.write_text(f"x{sep}y\n1{sep}2\n3{sep}4\n")
    df = Load_data.from_local(p)
    assert list(df.columns) == ["x", "y"]


def test_tsv(tmp_path):
    p = tmp_path / "data.tsv"
    p.write_text("x\ty\n1\t2\n")
    assert list(Load_data.from_local(p).columns) == ["x", "y"]


def test_excel(tmp_path):
    p = tmp_path / "data.xlsx"
    pd.DataFrame({"a": [1, 2]}).to_excel(p, index=False)
    assert Load_data.from_local(p)["a"].tolist() == [1, 2]


def test_kwargs_passed_to_pandas(tmp_path):
    p = tmp_path / "data.csv"
    p.write_text("a,b\n1,2\n")
    assert list(Load_data.from_local(p, usecols=["b"]).columns) == ["b"]


def test_unsupported_raises(tmp_path):
    p = tmp_path / "data.json"
    p.write_text("{}")
    with pytest.raises(Invalid_File_Support):
        Load_data.from_local(p)


def test_missing_file_raises(tmp_path):
    with pytest.raises(Invalid_Directory):
        Load_data.from_local(tmp_path / "nope.csv")
