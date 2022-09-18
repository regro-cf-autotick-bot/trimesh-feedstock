"""
Synchronize the conda-forge recipe with the requirements from
trimesh's latest setup.py on github.
"""
import yaml
import requests


def feedstock_name(package):
    """
    Check to see if a package has a conda-forge feedstock

    Parameters
    ------------
    package : str
      Name of a package to check

    Returns
    -------------
    name : str or None
      None if it doesn't exist
    """
    # base url to check
    base = 'https://github.com/conda-forge/{}-feedstock'

    #check_yes = requests.get(base.format('triangle'))
    #check_no = requests.get(base.format('blahahshdrraaa1123'))
    #assert check_no.status_code == 404
    #assert check_yes.status_code == 200

    # make sure name is clean
    package = package.lower().strip()

    # map packages to different name if known here
    name_map = {'msgpack': 'msgpack-python',
                'mapbox-earcut': 'mapbox_earcut'}
    if package in name_map:
        package = name_map[package]

    # check the feedstock on github
    fetch = requests.get(base.format(package))
    exists = fetch.status_code == 200

    print(f'{package} exists={exists}')

    if exists:
        return package
    return None


def fetch_requirements():
    """
    Fetch the latest `requirements_all` from trimesh's `setup.py`
    and then clean it up into `exec`-able string

    Returns
    ----------
    code : str
      Code containing requirements from trimesh
    """
    d = requests.get(
        'https://raw.githubusercontent.com/mikedh/trimesh/master/setup.py')
    lines = str.splitlines(d.content.decode('utf-8'))
    current = None
    saved = []
    for line in lines:
        if current is not None:
            current.append(line)
            if ')' in line:
                saved.append('\n'.join(current))
                current = None
        elif line.lower().startswith('requirements_'):
            current = [line]
    return '\n'.join(saved)


if __name__ == '__main__':
    # load `requirements_all` from trimesh's latest setup.py on github
    exec(fetch_requirements())

    # find the name on conda-forge of the trimesh requirements
    # remove any None-results with a set difference
    ok = set([feedstock_name(pack)
              for pack in requirements_all]).difference([None])

    # now update the run_constrained section with our results
    # NOT a yaml file: actually a jinja2 template for a yaml file
    meta_path = 'recipe/meta.yaml'
    with open(meta_path, 'r') as f:
        text = f.read()

    # use string wangling to find requirements section
    start = text.find('requirements')
    # look for ending whitespace- this is brittle!
    end = text.find('\n\n', start)
    # load requirements section from YAML
    load = yaml.safe_load(text[start:end])

    # find the existing set of `run_constrained` package requirements
    existing = set(load['requirements']['run_constrained'])

    print('packages changed: ', ok.symmetric_difference(existing))
    load['requirements']['run_constrained'] = list(ok)

    # compile result back into jinja2-template
    wangled = '\n'.join([text[:start],
                         yaml.dump(load, default_flow_style=False),
                         text[end:]]).strip() + '\n'
    # cheap hack to replace 2+ blank lines with a single blank line
    for i in range(10):
        wangled = wangled.replace('\n\n\n', '\n\n')
    print(f'\n\n{wangled}\n\n')

    # only write the result if the user says yes
    if (input(f'write to {meta_path}? (y/n)').lower().strip() == 'y'):
        with open(meta_path, 'w') as f:
            f.write(wangled)
