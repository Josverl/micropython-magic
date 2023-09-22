from pathlib    import Path 

MY_PATH = Path(__file__).parent.absolute()

def path_for_script(name:str):
    return MY_PATH / "scripts" / name 