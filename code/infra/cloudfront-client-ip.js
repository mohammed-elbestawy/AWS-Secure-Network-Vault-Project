// CloudFront Function (viewer request), attached to the /api/* behavior.
// It overwrites any client-supplied x-client-ip with the real viewer address,
// so the WAF rate rule cannot be dodged by sending a forged X-Forwarded-For.
function handler(event) {
  var request = event.request;
  request.headers['x-client-ip'] = { value: event.viewer.ip };
  return request;
}
