from django import forms
from lastwill.contracts.submodels.swaps import ContractDetailsSWAPS
from lastwill.contracts.serializers import ContractDetailsSWAPSSerializer
from django.forms.widgets import TextInput


class CommonSerializedContractForm(forms.ModelForm):
    serializer_class = None

    def get_serializer(self, *args, **kwargs):
        assert self.serializer_class is not None

        return self.serializer_class(*args, **kwargs)

    def is_valid(self):
        if super(CommonSerializedContractForm, self).is_valid():
            print(self.cleaned_data, flush=True)
            serializer = self.get_serializer(data=self.cleaned_data)
            valid = serializer.is_valid()
            self.add_error(None, serializer.errors)
            return valid
        return False


class ContractFormSWAPS(CommonSerializedContractForm):
    serializer_class = ContractDetailsSWAPSSerializer

    def __init__(self, *args, **kwargs):
        super(ContractFormSWAPS, self).__init__(*args, **kwargs)
        self.fields['stop_date'].widget = TextInput()

    class Meta:
        model = ContractDetailsSWAPS
        fields = ['base_address',
                  'base_limit',
                  'quote_address',
                  'quote_limit',
                  'stop_date',
                  'public',
                  'owner_address',
                  'unique_link'
                  ]

    def clean_stop_date(self):
            stop_date = self.cleaned_data['stop_date']
            stop_date = str(stop_date.replace(tzinfo=None))[:-3]
            return stop_date

