pe_files_xml = """
Task:

As an AI assistant, help me with the following:

Review the provided {technology} project files paths.

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

Review the provided {technology} project components.

List all the components that would be useful to resolve the user's request.
Output them in this exact XML format:

<components>
  <component><file>File of first relevant component</file><name>Name of first relevant component</name></component>
  <component><file>File of second relevant component</file><name>Name of second relevant component</name></component>
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

Review the provided {technology} project resources and the request

Provide me a detailed solution using the resources to solve the request.

"""

pe_final_answer_format = """
Please analyze the current code and provide a structured insight response in the following format:

<insight>
<file>/full/path/to/file.py</file>
<summary>
A good explanation of what the file or section does.
</summary>
<opportunities>
<item>Brief insight or improvement opportunity #1.</item>
<code><language>Code of the improvement #1 if pertinent.</language></code>
<item>Brief insight or improvement opportunity #2.</item>
<code><language>Code of the improvement #2 if pertinent.</language></code>
...
</opportunities>
<risk_zones>
<item>Optional: risky or unclear parts of the code.</item>
<code><language>Code of the risk #1 if pertinent.</language></code>
</risk_zones>
<recommendations>
<item>Specific and actionable recommendation #1.</item>
<code><language>Code of the recommendation #1 if pertinent.</language></code>
<item>Specific and actionable recommendation #2.</item>
<code><language>Code of the recommendation #2 if pertinent.</language></code>
</recommendations>
</insight>

Constraints:

Only return structured XML-style blocks as shown.

No generic summaries, everything must be tightly linked to the actual repo context.

Use <code> blocks if you suggest improvements or fixes.
Use <language> blocks to specify the used language (example: <python>, <javascript>, etc.), else use <text> block.

Do not rename functions, models, or variables unless strictly necessary.

If no issues found, still include <summary> and explicitly mention No critical issues found in <opportunities>.

Respect file paths, indentation, and original logic.

If needed, suggest monitoring areas for future technical debt or scalability risks.

Never include speculative advice not backed by the source code.

"""

none_answer = """
<step1> <Justifications> We haven't been able to process your request, please change the prompt or try again, if the error persists, please try later. </Justifications> </step1>
"""

no_components_answer = """
<step1> <Justifications> We didn't find any components that match your request, please update the prompt, if you think this is a mistake, please try again later </Justifications><file>None</file></step1>
"""