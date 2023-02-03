SHELL := /bin/bash

.PHONY: clean # clean files generated by make install/test_run
clean:
	-rm -rf build/ dist/ hecat.egg-info/ awesome-selfhosted awesome-selfhosted-data tests/audio/ tests/video/ tests/shaarli.yml

.PHONY: install # install in a virtualenv
install:
	python3 -m venv .venv && source .venv/bin/activate && \
	pip3 install wheel && \
	python3 setup.py install

##### TESTS #####

.PHONY: test # run tests
test: test_pylint clean clone_awesome_selfhosted test_import_awesome_selfhosted test_process_awesome_selfhosted test_export_awesome_selfhosted test_import_shaarli test_download_video

.PHONY: test_pylint # run linter (non blocking)
test_pylint: install
	source .venv/bin/activate && \
	pip3 install pylint pyyaml && \
	pylint --errors-only --disable=too-many-locals,line-too-long,consider-using-f-string hecat
	-source .venv/bin/activate && \
	pylint --disable=too-many-locals,line-too-long,consider-using-f-string hecat

.PHONY: clone_awesome_selfhosted # clone awesome-selfhosted/awesome-selfhosted-data
clone_awesome_selfhosted:
	git clone --depth=1 https://github.com/awesome-selfhosted/awesome-selfhosted
	git clone https://github.com/awesome-selfhosted/awesome-selfhosted-data

.PHONY: test_import_awesome_selfhosted # test import from awesome-sefhosted
test_import_awesome_selfhosted: install
	rm -rf awesome-selfhosted-data/{tags,software,platforms}
	mkdir awesome-selfhosted-data/{tags,software,platforms}
	source .venv/bin/activate && \
	hecat --config tests/.hecat.import_awesome_selfhosted.yml && \
	hecat --config tests/.hecat.import_awesome_selfhosted_nonfree.yml

.PHONY: test_process_awesome_selfhosted # test processing on awesome-selfhosted-data
test_process_awesome_selfhosted: install
	source .venv/bin/activate && \
	hecat --config tests/.hecat.url_check.yml && \
	hecat --config tests/.hecat.github_metadata.yml && \
	hecat --config tests/.hecat.awesome_lint.yml
	cd awesome-selfhosted-data && git --no-pager diff --color=always

.PHONY: test_export_awesome_selfhosted # test export to singlepage markdown from awesome-selfhosted-data
test_export_awesome_selfhosted: install
	source .venv/bin/activate && \
	hecat --config tests/.hecat.export_markdown_singlepage.yml && \
	cd awesome-selfhosted && git --no-pager diff --color=always

.PHONY: test_import_shaarli # test import from shaarli JSON
test_import_shaarli: install
	source .venv/bin/activate && \
	hecat --config tests/.hecat.import_shaarli.yml

.PHONY: test_download_video # test downloading videos from the shaarli import
test_download_video: install
	source .venv/bin/activate && \
	hecat --config tests/.hecat.download_video.yml

.PHONY: test_download_audio # test downloading audio files from the shaarli import
test_download_audio: install
	source .venv/bin/activate && \
	hecat --config tests/.hecat.download_audio.yml
