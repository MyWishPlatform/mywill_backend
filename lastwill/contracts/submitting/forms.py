from django import forms
from lastwill.contracts.submodels.swaps import ContractDetailsSWAPS
from lastwill.contracts.serializers import ContractDetailsSWAPSSerializer


class CommonSerializedContractForm(forms.ModelForm):
    serializer_class = None

    def get_serializer(self, *args, **kwargs):
        assert self.serializer_class is not None

        return self.serializer_class(*args, **kwargs)

    def is_valid(self):
        if super(CommonSerializedContractForm, self).is_valid():
            serializer = self.get_serializer(data=self.cleaned_data)
            valid = serializer.is_valid()
            self.add_error(None, serializer.errors)
            return valid
        return False


class ContractFormSWAPS(CommonSerializedContractForm):
    serializer_class = ContractDetailsSWAPSSerializer

    class Meta:
        model = ContractDetailsSWAPS
        exclude = ['id', 'contract' 'eth_contract', 'temp_directory']
