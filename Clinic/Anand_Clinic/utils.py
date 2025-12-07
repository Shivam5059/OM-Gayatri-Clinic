from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import redirect

def group_required(group_name, login_url='login'):
    def in_group(u):
        return u.is_authenticated and u.groups.filter(name=group_name).exists()
    return user_passes_test(in_group, login_url=login_url)