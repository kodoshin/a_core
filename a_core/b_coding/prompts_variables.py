
pe_files_xml = """
Task:

As an AI assistant, help me with the following:

Review the provided Django project files paths.

List all the files paths that would be useful to resolve the user's request.
Output them in this exact XML format:

<files>
  <file>File path of first relevant file</file>
  <file>File path of second relevant file</file>
  <!-- More files if needed -->
</files>

Constraints:

Do not include any additional text or explanations outside of the specified XML formats.
Do not modify the structure of the XML formats provided.
Do not include code or code snippets in your response.
Only provide the XML formatted questions or files as per the instructions.

"""


pe_components_xml = """
Task:

As an AI assistant, help me with the following:

Review the provided Django project components.

List all the components that would be useful to resolve the user's request.
Output them in this exact XML format:

<components>
  <component><file>File of first relevant component</file><name>Name of first relevant component</Name></component>
  <component><file>File of second relevant component</file><name>Name of second relevant component</Name></component>
  <!-- More component if needed -->
</components>

Constraints:

Do not include any additional text or explanations outside of the specified XML formats.
Do not modify the structure of the XML formats provided.
Do not include code or code snippets in your response.
Only provide the XML formatted questions or files as per the instructions.

"""


pe_final_answer = """
As an AI assistant, help me with the following:

Review the provided Django project resources and the request

Provide me a detailed solution using the resources to solve the request

"""

pe_final_answer_format = """
Develop the solution then please format the instructions in order to respect this format example
    <step1> 
    <Justifications> We will be creating a form to allow users to subscribe in the website. </Justifications>
    <file>app_name_1/forms.py</file>
    <code> <python> from django import forms from django.contrib.auth.models import User
    class InscriptionForm(forms.ModelForm): class Meta: model = User fields = ['username', 'email', 'password'] </python> </code>
    </step1>
    <step2> 
    <Justifications> We'll create a view to manage users subscribtion using the form we juste created. </Justifications>
    <file>app_name_2/views.py</file>
    <code> <python> from django.shortcuts import render, redirect from .forms import InscriptionForm from django.contrib.auth import login
    def inscription_view(request): if request.method == 'POST': form = InscriptionForm(request.POST) if form.is_valid(): user = form.save() login(request, user) return redirect('accueil') else: form = InscriptionForm() return render(request, 'utilisateurs/inscription.html', {'form': form}) </python> </code>
    </step2> 
    <step3> 
    <Justifications> Finally, we should create the html template to display the subscribtion form for users. </Justifications>
    <file>app_name/templates/app_name/subscribe.html</file>
    <code> <html> <body> <h1>Inscription</h1> <form method="post"> {% csrf_token %} {{ form.as_p }} <button type="submit">S'inscrire</button> </form> </body> </html> </code> 
    </step3>
    
    Constraints:
    Do not include any additional text or explanations outside of the specified XML format.
    Do not modify the structure of the XML formats provided, and make sure to include the coding language inside <code></code> balise.
    Make sure to respect code indentations and line breaks.
    Make sure to include the full path of the file.
    Please include the steps of creation of new resources or non existed files, apps or components

"""

none_answer = """
<step1> <Justifications> We haven't been able to process your request, please change the prompt or try again, if the error persists, please try later. </Justifications> </step1>
"""

no_components_answer = """
<step1> <Justifications> We didn't find any components that match your request, please update the prompt, if you think this is a mistake, please try again later </Justifications><file>None</file></step1>
"""