from django.shortcuts import render
from django.contrib.auth.decorators import login_required

@login_required
def test_flagging(request):
    """Test page for the flagging system"""
    return render(request, 'council_finance/test_flagging.html')