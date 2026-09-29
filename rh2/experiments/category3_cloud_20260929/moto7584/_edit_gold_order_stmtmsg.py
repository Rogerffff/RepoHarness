exec(open("/w/_edit_common.py").read())
# gold 的检查位置（先按旧订阅提前返回），报错正文按题面模板
s = s.replace(OLD, OLD + "\n" + check('f"Invalid parameter: Endpoint Reason: Endpoint does not exist for endpoint {endpoint}"'))
p.write_text(s)
