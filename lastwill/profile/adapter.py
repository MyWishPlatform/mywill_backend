from django.core.mail import send_mail, EmailMessage
from django.contrib.sites.shortcuts import get_current_site
from allauth.account.adapter import DefaultAccountAdapter
from lastwill.settings import MY_WISH_URL, DEFAULT_FROM_EMAIL,SWAPS_URL, SWAPS_MAIL
from email_messages import register_subject, register_text


class SubSiteRegistrationAdapter(DefaultAccountAdapter):

    def send_confirmation_mail(self, request, emailconfirmation, signup):
        welcome_head = ''
        current_site = get_current_site(request)
        activate_url = self.get_email_confirmation_url(
            request,
            emailconfirmation)
        if self.request.META['HTTP_HOST'] == MY_WISH_URL:
            from_email= DEFAULT_FROM_EMAIL
            welcome_head = 'MyWish Platform'
        if self.request.META['HTTP_HOST'] == SWAPS_URL:
            from_email = SWAPS_MAIL
            welcome_head = "SWAPS Network"

        to_user = emailconfirmation.email_address.user
        to_email = emailconfirmation.email_address.email

        send_mail(
            register_subject,
            register_text.format(
                subsite_name=welcome_head,
                user_display=to_user,
                activate_url=activate_url
            ),
            from_email,
            [to_email]
        )
