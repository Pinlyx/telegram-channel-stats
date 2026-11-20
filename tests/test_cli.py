import csv
import io
import json

from tgstats.cli import main
from tgstats.client import BASE_URL, Response


def run(make_client, routes, argv, capsys):
    client, _ = make_client(routes)
    code = main(argv, client=client)
    out = capsys.readouterr()
    return code, out.out, out.err


def test_text_report(make_client, ok, capsys):
    code, out, _ = run(make_client, {BASE_URL + "tgbeta": ok("tgbeta")}, ["tgbeta", "--posts", "20"], capsys)
    assert code == 0
    assert "Telegram Beta (@tgbeta)" in out
    assert "Subscribers:       27,900" in out
    assert "Top 5 posts by views" in out
    assert "median reach in its size band (20k-100k subscribers)" in out
    assert "Pinlyx, Telegram Channel Reach 2026" in out


def test_under_1000_report_explains(make_client, ok, capsys):
    routes = {BASE_URL + "golang_news": ok("golang_news")}
    code, out, _ = run(make_client, routes, ["golang_news", "--posts", "20"], capsys)
    assert code == 0 and "Benchmark:         not available" in out and "1,000" in out


def test_json_single_object_and_multi_list(make_client, ok, capsys):
    routes = {BASE_URL + "tgbeta": ok("tgbeta"), BASE_URL + "golang_news": ok("golang_news")}
    _, out, _ = run(make_client, routes, ["tgbeta", "--json", "--posts", "5"], capsys)
    assert json.loads(out)["username"] == "tgbeta"
    _, out, _ = run(make_client, routes, ["tgbeta", "golang_news", "--json", "--posts", "5"], capsys)
    data = json.loads(out)
    assert [d["username"] for d in data] == ["tgbeta", "golang_news"]


def test_csv_stdout(make_client, ok, capsys):
    routes = {BASE_URL + "tgbeta": ok("tgbeta")}
    _, out, _ = run(make_client, routes, ["tgbeta", "--csv", "--posts", "7"], capsys)
    rows = list(csv.DictReader(io.StringIO(out)))
    assert len(rows) == 7
    assert rows[0]["channel"] == "tgbeta" and rows[0]["views"].isdigit()


def test_csv_file(make_client, ok, capsys, tmp_path):
    target = tmp_path / "posts.csv"
    routes = {BASE_URL + "tgbeta": ok("tgbeta")}
    code, out, _ = run(make_client, routes, ["tgbeta", "--csv", str(target), "--posts", "3"], capsys)
    assert code == 0 and "Telegram Beta" in out
    with open(str(target), encoding="utf-8", newline="") as fh:
        assert len(list(csv.DictReader(fh))) == 3


def test_failure_exit_code_and_message(make_client, ok, capsys):
    routes = {
        BASE_URL + "tgbeta": ok("tgbeta"),
        BASE_URL + "closedchan": Response(302, "", "https://t.me/closedchan"),
    }
    code, out, err = run(make_client, routes, ["closedchan", "tgbeta", "--posts", "5"], capsys)
    assert code == 1
    assert "preview disabled" in err and "closedchan" in err
    assert "Telegram Beta" in out  # the good channel is still reported
