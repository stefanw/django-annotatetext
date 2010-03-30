from distutils.core import setup

setup(
    name='django-annotatetext',
    version='0.1.b',
    description='django-annotatext lets users annotate text fields of other models',
    author='Stefan Wehrmeyer',
    author_email='Stefan Wehrmeyer <mail@stefanwehrmeyer.com>',
    url='http://github.com/stefanw/django-annotatetext',
    packages = ["annotatetext", "annotatetext.templatetags"],
    classifiers=[
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Utilities',
    ]
)