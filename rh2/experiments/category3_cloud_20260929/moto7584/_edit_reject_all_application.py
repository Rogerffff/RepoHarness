exec(open("/w/_edit_common.py").read())
# 退化：application 协议一律拒绝（有效端点也不能订阅）
s = s.replace(OLD, '''        if protocol == "application":
            raise SNSInvalidParameter(
                f"Invalid parameter: Endpoint Reason: Endpoint does not exist for endpoint {endpoint}"
            )

''' + OLD)
p.write_text(s)
