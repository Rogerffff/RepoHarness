from pathlib import Path
p = Path("moto/sns/models.py")
s = p.read_text()
OLD = '''        # AWS doesn't create duplicates
        old_subscription = self._find_subscription(topic_arn, endpoint, protocol)
        if old_subscription:
            return old_subscription
'''
assert s.count(OLD) == 1
def check(msg):
    return f'''        if protocol == "application":
            try:
                self.get_endpoint(endpoint)
            except SNSNotFoundError:
                raise SNSInvalidParameter(
                    {msg}
                )

'''
