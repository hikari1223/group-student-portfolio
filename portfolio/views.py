from django.shortcuts import render


def home(request):
    return render(request, 'portfolio/home.html')


def about(request):
    return render(request, 'portfolio/about.html')


def members(request):
    return render(request, 'portfolio/members.html')


def skills(request):
    return render(request, 'portfolio/skills.html')


def projects(request):
    return render(request, 'portfolio/projects.html')


def gallery(request):
    return render(request, 'portfolio/gallery.html')


def contact(request):
    return render(request, 'portfolio/contact.html')


