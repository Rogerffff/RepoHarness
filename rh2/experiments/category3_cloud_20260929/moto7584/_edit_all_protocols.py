exec(open("/w/_edit_common.py").read())
# 复核反例：去掉 protocol == "application" 条件，对所有协议都校验 endpoint（检查放在查重之前）
s = s.replace(OLD, '''        try:
            self.get_endpoint(endpoint)
        except SNSNotFoundError:
            raise SNSInvalidParameter(
                f"Invalid parameter: Endpoint Reason: Endpoint does not exist for endpoint {endpoint}"
            )

''' + OLD)
p.write_text(s)
