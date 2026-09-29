exec(open("/w/_edit_common.py").read())
# 退化（§4 第 3 步“一律拒绝”）：application 协议一律报错，正文采用隐藏测试的 arn{endpoint} 形态
s = s.replace(OLD, '''        if protocol == "application":
            raise SNSInvalidParameter(
                f"Invalid parameter: Endpoint Reason: Endpoint does not exist for endpoint arn{endpoint}"
            )

''' + OLD)
p.write_text(s)
