from llm_sandbox import SandboxSession

# Or default image
with SandboxSession(lang="python", keep_template=True) as session:
    result = session.run("print('Hello, World!')")
    print(result)