

def test_metrics_show_precision_real_values(tmp_dir, dvc, caplog):
    # 读取真实 YAML，断言命令输出数值；不 mock 格式化 helper 或约束传参形式。
    tmp_dir.gen("metrics.yaml", "error: 0.123456789\nsmall: 1.4832495253358502e-05\n")
    cases = [
        ([], 5),
        (["--precision", "3"], 3),
        (["--precision", "8"], 8),
        (["--precision", "8", "--show-md"], 8),
    ]
    for options, precision in cases:
        caplog.clear()
        cli_args = parse_args(["metrics", "show", "metrics.yaml", *options])
        with caplog.at_level("INFO", logger="dvc"):
            assert cli_args.func(cli_args).run() == 0
        messages = [
            record.getMessage()
            for record in caplog.records
            if record.name == "dvc.command.metrics"
        ]
        rows = [
            row for message in messages for row in message.splitlines()
            if "metrics.yaml" in row
        ]
        assert len(rows) == 1, (options, messages)
        cells = rows[0].replace("|", " ").split()
        assert cells[0] == "metrics.yaml", (options, cells)
        assert [float(cell) for cell in cells[1:]] == [
            round(0.123456789, precision),
            round(1.4832495253358502e-05, precision),
        ], (options, cells)
