import pyotp

def valid_totp(user, totp):
    if pyotp.TOTP(user.profile.totp_key).now() != totp:
        return False
    # prevent replay attack
    if user.profile.last_used_totp is not None and user.profile.last_used_totp == totp:
        return False
    user.profile.last_used_totp = totp
    user.profile.save(update_fields=['last_used_totp'])
    return True
