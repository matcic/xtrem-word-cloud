# PyInstaller bundles for jira_labels_wordcloud.py
#
# You get one native binary per OS. There is no cross-compile: run `make macos`
# on macOS and `make windows` on Windows (or use a CI matrix) to produce both
# artifacts:
#   macOS   -> dist/jira-labels-wordcloud
#   Windows -> dist/jira-labels-wordcloud.exe
#
# Prereqs: pip install -r requirements.txt pyinstaller
# Optional: export PYTHON=.venv/bin/python3 to use a venv interpreter.

PYTHON         ?= python3
SCRIPT         := jira_labels_wordcloud.py
APP_NAME       := jira-labels-wordcloud
PYINSTALLER    := $(PYTHON) -m PyInstaller

# Helps matplotlib/fonts and lazy imports at runtime; increases bundle size.
PYINSTALLER_OPTS := --onefile \
	--name $(APP_NAME) \
	--collect-all matplotlib \
	--hidden-import wordcloud \
	--hidden-import PIL \
	--hidden-import lxml \
	--hidden-import lxml.etree \
	--hidden-import bs4

ifeq ($(OS),Windows_NT)
DETECTED_OS := Windows
else
_UNAME := $(shell uname -s 2>/dev/null)
ifneq ($(findstring MINGW,$(_UNAME)),)
DETECTED_OS := Windows
else
ifneq ($(findstring MSYS,$(_UNAME)),)
DETECTED_OS := Windows
else
DETECTED_OS := $(_UNAME)
endif
endif
endif

.PHONY: help build macos windows clean

help:
	@echo "Targets:"
	@echo "  make macos    - one-file app for macOS (run on a Mac)"
	@echo "  make windows  - one-file .exe for Windows (run on Windows)"
	@echo "  make build    - same as macos or windows for this machine"
	@echo "  make clean    - remove PyInstaller build/, dist/, and *.spec"
	@echo ""
	@echo "For both macOS and Windows binaries, run the matching target on each OS."

build:
ifeq ($(DETECTED_OS),Darwin)
	@$(MAKE) macos
else
ifeq ($(DETECTED_OS),Windows)
	@$(MAKE) windows
else
	$(error Unsupported host OS '$(DETECTED_OS)'. Run make macos on macOS or make windows on Windows.)
endif
endif

macos:
ifneq ($(DETECTED_OS),Darwin)
	$(error Target 'macos' must be run on macOS (Darwin). This host is '$(DETECTED_OS)'.)
endif
	$(PYINSTALLER) $(PYINSTALLER_OPTS) $(SCRIPT)
	@echo "Built dist/$(APP_NAME)"

windows:
ifneq ($(DETECTED_OS),Windows)
	$(error Target 'windows' must be run on Windows. This host is '$(DETECTED_OS)'.)
endif
	$(PYINSTALLER) $(PYINSTALLER_OPTS) $(SCRIPT)
	@echo "Built dist/$(APP_NAME).exe"

clean:
	rm -rf build dist
	rm -f $(APP_NAME).spec
