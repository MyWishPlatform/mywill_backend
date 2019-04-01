from django.shortcuts import render
from rest_framework.response import Response
from .forms import ContractFormSWAPS


def create_contract_swaps(request):
    if request.method == 'POST':
        form = ContractFormSWAPS(request.POST)
        if form.is_valid():
            return Response('contract created')
    else:
        form = ContractFormSWAPS()

    return render(request, 'create.html', {'form': form})
