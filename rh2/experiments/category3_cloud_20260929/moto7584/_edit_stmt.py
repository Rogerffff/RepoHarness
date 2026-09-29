exec(open("/w/_edit_common.py").read())
# 题面：删除端点后再次订阅（即使之前订阅过）也应报错；报错正文按题面模板 {endpoint_arn}
s = s.replace(OLD, check('f"Invalid parameter: Endpoint Reason: Endpoint does not exist for endpoint {endpoint}"') + OLD)
p.write_text(s)
