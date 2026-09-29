exec(open("/w/_edit_common.py").read())
# 退化：检查位置正确但抛 NotFound（错误码不是题面要求的 InvalidParameter）
s = s.replace(OLD, '''        if protocol == "application":
            self.get_endpoint(endpoint)

''' + OLD)
p.write_text(s)
