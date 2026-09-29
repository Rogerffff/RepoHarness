exec(open("/w/_edit_common.py").read())
# 复核反例（v2 聚焦复核）：凡是 ARN 形式的 endpoint（不论协议）都校验是否为已存在的 platform endpoint
s = s.replace(OLD, '''        if endpoint.startswith("arn:"):
            try:
                self.get_endpoint(endpoint)
            except SNSNotFoundError:
                raise SNSInvalidParameter(
                    f"Invalid parameter: Endpoint Reason: Endpoint does not exist for endpoint {endpoint}"
                )

''' + OLD)
p.write_text(s)
