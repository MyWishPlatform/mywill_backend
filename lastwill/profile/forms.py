
from django.contrib.auth.forms import PasswordResetForm,




class CustomPasswordResetForm(PasswordResetForm):
    email = forms.EmailField(
        label=_("Email"),
        max_length=254,
        widget=forms.EmailInput(attrs={'autocomplete': 'email'})
    )

    def save(self, domain_override=None,
             subject_template_name='registration/password_reset_subject.txt',
             email_template_name='registration/password_reset_email.html',
             use_https=False, token_generator=default_token_generator,
             from_email=None, request=None, html_email_template_name=None,
             extra_email_context=None):
        """
        Generate a one-use only link for resetting password and send it to the
        user.
        """
        email = self.cleaned_data["email"]

        for user in self.get_users(email):
            if not domain_override:
                current_site = get_current_site(request)
                site_name = current_site.name
                domain = current_site.domain
            else:
                site_name = domain = domain_override
            context = {
                'email': email,
                'user': user,
                **(extra_email_context or {}),
            }
            if self.request.META['HTTP_HOST'] == MY_WISH_URL:
                email_user = EMAIL_HOST_USER
                site_name = 'MyWish Platform'

                self.send_mail(
                subject_template_name, email_template_name, context, from_email,
                email, html_email_template_name=html_email_template_name,

            if self.request.META['HTTP_HOST'] == SWAPS_URL:
                #from_email = EMAIL_HOST_USER_SWAPS
                email_user = EMAIL_HOST_USER
                site_name = "SWAPS.NETWORK"

                self.send_mail(
                subject_template_name, email_template_name, context, from_email,
                email, html_email_template_name=html_email_template_name,
            )
