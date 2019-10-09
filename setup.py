import setuptools

with open("readme.md", "r") as fh:
    long_description = fh.read()

setuptools.setup(
    name="gatetools",
    version="0.8.1",
    author="OpenGate collaboration",
    author_email="david.sarrut@creatis.insa-lyon.fr",
    description="Python tools for GATE, see https://github.com/OpenGATE/Gate",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/OpenGATE/GateTools",
    packages=['gatetools'],
    classifiers=(
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: Apache Software License",
        "Operating System :: OS Independent",
    ),
    install_requires=[
        'uproot',
        'click',
        'pydicom',
        'tqdm',
        'colored',
        'itk',
        'uproot',
    ],
    scripts=[
        'bin/gt_gate_info',
        
        'bin/gt_image_uncertainty',
        'bin/gt_image_arithm',
        'bin/gt_image_convert',
        'bin/gt_gamma_index',
        
        'bin/phsp_info',
        'bin/phsp_convert',
        'bin/phsp_merge',
        'bin/phsp_plot',
        'bin/phsp_peaks',
    ]
)


# Help for uploading the package (TEST)

# pip uninstall gatetools
# python3 setup.py sdist bdist_wheel
# twine upload --repository-url https://test.pypi.org/legacy/ dist/*

# test with
# pip3 install --index-url https://test.pypi.org/simple/ gatetools
