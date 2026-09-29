exec(open("/w/_edit_common.py").read())
# 复核反例（示例拟合）：只拒绝“删除过的”端点 ARN，从未创建过的 ARN 仍可订阅
s = s.replace(OLD, '''        if protocol == "application" and endpoint in getattr(self, "_deleted_endpoints", set()):
            raise SNSInvalidParameter(
                f"Invalid parameter: Endpoint Reason: Endpoint does not exist for endpoint {endpoint}"
            )

''' + OLD)
old_del = '''    def delete_endpoint(self, arn: str) -> None:
        try:
            del self.platform_endpoints[arn]
'''
assert s.count(old_del) == 1
s = s.replace(old_del, '''    def delete_endpoint(self, arn: str) -> None:
        if not hasattr(self, "_deleted_endpoints"):
            self._deleted_endpoints = set()
        self._deleted_endpoints.add(arn)
        try:
            del self.platform_endpoints[arn]
''')
p.write_text(s)
