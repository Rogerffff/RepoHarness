# 附加到私有评分测试文件；截获真实HTTP运输的最底层，Moto的before-send事件仍实际运行。
import pytest


@pytest.fixture
def rh2_offline_ec2_transport():
    from unittest.mock import patch
    from botocore.awsrequest import AWSResponse

    payload = (
        b'<Response><Errors><Error><Code>AuthFailure</Code><Message>'
        b'AWS was not able to validate the provided access credentials'
        b'</Message></Error></Errors><RequestID>rh2-offline</RequestID></Response>'
    )

    class Raw:
        def stream(self, amt=None, decode_content=False):
            yield payload

    def send(session, request):
        assert request.url == 'https://ec2.us-west-1.amazonaws.com/'
        body = request.body.encode() if isinstance(request.body, str) else request.body
        assert b'Action=DescribeAddresses' in body
        return AWSResponse(request.url, 401, {'content-type': 'text/xml'}, Raw())

    with patch('botocore.httpsession.URLLib3Session.send', autospec=True, side_effect=send) as transport:
        yield transport
