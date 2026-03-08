from django import forms
from .models import Challenge, TestCase

class ChallengeForm(forms.ModelForm):
    class Meta:
        model = Challenge
        fields = ['title', 'description']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-input', 'placeholder': 'Challenge Title'}),
            'description': forms.Textarea(attrs={'class': 'form-input', 'placeholder': 'Describe the problem statement...'}),
        }

class TestCaseForm(forms.ModelForm):
    class Meta:
        model = TestCase
        fields = ['input_text', 'input_file', 'output_text', 'output_file', 'is_hidden']
        widgets = {
            'input_text': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Input text data...'}),
            'input_file': forms.FileInput(attrs={'class': 'form-input-file'}),
            'output_text': forms.Textarea(attrs={'class': 'form-input', 'rows': 3, 'placeholder': 'Expected output text data...'}),
            'output_file': forms.FileInput(attrs={'class': 'form-input-file'}),
            'is_hidden': forms.CheckboxInput(attrs={'class': 'form-checkbox'}),
        }
