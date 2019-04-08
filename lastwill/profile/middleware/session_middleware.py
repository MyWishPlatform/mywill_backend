# from django.conf import settings


class CrossDomainSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response
        # One-time configuration and initialization.

    def __call__(self, request):
        # Code to be executed for each request before
        # the view (and later middleware) are called.

        response = self.get_response(request)

        # Code to be executed for each request/response after
        # the view is called.

        return response
    # def process_response(self, request, response):
    #     if response.cookies:
    #         host = request.get_host()
    #         # check if it's a different domain
    #         if host not in settings.SESSION_COOKIE_DOMAIN:
    #             domain = ".{domain}".format(domain=host)
    #             for cookie in response.cookies:
    #                 if 'domain' in response.cookies[cookie]:
    #                     response.cookies[cookie]['domain'] = domain
    #     return response
