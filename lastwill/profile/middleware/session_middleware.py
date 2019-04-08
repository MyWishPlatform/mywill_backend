# from django.conf import settings


class CrossDomainSessionMiddleware():
    pass
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
