import os
import unreal

project_dir = unreal.Paths.project_dir()
scripts = [
    os.path.join(project_dir, "Content", "Python", "build_hotel_greybox.py"),
    os.path.join(project_dir, "Content", "Python", "build_hotel_exterior.py"),
]

for script in scripts:
    if not os.path.exists(script):
        raise RuntimeError(f"Missing generator script: {script}")
    unreal.log(f"Running: {script}")
    with open(script, "r", encoding="utf-8") as handle:
        code = compile(handle.read(), script, "exec")
        exec(code, {"__name__": "__main__", "__file__": script})

unreal.log("Where's My Room: complete hotel interior greybox + exterior shell generated.")
