# Django libraries
from django.template import RequestContext
from django.shortcuts import render_to_response, get_object_or_404
from django.http import HttpResponse, HttpResponseRedirect
from django.http import Http404
from django.contrib.auth.hashers import *
from django.views.csrf import csrf_failure
from django.db.models import Q

# Application specific functions
from images.models import ProfileImage, User_info
from register.forms import LoginForm, NewRegisterForm, UpdateProfileForm
from register.forms import ChangePasswordForm
from achievement.models import *
from images.models import ProfileImage
from register.helper import sendmail_after_userreg
from register.helper import notify_new_user, sendmail_after_pass_change
from fossWebsite.helper import error_key, csrf_failure, logged_in
from fossWebsite.helper import get_session_variables

# Python libraries
from hashlib import sha512 as hash_func
import json


# Create your views here.
def login(request):
    """
    A view to evaluate login form
    """
    try:
        # If the user is already loggedin never show the login page
        if logged_in(request):
            return render_to_response('register/logged_in.html', \
                    RequestContext(request))

        # Upon signin button click 
        if request.method=='POST':
            form = LoginForm(request.POST)

            # Form has all valid entries
            if form.is_valid():
                cleaned_login_data = form.cleaned_data
                inp_username = cleaned_login_data['username']
                inp_password = cleaned_login_data['password']
                hashed_password = hash_func(inp_password).hexdigest()
                user_tuple = User_info.objects.all().filter \
                        (username = inp_username)
                
                # There exist an entry in table with the given username
                if user_tuple:
                    actual_pwd = user_tuple[0].password
                    
                    # Password matches: session validation
                    if actual_pwd == hashed_password:
                        request.session['is_loggedin'] = True
                        request.session['username'] = inp_username
			request.session['email'] = user_tuple[0].email
                        return HttpResponseRedirect('/')
                    
                    # Invalid password
                    else:
                        error = "Invalid password. Is it really you, " + \
                                str(inp_username) + "?"
                        return render_to_response('register/login.html', \
                                {'form':form, 'error':error},
                                RequestContext(request))

                # There's no entry in the table with the given username
                else:
                    error = "User doesn't exist!"
                    return render_to_response('register/login.html', \
                            {'form':form, 'error':error},
                            RequestContext(request))

            # Invalid form inputs
            else:
                error = "Invalid username and password"
                return render_to_response('register/login.html',
                        {'form':form, 'error':error},
                        RequestContext(request))

        # 'GET' request i.e refresh
        else:
            # User is logged in and hence redirect to home page
    	    if 'is_loggedin' in request.session and \
                request.session['is_loggedin']:
	        return HttpResponseRedirect('/')
            # User is not logged in and refresh the page
            else:
                form=LoginForm()

        return render_to_response('register/login.html',
                {'form':form},
                RequestContext(request))

    except KeyError:
        return error_key(request)


def logout(request):
    """
    A view to handle logout request
    """
    try:
        del request.session['is_loggedin']
        del request.session['username']
        request.session.flush()
        return render_to_response('register/logout.html', \
                RequestContext(request))
    except KeyError:
        pass


def newregister(request):
    """
    Make a new registration, inserting into User_info and 
    ProfileImage models.
    """ 
    try:
        # If the user is already loggedin never show the login page
        if logged_in(request):
            return render_to_response('register/logged_in.html', 
                    RequestContext(request))
        
        # Upon Register button click
        if request.method == 'POST':
            form = NewRegisterForm(request.POST, request.FILES)

            # Form has all valid entries
            if form.is_valid():
                cleaned_reg_data = form.cleaned_data
                inp_username = cleaned_reg_data['username']
                inp_password = cleaned_reg_data['password']
                inp_email = cleaned_reg_data['email']

                # Saving the user inputs into table 
                new_register = form.save(commit=False)
                new_register.password = hash_func(inp_password) \
                                            .hexdigest()
                new_register.save()
                
                user_object = get_object_or_404(User_info, \
                        username=inp_username)
                
                # Optional image upload processing and saving
                if 'image' in request.FILES:
                    profile_image = request.FILES['image']
                    profile_image_object = ProfileImage \
                            (image=profile_image, \
                            username=user_object)
                    profile_image_object.image.name = inp_username + \
                                                    ".jpg"
                    profile_image_object.save()
                
                # Setting the session variables
                request.session['username'] = cleaned_reg_data['username']
                request.session['is_loggedin'] = True
		request.session['email'] = cleaned_reg_data['email']
                sendmail_after_userreg(inp_username, inp_password, inp_email)
                notify_new_user(inp_username, inp_email)
                return render_to_response('register/register_success.html',
                            {'is_loggedin':logged_in(request), \
                             'username':request.session['username']}, \
                            RequestContext(request))

            # Invalid form inputs
            else:
                error = "Invalid inputs"
                return render_to_response('register/newregister.html', 
                        {'form': form, 'error':error}, 
                        RequestContext(request))

        return render_to_response('register/newregister.html', 
                {'form': NewRegisterForm}, 
                RequestContext(request))

    except KeyError:
        return error_key(request)


def profile(request, user_name):
    """
    A view to display the profile (public)
    """
    is_loggedin, username = get_session_variables(request)
    user_object = get_object_or_404(User_info, \
            username = user_name)
    profile_image_object = ProfileImage.objects \
            .filter(username=user_object)
    user_email = user_object.email.replace('.', ' DOT ') \
            .replace('@', ' AT ')
    contributions = Contribution.objects.all() \
            .filter(username=user_name)[:3]
    articles = Article.objects.all() \
            .filter(username=user_name)[:3]
    gsoc = Gsoc.objects.all() \
            .filter(username=user_name)[:3]
    interns = Intern.objects.all() \
            .filter(username=user_name)[:3]
    speakers = Speaker.objects.all() \
            .filter(username=user_name)[:3]
    email = user_object.email
    icpc_achievement = ACM_ICPC_detail.objects.filter(participant1_email=email)| \
        ACM_ICPC_detail.objects.filter(participant2_email=email)| ACM_ICPC_detail.objects.filter(participant3_email=email)
    print icpc_achievement
    if profile_image_object:
       	image_name = user_name+".jpg"
    else:
       	image_name = "default_image.jpeg"

    return render_to_response( \
            'register/profile.html', \
            {'is_loggedin':is_loggedin, \
            'username':username, \
            'user_object':user_object, \
            'user_email':user_email, \
            'user_email':user_email, \
            'gsoc':gsoc, \
            'interns':interns, \
            'speakers':speakers, \
            'image_name':image_name, \
            'articles':articles, \
            'contributions':contributions, \
            'icpc_achievement':icpc_achievement}, \
            RequestContext(request))


def change_password(request):
    """
    A view to change the password of a logged in user
    """
    try:
        is_loggedin, username = get_session_variables(request)
        if not is_loggedin:
            return HttpResponseRedirect("/register/login")
        # POST request 
        if request.method == 'POST':
            form = ChangePasswordForm(request.POST)

            # Form inputs are valid
            if form.is_valid():
                new_pass = request.POST['new_password']
               	old_password = hash_func(request.POST['old_password']) \
                                .hexdigest()
                new_password = hash_func(request.POST['new_password']) \
                                .hexdigest()
                confirm_new_password = hash_func(
                                request.POST['confirm_new_password']) \
                                .hexdigest()

                user_data = User_info.objects.get(username = username)
                actual_pwd = user_data.password
                
                # Given current and stored passwords same
                if old_password == actual_pwd:
                    # New and current passwords user provided are not same 
                    if new_password != actual_pwd:
                        # Repass and new pass are same
                        if new_password == confirm_new_password:
                            user_data.password = new_password
                            sendmail_after_pass_change( \
                                    username, \
                                    new_pass, \
                                    user_data.email)
                            user_data.save()
                            return render_to_response( \
                                    'register/pass_success.html',
                                    {'username': username, \
                                    'is_loggedin': is_loggedin}, \
                                    RequestContext(request))
                        # Repass and new pass are not same
                        else:
                            error = "New passwords doesn't match"
                            return render_to_response( \
                                    'register/change_password.html', 
                                    {'form':form, \
                                    'username' :username, \
                                    'is_loggedin':is_loggedin, \
                                    'error':error}, \
                                    RequestContext(request))
                    # New and current password user provided are same
                    else:
                        error = "Your old and new password are same. Please \
                                choose a different password"
                        return render_to_response( \
                                'register/change_password.html', 
                                {'form':form, \
                                'username':username, \
                                'is_loggedin':is_loggedin, \
                                'error':error}, \
                                RequestContext(request))
                # Given current and stored passwords are not same
                else:
                    error = "Current password and given password doesn't match"
                    return render_to_response( \
                            'register/change_password.html', 
                            {'form':form, \
                            'username':username, \
                            'is_loggedin':is_loggedin, \
                            'error':error}, \
                            RequestContext(request))
            # Form inputs is/are invalid
            else:
                form = ChangePasswordForm()

            return render_to_response( \
                    'register/change_password.html', 
                    {'form':form, \
                    'username':username, \
                    'is_loggedin':is_loggedin}, \
                    RequestContext(request))

        return render_to_response( \
                'register/change_password.html',
                {'username': username, \
                'is_loggedin': is_loggedin}, \
                RequestContext(request))

    except KeyError:
        return error_key(request)


def mypage(request):
    """
    An editable profile page for the user
    """
    if not logged_in(request):
        return HttpResponseRedirect('/register/login')
    
    else:
        is_loggedin, username = get_session_variables(request)
        name = User_info.objects.get(username=username)
        return render_to_response( \
                'register/mypages.html',
                {'username':username, \
                'firstname':name.firstname, \
                'is_loggedin':is_loggedin, \
                'lastname':name.lastname,},\
                RequestContext(request))


def update_profile(request):
    try:
        is_loggedin, username = get_session_variables(request)
        # User is not logged in
        if not logged_in(request):
            return HttpResponseRedirect('/register/login')
        else:
            user_details = get_object_or_404(User_info, username = username)
            init_user_details = user_details.__dict__

            #If method is not POST 
            if request.method != 'POST':
                #return form with old details
                return render_to_response('register/update_profile.html',\
                    {'form':UpdateProfileForm(init_user_details),\
                    'is_loggedin':is_loggedin, 'username':username},\
                    RequestContext(request))

            # If method is POST
            else:
                profile_update_form = UpdateProfileForm(request.POST)
                # Form is not valid
                if not profile_update_form.is_valid():
                    #return form with old details

                    print profile_update_form.cleaned_data
                    return render_to_response('register/update_profile.html',\
                        {'form':UpdateProfileForm(init_user_details),\
                        'is_loggedin':is_loggedin, 'username':username},\
                        RequestContext(request))    
                # Form is valid:
                else:
                    user_details_form = profile_update_form.save(commit = False)
                    user_details_obj = get_object_or_404(User_info, username = username)
                    user_details_obj.firstname = user_details_form.firstname
                    user_details_obj.lastname = user_details_form.lastname
                    user_details_obj.gender = user_details_form.gender
                    user_details_obj.contact = user_details_form.contact
                    user_details_obj.role = user_details_form.role
                    user_details_obj.blog_url = user_details_form.blog_url
                    user_details_obj.twitter_id = user_details_form.twitter_id
                    user_details_obj.bitbucket_id = user_details_form.topcoder_handle
                    user_details_obj.github_id = user_details_form.github_id
                    user_details_obj.bitbucket_id = user_details_form.bitbucket_id
                    user_details_obj.typing_speed = user_details_form.typing_speed
                    user_details_obj.interest= user_details_form.interest
                    user_details_obj.expertise = user_details_form.expertise
                    user_details_obj.goal = user_details_form.goal
                    #user_details_obj.email = user_details_form.email
                    user_details_obj.save()  
                    redirect_url = "/register/profile/"+username+"/"
                    return HttpResponseRedirect(redirect_url)

    except KeyError:
        return error_key(request)

