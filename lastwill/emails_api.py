from django.core.mail import EmailMessage
from email_messages import verification_message, verification_subject
from lastwill.settings import DEFAULT_FROM_EMAIL, SUPPORT_EMAIL


def send_verification_mail(network, addresses, compiler, files):
    mail = EmailMessage(
        subject=verification_subject,
        body=verification_message.format(
            network=network,
            addresses=', '.join(addresses),
            compiler_version=compiler,
            optimization='Yes',
            runs='200',
        ),
        from_email=DEFAULT_FROM_EMAIL,
        to=[SUPPORT_EMAIL]
    )
    for filename, code in files.items():
        mail.attach(filename, code)
    mail.send()
