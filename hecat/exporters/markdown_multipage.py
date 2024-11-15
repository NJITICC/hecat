"""export YAML data to a multipage markdown site which can be used to generate a HTML site with Sphinx
- A main index.html page listing all items
- Pages for each tag
This will output an intermediary markdown site in output_directory/md. sphinx (https://www.sphinx-doc.org/) must be used to generate the final HTML site

$ git clone https://github.com/awesome-selfhosted/awesome-selfhosted-data tests/awesome-selfhosted-data
$ $EDITOR .hecat.yml
$ hecat

# .hecat.yml
steps:
  - name: export YAML data to multi-page markdown/HTML site
    module: exporters/markdown_multipage
    module_options:
      source_directory: tests/awesome-selfhosted-data # directory containing YAML data
      output_directory: tests/awesome-selfhosted-html # directory to write markdown pages to
      exclude_licenses: # optional, default []
        - '⊘ Proprietary'
        - 'BUSL-1.1'
        - 'CC-BY-NC-4.0'
        - 'CC-BY-NC-SA-3.0'
        - 'CC-BY-ND-3.0'
        - 'Commons-Clause'
        - 'DPL'
        - 'SSPL-1.0'
        - 'DPL'
        - 'Elastic-1.0'
        - 'Elastic-2.0'

$ sphinx-build -b html -c CONFIG_DIR/ SOURCE_DIR/ OUTPUT_DIR/
CONFIG_DIR/ is the directory containing the conf.py sphinx configuration file, example at https://github.com/nodiscc/hecat/blob/master/tests/conf.py
SOURCE_DIR/ is the directory containing the markdown site generated by hecat/markdown_multipage.py
OUTPUT_DIR/ is the output directory for the HTML site
Currently, the following settings are expected in the sphinx configuration file (CONFIG_DIR/conf.py)
  html_theme = 'furo'
  extensions = ['myst_parser', 'sphinx_design']
  myst_enable_extensions = ['fieldlist']
  html_static_path = ['SOURCE_DIR/_static']
  html_css_files = ['custom.css']


Output directory structure (after running sphinx-build):
├── html # publish contents of this directory
│   ├── genindex.html
│   ├── index.html
│   ├── search.html
│   ├── searchindex.js
│   ├── _sphinx_design_static
│   │   ├── *.css
│   │   └── *.js
│   ├── _static
│   │   ├── *.png
│   │   ├── *.svg
│   │   ├── custom.css
│   │   ├── *.css
│   │   ├── *.js
│   │   ├── favicon.ico
│   │   └── opensearch.xml
│   └── tags
│       ├── analytics.html
│       ├── archiving-and-digital-preservation-dp.html
│       ├── ....html
│       └── wikis.html
└── md # intermediary markdown version, can be discarded
    ├── index.md
    └── tags

The source YAML directory structure, and formatting for software/platforms data is documented in markdown_singlepage.py.
"""

import os
import sys
import logging
from datetime import datetime, timedelta
import urllib
import ruamel.yaml
from jinja2 import Template
from ..utils import load_yaml_data, to_kebab_case, render_markdown_licenses

yaml = ruamel.yaml.YAML(typ='safe')
yaml.indent(sequence=4, offset=2)

MARKDOWN_CSS="""
    .tag {
        background-color: #DBEAFE;
        border-radius: 5px;
        padding: 2px 8px 0px 8px;
        color: #1E40AF;
        font-weight: bold;
        display: inline-block;
    }
    .tag a {
        text-decoration: none
    }
    .platform {
        background-color: #B0E6A3;
        border-radius: 5px;
        padding: 2px 8px 0px 8px;
        color: #2B4026;
        font-weight: bold;
        display: inline-block;
    }
    .platform a {
        text-decoration: none;
        color: #2B4026;
    }
    .license-box {
        background-color: #A7C7F9;
        border-radius: 5px;
        padding: 2px 8px 0px 8px;
        display: inline-block;
    }
    .license-link {
        color: #173B80;
        font-weight: bold;
        text-decoration: none
    }
    .stars {
        background-color: #FFFCAB;
        border-radius: 5px;
        padding: 2px 8px 0px 8px;
        color: #856000;
        font-weight: bold;
        display: inline-block;
    }
    .updated-at {
        background-color: #EFEFEF;
        border-radius: 5px;
        padding: 2px 8px 0px 8px;
        color: #444444;
        display: inline-block;
        font-weight: bold
    }
    .orangebox {
        background-color: #FD9D49;
        border-radius: 5px;
        padding: 2px 8px 0px 8px;
        color: #FFFFFF;
        display: inline-block;
        font-weight: bold
    }
    .redbox {
        background-color: #FD4949;
        border-radius: 5px;
        padding: 2px 8px 0px 8px;
        color: #FFFFFF;
        display: inline-block;
        font-weight: bold
    }
    .external-link-box {
        background-color: #1E40AF;
        border-radius: 5px;
        padding: 2px 8px 0px 8px;
        display: inline-block;
    }
    .external-link {
        color: #DBEAFE;
        font-weight: bold;
        text-decoration: none
    }
    .external-link a:hover {
        color: #FFF;
    }
    .sd-octicon {
        vertical-align: inherit
    }
    hr.docutils {
        margin: 1rem 0;
    }
    .sidebar-brand-text {
        font-size: 1.4rem;
    }
"""

MARKDOWN_INDEX_CONTENT_HEADER="""
--------------------

## Entries

This page lists all entries. Use links in the sidebar or click on {octicon}`tag;0.8em;octicon` tags to browse projects by category.
"""

SOFTWARE_JINJA_MARKDOWN="""
--------------------

### {{ software['name'] }}

{{ software['description'] }}

<span class="external-link-box"><a class="external-link" href="{{ software['website_url'] }}" target="_blank">{% raw %}{octicon}{% endraw %}`globe;0.8em;octicon` Website</a></span>
{% if software['source_code_url'] is defined %}<span class="external-link-box"><a class="external-link" href="{{ software['source_code_url'] }}" target="_blank">{% raw %}{octicon}{% endraw %}`git-branch;0.8em;octicon` Source Code</a></span>{% endif %}
{% if software['related_software_url'] is defined -%}<span class="external-link-box"><a class="external-link" href="{{ software['related_software_url'] }}" target="_blank">{% raw %}{octicon}{% endraw %}`package;0.8em;octicon` Clients</a></span>
{% endif -%}
{% if software['demo_url'] is defined -%}<span class="external-link-box"><a class="external-link" href="{{ software['demo_url'] }}" target="_blank">{% raw %}{octicon}{% endraw %}`play;0.8em;octicon` Demo</a></span>
{% endif %}

{% for platform in platforms %}<span class="platform"><a href="{{ platform['href'] }}">{% raw %}{octicon}{% endraw %}`package;0.8em;octicon` {{ platform['name'] }}</a> </span> {% endfor %}
{% for license in software['licenses'] %}<span class="license-box"><a class="license-link" href="{{ licenses_relative_url }}">{% raw %}{octicon}{% endraw %}`law;0.8em;octicon` {{ license }}</a> </span> {% endfor %}
{% if software['depends_3rdparty'] is defined and software['depends_3rdparty'] %}<span class="orangebox" title="Depends on a proprietary service outside the user's control">⚠ Anti-features</span>{% endif %}

{% for tag in tags %}<span class="tag"><a href="{{ tag['href'] }}">{% raw %}{octicon}{% endraw %}`tag;0.8em;octicon` {{ tag['name'] }}</a> </span>
{% endfor %}

"""

TAG_HEADER_JINJA_MARKDOWN="""

# {{ item['name'] }}

{{ item['description']}}

{% if item['related_tags'] is defined %}```{admonition} Related tags
{% for related_tag in item['related_tags'] %}- [{{ related_tag }}]({{ to_kebab_case(related_tag) }}.md)
{% endfor %}
```
{% endif %}
{% if item['external_links'] is defined %}```{seealso}
{% for link in item['external_links'] %}- [{{ link['title'] }}]({{ link['url'] }})
{% endfor %}
```{% endif %}
{% if item['redirect'] is defined %}```{important}
**Please visit {% for redirect in item['redirect'] %}[{{ redirect['title'] }}]({{ redirect['url'] }}){% if not loop.last %}{{', '}}{% endif %}{% endfor %} instead**
```{% endif %}

"""

MARKDOWN_TAGPAGE_CONTENT_HEADER="""
--------------------

## Software

This page lists all projects in this category. Use the [index of all projects](../index.md), the sidebar, or click on {octicon}`tag;0.8em;octicon` tags to browse other categories.

"""


PLATFORM_HEADER_JINJA_MARKDOWN="""

# {{ item['name'] }}

{{ item['description']}}

"""

MARKDOWN_PLATFORMPAGE_CONTENT_HEADER="""
--------------------

## Software

This page lists all projects using this programming language or deployment platform. Only the main server-side requirements, packaging or distribution formats are considered.

"""

def render_markdown_software(software, tags_relative_url='tags/', platforms_relative_url='platforms/', licenses_relative_url='#list-of-licenses'):
    """render a software project info as a markdown list item"""
    tags_dicts_list = []
    platforms_dicts_list = []
    for tag in software['tags']:
        tags_dicts_list.append({"name": tag, "href": tags_relative_url + urllib.parse.quote(to_kebab_case(tag)) + '.html'})
    if 'platforms' in software:
        for platform in software['platforms']:
            platforms_dicts_list.append({"name": platform, "href": platforms_relative_url + urllib.parse.quote(to_kebab_case(platform)) + '.html'})
    date_css_class = 'updated-at'
    if 'updated_at' in software:
        last_update_time = datetime.strptime(software['updated_at'], "%Y-%m-%d")
        if last_update_time < datetime.now() - timedelta(days=365):
            date_css_class = 'redbox'
        elif last_update_time < datetime.now() - timedelta(days=186):
            date_css_class = 'orangebox'
    software_template = Template(SOFTWARE_JINJA_MARKDOWN)
    markdown_software = software_template.render(software=software,
                                                 tags=tags_dicts_list,
                                                 platforms=platforms_dicts_list,
                                                 date_css_class=date_css_class,
                                                 licenses_relative_url=licenses_relative_url)
    return markdown_software

def render_item_page(step, item_type, item, software_list):
    """
    render a page for a tag of platform.
    :param dict step: step configuration
    :param str item_type: type of page to render (tag or platform)
    :param dict item: the item to render a page for (tag or platform object)
    :param list software_list: the full list of software (list of dicts)
    """
    logging.debug('rendering page for %s %s', item_type, item['name'])
    if item_type == 'tag':
        markdown_fieldlist = ''
        header_template = Template(TAG_HEADER_JINJA_MARKDOWN)
        content_header = MARKDOWN_TAGPAGE_CONTENT_HEADER
        match_key = 'tags'
        tags_relative_url = './'
        platforms_relative_url = '../platforms/'
        output_dir = step['module_options']['output_directory'] + '/md/tags/'
    elif item_type == 'platform':
        markdown_fieldlist = ':orphan:\n:nosearch:\n'
        header_template = Template(PLATFORM_HEADER_JINJA_MARKDOWN)
        content_header = MARKDOWN_PLATFORMPAGE_CONTENT_HEADER
        match_key = 'platforms'
        tags_relative_url = '../tags/'
        platforms_relative_url = './'
        output_dir = step['module_options']['output_directory'] + '/md/platforms/'
    else:
        logging.error('invalid value for facte_type, must be tag or platform')
        sys.exit(1)
    header_template.globals['to_kebab_case'] = to_kebab_case
    markdown_page_header = header_template.render(item=item)
    markdown_software_list = ''
    for software in software_list:
        if any(license in software['licenses'] for license in step['module_options']['exclude_licenses']):
            logging.debug("%s has a license listed in exclude_licenses, skipping", software['name'])
        elif match_key in software and any(value == item['name'] for value in software[match_key]):
            markdown_software_list = markdown_software_list + render_markdown_software(software,
                                                                                       tags_relative_url=tags_relative_url,
                                                                                       platforms_relative_url=platforms_relative_url,
                                                                                       licenses_relative_url='../index.html#list-of-licenses')
    if markdown_software_list:
        markdown_page = '{}{}{}{}'.format(markdown_fieldlist, markdown_page_header, content_header, markdown_software_list)
    else:
        markdown_page = markdown_page_header
    output_file_name = output_dir + to_kebab_case(item['name'] + '.md')
    with open(output_file_name, 'w+', encoding="utf-8") as outfile:
        logging.debug('writing output file %s', output_file_name)
        outfile.write(markdown_page)

def render_markdown_toctree(tags):
    """render the toctree block"""
    logging.debug('rendering toctree')
    tags_files_list = ''
    for tag in tags:
        tag_file_name = 'tags/' + to_kebab_case(tag['name'] + '.md')
        tags_files_list = '{}\n{}'.format(tags_files_list, tag_file_name)
    markdown_toctree = '\n```{{toctree}}\n:maxdepth: 1\n:hidden:\n{}\n```\n\n'.format(tags_files_list)
    return markdown_toctree

def render_markdown_multipage(step):
    """
    Render a single-page markdown list of all software, in alphabetical order
    Prepend/appends the header/footer
    """
    if 'exclude_licenses' not in step['module_options']:
        step['module_options']['exclude_licenses'] = []
    if 'output_file' not in step['module_options']:
        step['module_options']['output_file'] = 'index.md'
    tags = load_yaml_data(step['module_options']['source_directory'] + '/tags', sort_key='name')
    platforms = load_yaml_data(step['module_options']['source_directory'] + '/platforms', sort_key='name')
    software_list = load_yaml_data(step['module_options']['source_directory'] + '/software')
    licenses = load_yaml_data(step['module_options']['source_directory'] + '/licenses.yml')
    # use fieldlist myst-parser extension to limit the TOC depth to 2
    markdown_fieldlist = ':tocdepth: 2\n'
    markdown_content_header = MARKDOWN_INDEX_CONTENT_HEADER
    with open(step['module_options']['source_directory'] + '/markdown/header.md', 'r', encoding="utf-8") as header_file:
        markdown_header = header_file.read()
    with open(step['module_options']['source_directory'] + '/markdown/footer.md', 'r', encoding="utf-8") as footer_file:
        markdown_footer = footer_file.read()
    markdown_toctree = render_markdown_toctree(tags)
    markdown_software_list = ''
    for software in software_list:
        if any(license in software['licenses'] for license in step['module_options']['exclude_licenses']):
            logging.debug("%s has a license listed in exclude_licenses, skipping", software['name'])
        else:
            markdown_software_list = markdown_software_list + render_markdown_software(software)
    markdown_licenses = render_markdown_licenses(step, licenses)
    markdown = '{}{}{}{}{}{}{}'.format(markdown_fieldlist,
                                        markdown_header,
                                        markdown_content_header,
                                        markdown_toctree,
                                        markdown_software_list,
                                        markdown_licenses,
                                        markdown_footer)
    output_file_name = step['module_options']['output_directory'] + '/md/' + step['module_options']['output_file']
    for directory in ['/md/', '/md/tags/', '/md/platforms/']:
        try:
            os.mkdir(step['module_options']['output_directory'] + directory)
        except FileExistsError:
            pass
    with open(output_file_name, 'w+', encoding="utf-8") as outfile:
        logging.info('writing output file %s', output_file_name)
        outfile.write(markdown)
    logging.info('rendering tags pages')
    for tag in tags:
        render_item_page(step, 'tag', tag, software_list)
    logging.info('rendering platforms pages')
    for platform in platforms:
        render_item_page(step, 'platform', platform, software_list)
    try:
        os.mkdir(step['module_options']['output_directory'] + '/_static')
    except FileExistsError:
        pass
    output_css_file_name = step['module_options']['source_directory'] + '/html/_static/custom.css'
    with open(output_css_file_name, 'w+', encoding="utf-8") as outfile:
        logging.info('writing output CSS file %s', output_css_file_name)
        outfile.write(MARKDOWN_CSS)
