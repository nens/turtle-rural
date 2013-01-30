from setuptools import setup

version = '3.3.2dev'

long_description = '\n\n'.join([
    open('README.rst').read(),
    open('TODO.rst').read(),
    open('CREDITS.rst').read(),
    open('CHANGES.rst').read(),
    ])

install_requires = [
    'nens',
    'pkginfo',
    'setuptools',
    'turtlebase',
	'jinja2',
    ],

tests_require = [
    ]

setup(name='turtle-rural',
      version=version,
      description="TODO",
      long_description=long_description,
      # Get strings from http://www.python.org/pypi?%3Aaction=list_classifiers
      classifiers=[],
      keywords=[],
      author='Coen Nengerman',
      author_email='coen.nengerman@nelen-schuurmans.nl',
      url='',
      license='GPL',
      packages=['turtle_rural'],
      include_package_data=True,
      zip_safe=False,
      install_requires=install_requires,
      tests_require=tests_require,
      extras_require={'test': tests_require},
      entry_points={
          'console_scripts': [
            # Note: the .ini/tbx/dll/exe files used to be installed by the 'script' option.
            # Now buildout copies them into the bin dir through our own bin/copy_extra_bin_files script.
            'copy_extra_bin_files = turtle_rural.copy_extra_bin_files:main',

            'rural_aanmaken_koppelpunten = turtle_rural.rural_aanmaken_koppelpunten:main',
            'rural_afvoerendoppervlak = turtle_rural.rural_afvoerendoppervlak:main',
            'rural_afvoerpercentages = turtle_rural.rural_afvoerpercentages:main',
            'rural_afvoerrelaties = turtle_rural.rural_afvoerrelaties:main',
            'rural_bepalen_watersysteemlijn = turtle_rural.rural_bepalen_watersysteemlijn:main',
            'rural_cf_conversie = turtle_rural.rural_cf_conversie:main',
            'rural_compenserende_zijtakken = turtle_rural.rural_compenserende_zijtakken:main',
            'rural_controle_afvoer = turtle_rural.rural_controle_afvoer:main',
            'rural_correctie_oppervlakteparameter = turtle_rural.rural_correctie_oppervlakteparameter:main',
            'rural_drainageparameters = turtle_rural.rural_drainageparameters:main',
            'rural_genereren_afvoervlakken = turtle_rural.rural_genereren_afvoervlakken:main',
            'rural_indicatie_waterbezwaar = turtle_rural.rural_indicatie_waterbezwaar:main',
            'rural_inundatie = turtle_rural.rural_inundatie:main',
            'rural_maaiveldkarakteristiek = turtle_rural.rural_maaiveldkarakteristiek:main',
            'rural_naverwerking = turtle_rural.rural_naverwerking:main',
            'rural_naverwerking_rrcf = turtle_rural.rural_naverwerking_rrcf:main',
            'rural_oppervlakteparameter = turtle_rural.rural_oppervlakteparameter:main',
            'rural_risico = turtle_rural.rural_risico:main',
            'rural_rrcf_conversie = turtle_rural.rural_rrcf_conversie:main',
            'rural_rrcf_waterlevel = turtle_rural.rural_rrcf_waterlevel:main',
            'rural_rr_conversie = turtle_rural.rural_rr_conversie:main',
            'rural_profile_sorter = turtle_rural.rural_profile_sorter:main',
            'rural_rr_rrcf_conversie = turtle_rural.rural_rr_rrcf_conversie:main',
            'rural_toetsing_overstorten = turtle_rural.rural_toetsing_overstorten:main',
            'rural_toetspuntenbepaling = turtle_rural.rural_toetspuntenbepaling:main',
            'rural_voronoi_polygons = turtle_rural.rural_voronoi_polygons:main',
            'rural_convert_to_sobek = turtle_rural.rural_convert_to_sobek:script',
            'rural_import_cross_section = turtle_rural.rural_import_cross_section:main',
            'rural_plot_yz_profile = turtle_rural.rural_plot_yz_profile:main',
            'rural_bepalen_landgebruik = turtle_rural.rural_bepalen_landgebruik:main',
            'rural_flip_lines = turtle_rural.rural_flip_lines:main',
            'rural_network_analysis = turtle_rural.rural_network_analysis:main',
            'rural_import_sobek_cf = turtle_rural.rural_import_sobek_cf:main',
            'rural_culvertprofiles = turtle_rural.rural_culvertprofiles:main',
			'rural_waterbalance = turtle_rural.rural_waterbalance:main',
			'rural_controle_duikers = turtle_rural.rural_controle_duikers:main',
			'rural_aanwezigheid_peilscheidingen = turtle_rural.rural_aanwezigheid_peilscheidingen:main',
            'rural_abc_watergangen = turtle_rural.rural_abc_watergangen.py:main',
          ]},
      )
